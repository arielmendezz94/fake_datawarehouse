select

    bill_id
    ,vendor_id
    ,expense_account_id
    ,bill_date::date                                           as bill_date
    ,due_date::date                                            as due_date
    ,amount::double precision                                  as amount
    ,upper(trim(status))                                       as status
    ,description
    ,upper(trim(currency))                                     as currency
    ,created_at::date                                          as created_at

    -- flags
    ,case when upper(trim(status)) = 'PAID' then true else false end     as is_paid
    ,case
        when upper(trim(status)) != 'PAID'
         and current_date > due_date::date
        then true else false
     end                                                       as is_overdue

    -- derived
    ,case
        when upper(trim(status)) != 'PAID'
         and current_date > due_date::date
        then (current_date - due_date::date)
        else 0
     end                                                       as days_past_due

    -- date spine
    ,date_trunc('month',   bill_date::date)::date             as bill_month
    ,date_trunc('quarter', bill_date::date)::date             as bill_quarter
    ,extract(year from     bill_date::date)::int              as bill_year

    ,current_timestamp                                         as silver_inserted_at

from {{ ref('stg_vendor_bills') }}