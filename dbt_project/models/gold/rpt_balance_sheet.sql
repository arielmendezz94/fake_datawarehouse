with calendar_spine as (
    select distinct
        date_trunc('month', entry_date)::date       as entry_month
    from {{ ref('fact_journal_entries') }}
),

account_spine as (
    select distinct
        account_name,
        account_type,
        account_subtype
    from {{ ref('fact_journal_entries') }}
    where account_type in ('ASSET', 'LIABILITY', 'EQUITY')
),

report_base_matrix as (
    select
        c.entry_month,
        date_trunc('quarter', c.entry_month)::date  as entry_quarter,
        extract(year  from c.entry_month)::int       as entry_year,
        a.account_name,
        a.account_type,
        a.account_subtype
    from calendar_spine c
    cross join account_spine a
),

monthly_actuals as (
    select
        date_trunc('month', entry_date)::date        as entry_month,
        account_name,
        sum(standard_balance_amount)                 as period_amount
    from {{ ref('fact_journal_entries') }}
    where account_type in ('ASSET', 'LIABILITY', 'EQUITY')
    group by 1, 2
),

enriched as (
    select
        m.entry_month,
        m.entry_quarter,
        m.entry_year,
        m.account_type,
        m.account_subtype,
        m.account_name,
        coalesce(a.period_amount, 0.0)::numeric      as period_movement
    from report_base_matrix m
    left join monthly_actuals a
        on  m.entry_month  = a.entry_month
        and m.account_name = a.account_name
),

closing_balances as (
    select
        entry_month,
        entry_quarter,
        entry_year,
        account_type,
        account_subtype,
        account_name,
        period_movement,
        sum(period_movement) over (
            partition by account_name
            order by entry_month
            rows between unbounded preceding and current row
        )::numeric                                   as closing_balance
    from enriched
)

select

    entry_month,
    entry_quarter,
    entry_year,
    account_type,
    account_subtype,
    account_name,

    case
        when account_type = 'ASSET'     then 'Assets'
        when account_type = 'LIABILITY' then 'Liabilities'
        when account_type = 'EQUITY'    then 'Equity'
    end                                              as bs_section,

    case
        when account_type = 'ASSET'     then 1
        when account_type = 'LIABILITY' then 2
        when account_type = 'EQUITY'    then 3
    end                                              as section_sort_key,

    period_movement,
    closing_balance,

    lag(closing_balance, 1, 0.0) over (
        partition by account_name
        order by entry_month
    )                                                as prior_month_balance,

    closing_balance - lag(closing_balance, 1, 0.0) over (
        partition by account_name
        order by entry_month
    )                                                as mom_balance_change,

    case
        when lag(closing_balance, 1, 0.0) over (
            partition by account_name order by entry_month
        ) = 0 then null
        else round(
            (closing_balance - lag(closing_balance, 1, 0.0) over (
                partition by account_name order by entry_month
            ))
            / abs(lag(closing_balance, 1, 0.0) over (
                partition by account_name order by entry_month
            )) * 100
        , 2)
    end                                              as mom_balance_pct,

    current_timestamp                                as _loaded_at,
    md5(entry_month::text || '|' || account_name)    as surrogate_key

from closing_balances
order by entry_month, section_sort_key, account_name