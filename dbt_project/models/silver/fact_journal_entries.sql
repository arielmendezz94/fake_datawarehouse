select

    b.entry_id
    ,b.transaction_ref
    ,b.transaction_type
    ,b.account_id
    ,b.account_code
    ,b.entry_date::date                                            as entry_date
    ,b.debit_amount::double precision                             as debit_amount
    ,b.credit_amount::double precision                            as credit_amount
    ,b.description
    ,b.created_at::date                                           as created_at

    -- from dim_accounts
    ,a.account_name
    ,a.account_type       -- Revenue / COGS / OpEx / Asset / Liability / Equity
    ,a.account_subtype
    ,a.is_active          as account_is_active

    -- derived
    ,(b.debit_amount - b.credit_amount)::double precision        as net_amount
    ,case when b.debit_amount > 0 then true else false end        as is_debit
    ,date_trunc('month',   b.entry_date::date)::date             as entry_month
    ,date_trunc('quarter', b.entry_date::date)::date             as entry_quarter
    ,extract(year from     b.entry_date::date)::int              as entry_year

    ,current_timestamp                                             as silver_inserted_at


    ,case 
            when upper(trim(a.account_type)) in ('ASSET', 'OPEX', 'COGS') 
            then (b.debit_amount::double precision - b.credit_amount::double precision)
            when upper(trim(a.account_type)) in ('LIABILITY', 'EQUITY', 'REVENUE') 
            then (b.credit_amount::double precision - b.debit_amount::double precision)
            else (b.debit_amount::double precision - b.credit_amount::double precision)
        end as standard_balance_amount


        -- 3. Is Closed/Frozen Period Flag (Protects historical financial books from editing)
        ,case 
            when b.entry_date::date < date_trunc('month', current_date)::date then true 
            else false 
        end as is_closed_accounting_period


from {{ ref('stg_journal_entries') }}  b
left join {{ ref('dim_accounts') }}     a  on b.account_id = a.account_id