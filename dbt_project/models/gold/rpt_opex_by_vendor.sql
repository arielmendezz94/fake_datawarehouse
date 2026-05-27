{{ config(materialized='table', tags=['finance', 'opex', 'ap']) }}

-- ============================================================
-- MODEL: rpt_opex_by_vendor
-- PURPOSE: Operating expense breakdown by vendor and account.
--          Joins dim_vendors and dim_accounts in gold.
-- ============================================================

select

    -- time
    b.bill_month
    ,b.bill_quarter
    ,b.bill_year

    -- vendor context
    ,v.vendor_id
    ,v.vendor_name
    ,v.vendor_category
    ,v.payment_terms_days

    -- account context
    ,a.account_id                                   as expense_account_id
    ,a.account_code                                 as expense_account_code
    ,a.account_name                                 as expense_account_name
    ,a.account_subtype                              as expense_account_subtype

    -- bill details
    ,b.bill_id
    ,b.bill_date
    ,b.due_date
    ,b.status
    ,b.currency
    ,b.description

    -- amounts
    ,b.amount

    -- aging flags
    ,b.is_paid
    ,b.is_overdue
    ,b.days_past_due

    -- monthly aggregates
    ,count(b.bill_id) over (
        partition by b.bill_month, v.vendor_id
    )                                               as bills_this_month_per_vendor

    ,sum(b.amount) over (
        partition by b.bill_month, v.vendor_id
    )::numeric                                      as total_spend_this_month_per_vendor

    ,sum(b.amount) over (
        partition by b.bill_month, a.account_id
    )::numeric                                      as total_spend_this_month_per_account

    -- audit
    ,current_timestamp                              as _loaded_at

from {{ ref('fact_vendor_bills') }}               b
left join {{ ref('dim_vendors') }}                  v on b.vendor_id         = v.vendor_id
left join {{ ref('dim_accounts') }}                 a on b.expense_account_id = a.account_id
order by b.bill_month, v.vendor_name
