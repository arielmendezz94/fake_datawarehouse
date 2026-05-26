-- 1. Create a clean matrix of every account and every active month to prevent reporting gaps
with calendar_spine as (
    select distinct 
        date_trunc('month', entry_date)::date as entry_month
    from {{ ref('fact_journal_entries') }} 
),

account_spine as (
    select distinct 
        account_name,
        account_type,
        account_subtype
    from {{ ref('fact_journal_entries') }} 
    where account_type in ('REVENUE', 'COGS', 'OPEX')
),

report_base_matrix as (
    select 
        c.entry_month,
        date_trunc('quarter', c.entry_month)::date as entry_quarter,
        extract(year from c.entry_month)::int as entry_year,
        a.account_name,
        a.account_type,
        a.account_subtype
    from calendar_spine c
    cross join account_spine a
),

-- 2. Aggregate actual transactional amounts
monthly_actuals as (
    select
        date_trunc('month', entry_date)::date as entry_month
        ,account_name
        ,sum(standard_balance_amount) as actual_period_amount
    from {{ ref('fact_journal_entries') }} 
    group by 1, 2
),

-- 3. Combine matrix with actuals, turning missing periods into $0
enriched_pnl as (
    select
        m.entry_month
        ,m.entry_quarter
        ,m.entry_year
        ,m.account_type
        ,m.account_subtype
        ,m.account_name
        ,coalesce(a.actual_period_amount, 0.0)::double precision as period_amount
    from report_base_matrix m
    left join monthly_actuals a 
        on m.entry_month = a.entry_month 
        and m.account_name = a.account_name
)

-- 4. Final selection with Time-Travel Lag Metrics and Hierarchy Sort Keys
select
    entry_month
    ,entry_quarter
    ,entry_year
    ,account_type
    ,account_subtype
    ,account_name
    ,period_amount
    
    -- YTD running total that resets every January 1st
    ,sum(period_amount) over (
        partition by account_name, entry_year
        order by entry_month
        rows between unbounded preceding and current row
    )::double precision as ytd_cumulative_amount

    -- NEW: Prior Month Amount (For Month-over-Month variance analysis)
    ,lag(period_amount, 1, 0.0) over (
        partition by account_name 
        order by entry_month
    )::double precision as prior_month_amount

    -- NEW: Prior Year Same Month Amount (For Year-over-Year seasonality analysis)
    ,lag(period_amount, 12, 0.0) over (
        partition by account_name 
        order by entry_month
    )::double precision as prior_year_same_month_amount

    -- Hierarchy sorting keys for flawless dashboard rendering
    ,case 
        when account_type = 'REVENUE' then 1
        when account_type = 'COGS' then 2
        when account_type = 'OPEX' then 3
        else 4 
     end as account_type_sort_key

    -- NEW: Standardizes P&L naming conventions for financial statement output
    ,case 
        when account_type = 'REVENUE' then 'Gross Revenue'
        when account_type = 'COGS' then 'Cost of Goods Sold'
        when account_type = 'OPEX' then 'Operating Expenses'
        else 'Other'
     end as financial_statement_line_item

from enriched_pnl
