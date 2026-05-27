{{ config(materialized='table', tags=['finance', 'cash_flow']) }}

-- ============================================================
-- MODEL: rpt_cash_flow
-- PURPOSE: Direct-method cash flow statement.
--          Tracks actual cash movements through the Cash account
--          (account_code 1010) classified by transaction type.
--          All activities in this dataset are Operating.
-- ============================================================

with cash_entries as (
    select
        entry_id,
        transaction_ref,
        transaction_type,
        entry_date,
        entry_month,
        entry_quarter,
        entry_year,
        debit_amount,
        credit_amount,
        -- debits to cash = inflows (cash received)
        -- credits to cash = outflows (cash paid out)
        debit_amount                            as cash_inflow,
        credit_amount                           as cash_outflow,
        (debit_amount - credit_amount)          as net_cash_movement
    from {{ ref('fact_journal_entries') }}
    where account_code::text = '1010'
),

classified as (
    select
        *,
        case
            when transaction_type = 'PAYMENT'
                then 'Cash Received from Customers'
            when transaction_type = 'BILL_PAYMENT'
                then 'Cash Paid to Vendors'
            when transaction_type in ('PAYROLL_SALARY', 'PAYROLL_BONUS')
                then 'Cash Paid for Payroll'
            else 'Other Operating Cash'
        end                                     as cash_flow_category,

        case
            when transaction_type = 'PAYMENT'                           then 1
            when transaction_type = 'BILL_PAYMENT'                      then 2
            when transaction_type in ('PAYROLL_SALARY','PAYROLL_BONUS') then 3
            else 9
        end                                     as category_sort_key,

        'Operating Activities'                  as cash_flow_section
    from cash_entries
),

monthly_summary as (
    select
        entry_month,
        entry_quarter,
        entry_year,
        cash_flow_section,
        cash_flow_category,
        category_sort_key,
        transaction_type,
        sum(cash_inflow)::numeric               as total_cash_inflow,
        sum(cash_outflow)::numeric              as total_cash_outflow,
        sum(net_cash_movement)::numeric         as net_cash_movement
    from classified
    group by 1, 2, 3, 4, 5, 6, 7
),

-- compute cumulative balance first, then LAG on top (PostgreSQL safe)
with_running_balance as (
    select
        *,
        sum(net_cash_movement) over (
            order by entry_month
            rows between unbounded preceding and current row
        )::numeric                              as cumulative_cash_balance
    from monthly_summary
)

select

    entry_month,
    entry_quarter,
    entry_year,
    cash_flow_section,
    cash_flow_category,
    category_sort_key,
    transaction_type,

    total_cash_inflow,
    total_cash_outflow,
    net_cash_movement,
    cumulative_cash_balance,

    -- MoM movement per category
    lag(net_cash_movement, 1, 0.0) over (
        partition by cash_flow_category
        order by entry_month
    )                                           as prior_month_net_cash,

    net_cash_movement
        - lag(net_cash_movement, 1, 0.0) over (
            partition by cash_flow_category
            order by entry_month
        )                                       as mom_cash_variance,

    case
        when lag(net_cash_movement, 1, 0.0) over (
            partition by cash_flow_category order by entry_month
        ) = 0 then null
        else round(
            (net_cash_movement
                - lag(net_cash_movement, 1, 0.0) over (
                    partition by cash_flow_category order by entry_month
                )
            )
            / abs(lag(net_cash_movement, 1, 0.0) over (
                partition by cash_flow_category order by entry_month
            )) * 100
        , 2)
    end                                         as mom_cash_variance_pct,

    current_timestamp                           as _loaded_at,
    md5(entry_month::text || '|' || cash_flow_category) as surrogate_key

from with_running_balance
order by entry_month, category_sort_key
