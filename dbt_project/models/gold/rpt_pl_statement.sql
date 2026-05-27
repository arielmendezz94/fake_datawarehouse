{{
  config(
    materialized = 'table',
    tags         = ['finance', 'pnl', 'daily'],
    meta         = {
      'owner': 'finance-analytics',
      'contains_pii': false,
      'sla': 'daily_by_6am'
    }
  )
}}

-- ============================================================
-- MODEL: pnl_production
-- PURPOSE: Corporate P&L reporting model with actuals,
--          common-size metrics, and MoM/YoY analysis.
-- NOTE:    Budget variance columns are stubbed as 0.0 until
--          a fact_budget source is available. Search for
--          "BUDGET STUB" to find and replace when ready.
-- ============================================================


-- ------------------------------------------------------------
-- SPINE 1: Every distinct reporting month in the ledger.
--          Ensures no gaps in the time series even if a month
--          has zero activity for a given account.
-- ------------------------------------------------------------
with calendar_spine as (
    select distinct
        date_trunc('month', entry_date)::date as entry_month
    from {{ ref('fact_journal_entries') }}
),

-- ------------------------------------------------------------
-- SPINE 2: Every P&L account (Revenue, COGS, Opex).
--          Scoped to the three types that belong on the P&L;
--          balance sheet accounts are intentionally excluded.
-- ------------------------------------------------------------
account_spine as (
    select distinct
        account_name,
        account_type,
        account_subtype
    from {{ ref('fact_journal_entries') }}
    where account_type in ('REVENUE', 'COGS', 'OPEX')
),

-- ------------------------------------------------------------
-- MATRIX: Cross-join of all months × all accounts.
--         Every account will have a row for every month,
--         even if the actual amount is $0.
-- ------------------------------------------------------------
report_base_matrix as (
    select
        c.entry_month,
        date_trunc('quarter', c.entry_month)::date  as entry_quarter,
        extract(year  from c.entry_month)::int       as entry_year,
        extract(month from c.entry_month)::int       as entry_month_num,
        a.account_name,
        a.account_type,
        a.account_subtype
    from calendar_spine c
    cross join account_spine a
),

-- ------------------------------------------------------------
-- ACTUALS: Monthly aggregation of journal entry amounts.
--          standard_balance_amount is assumed to be stored as
--          a positive value regardless of account type; sign
--          convention is applied in the signed_pnl CTE below.
-- ------------------------------------------------------------
monthly_actuals as (
    select
        date_trunc('month', entry_date)::date as entry_month,
        account_name,
        sum(standard_balance_amount)          as actual_period_amount
    from {{ ref('fact_journal_entries') }}
    group by 1, 2
),

-- ------------------------------------------------------------
-- ENRICH: Join actuals onto the spine matrix.
--         Missing periods default to $0 (not NULL) so that
--         window functions are never skewed by NULLs.
-- ------------------------------------------------------------
enriched_pnl as (
    select
        m.entry_month,
        m.entry_quarter,
        m.entry_year,
        m.entry_month_num,
        m.account_type,
        m.account_subtype,
        m.account_name,

        coalesce(a.actual_period_amount, 0.0)::numeric as period_amount,

        -- BUDGET STUB: replace 0.0 with the budget join column
        -- once fact_budget is available (see model header note).
        0.0::numeric as budget_period_amount

    from report_base_matrix m
    left join monthly_actuals a
        on  m.entry_month  = a.entry_month
        and m.account_name = a.account_name
),

-- ------------------------------------------------------------
-- SIGN: Apply standard accounting sign convention.
--       Revenue → positive. COGS / OPEX → negative.
--       Allows plain SUM() in BI tools to produce
--       Gross Profit, EBIT, etc. without extra logic.
-- ------------------------------------------------------------
signed_pnl as (
    select
        *,
        case
            when account_type = 'REVENUE' then  period_amount
            else                               -period_amount
        end::numeric as signed_period_amount,

        case
            when account_type = 'REVENUE' then  budget_period_amount
            else                               -budget_period_amount
        end::numeric as signed_budget_amount

    from enriched_pnl
)


-- ============================================================
-- FINAL OUTPUT
-- ============================================================
select

    -- ----------------------------------------------------------
    -- TIME DIMENSIONS
    -- ----------------------------------------------------------
    entry_month,
    entry_quarter,
    entry_year,
    entry_month_num,

    -- ----------------------------------------------------------
    -- ACCOUNT DIMENSIONS
    -- ----------------------------------------------------------
    account_type,
    account_subtype,
    account_name,

    case
        when account_type = 'REVENUE' then 'Gross Revenue'
        when account_type = 'COGS'    then 'Cost of Goods Sold'
        when account_type = 'OPEX'    then 'Operating Expenses'
        else 'Other'
    end as financial_statement_line_item,

    -- ----------------------------------------------------------
    -- HIERARCHY SORT KEYS
    -- ----------------------------------------------------------
    case
        when account_type = 'REVENUE' then 1
        when account_type = 'COGS'    then 2
        when account_type = 'OPEX'    then 3
        else 9
    end as account_type_sort_key,

    case
        when account_type = 'OPEX' and account_subtype = 'SALES_MARKETING' then 1
        when account_type = 'OPEX' and account_subtype = 'R&D'             then 2
        when account_type = 'OPEX' and account_subtype = 'G&A'             then 3
        else 9
    end as account_subtype_sort_key,

    (
        case
            when account_type = 'REVENUE' then 1
            when account_type = 'COGS'    then 2
            when account_type = 'OPEX'    then 3
            else 9
        end * 100
    ) + (
        case
            when account_type = 'OPEX' and account_subtype = 'SALES_MARKETING' then 1
            when account_type = 'OPEX' and account_subtype = 'R&D'             then 2
            when account_type = 'OPEX' and account_subtype = 'G&A'             then 3
            else 9
        end
    ) as display_sort_key,

    -- ----------------------------------------------------------
    -- ACTUALS
    -- ----------------------------------------------------------
    period_amount,
    signed_period_amount,

    -- YTD running total, resets every January
    sum(signed_period_amount) over (
        partition by account_name, entry_year
        order by entry_month
        rows between unbounded preceding and current row
    ) as ytd_cumulative_amount,

    -- ----------------------------------------------------------
    -- MoM VARIANCE
    -- ----------------------------------------------------------
    lag(signed_period_amount, 1, 0.0) over (
        partition by account_name
        order by entry_month
    ) as prior_month_amount,

    signed_period_amount
        - lag(signed_period_amount, 1, 0.0) over (
            partition by account_name order by entry_month
        ) as mom_variance_abs,

    -- NULL when prior month is $0 to avoid divide-by-zero
    case
        when lag(signed_period_amount, 1, 0.0) over (
            partition by account_name order by entry_month
        ) = 0 then null
        else round(
            (
                signed_period_amount
                - lag(signed_period_amount, 1, 0.0) over (
                    partition by account_name order by entry_month
                )
            )
            / abs(
                lag(signed_period_amount, 1, 0.0) over (
                    partition by account_name order by entry_month
                )
            ) * 100
        , 2)
    end as mom_variance_pct,

    -- ----------------------------------------------------------
    -- YoY VARIANCE
    -- ----------------------------------------------------------
    lag(signed_period_amount, 12, 0.0) over (
        partition by account_name
        order by entry_month
    ) as prior_year_same_month_amount,

    signed_period_amount
        - lag(signed_period_amount, 12, 0.0) over (
            partition by account_name order by entry_month
        ) as yoy_variance_abs,

    -- NULL when prior year month is $0
    case
        when lag(signed_period_amount, 12, 0.0) over (
            partition by account_name order by entry_month
        ) = 0 then null
        else round(
            (
                signed_period_amount
                - lag(signed_period_amount, 12, 0.0) over (
                    partition by account_name order by entry_month
                )
            )
            / abs(
                lag(signed_period_amount, 12, 0.0) over (
                    partition by account_name order by entry_month
                )
            ) * 100
        , 2)
    end as yoy_variance_pct,

    -- ----------------------------------------------------------
    -- BUDGET VARIANCE
    -- Stubbed at 0.0 until fact_budget is available.
    -- Search "BUDGET STUB" in this file to wire it up.
    -- ----------------------------------------------------------
    signed_budget_amount as budget_amount,

    (signed_period_amount - signed_budget_amount) as actuals_vs_budget_abs,

    case
        when signed_budget_amount = 0 then null
        else round(
            (signed_period_amount - signed_budget_amount)
            / abs(signed_budget_amount) * 100
        , 2)
    end as actuals_vs_budget_pct,

    -- ----------------------------------------------------------
    -- COMMON-SIZE P&L (% of Revenue)
    -- NULL when total revenue for the month is $0.
    -- ----------------------------------------------------------
    round(
        period_amount / nullif(
            sum(case when account_type = 'REVENUE' then period_amount end)
                over (partition by entry_month),
        0) * 100
    , 2) as pct_of_revenue,

    -- ----------------------------------------------------------
    -- AUDIT METADATA
    -- ----------------------------------------------------------
    current_timestamp                                  as _loaded_at,
    '{{ invocation_id }}'                              as _dbt_invocation_id,
    md5(entry_month::text || '|' || account_name)      as surrogate_key

from signed_pnl
order by entry_month, display_sort_key, account_name