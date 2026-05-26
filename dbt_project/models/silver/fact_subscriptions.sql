select

    subscription_id
    ,customer_id
    ,product_id
    ,plan_name
    ,upper(trim(status))                                        as status
    ,mrr::double precision                                      as mrr
    ,(mrr * 12)::double precision                              as arr
    ,start_date::date                                          as start_date
    ,end_date::date                                            as end_date
    ,created_at::date                                          as created_at
    ,updated_at::date                                          as updated_at

    -- flags
    ,case when upper(trim(status)) = 'ACTIVE'  then true else false end  as is_active
    ,case when upper(trim(status)) = 'CHURNED' then true else false end  as is_churned

    -- derived
    ,round((coalesce(end_date::date, current_date) - start_date::date) / 30.0)::int as tenure_months

    -- date spine
    ,date_trunc('month', start_date::date)::date               as start_month
    ,date_trunc('month', coalesce(end_date::date, current_date))::date          as end_month
    ,extract(year from start_date::date)::int                  as start_year
    ,current_timestamp


    ,(mrr::double precision * round((coalesce(end_date::date, current_date) - start_date::date) / 30.0)) as lifetime_revenue_to_date

    -- 2. Renewal Risk & Window (Postgres direct subtraction returns days)
    ,case 
        when upper(trim(status)) = 'ACTIVE' and end_date is not null then (end_date::date - current_date)
        else null 
     end as days_until_renewal_or_expiration

    -- 3. Customer Lifecycle Segment (Using Postgres date math)
    ,case 
        when upper(trim(status)) = 'CHURNED' then 'CHURNED'
        when (current_date - start_date::date) <= 90 then 'NEW_CUSTOMER'    -- 90 days instead of 3 months
        when (current_date - start_date::date) <= 365 then 'RAMPING'         -- 365 days instead of 12 months
        else 'MATURE_LOYAL'
     end as account_lifecycle_stage

    -- 4. Next Month Expansion MRR Baseline
    ,case 
        when upper(trim(status)) = 'ACTIVE' then mrr::double precision 
        else 0.0 
     end as active_mrr_baseline

from {{ ref('stg_subscriptions') }}
