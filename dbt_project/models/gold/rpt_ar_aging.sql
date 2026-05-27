{{ config(materialized='table', tags=['finance', 'ar', 'aging']) }}

-- ============================================================
-- MODEL: rpt_ar_aging
-- PURPOSE: Accounts receivable aging report.
--          One row per open invoice line with customer context.
--          ar_aging_bucket is pre-computed in fact_invoices.
-- ============================================================

select

    -- invoice identifiers
    i.invoice_id
    ,i.invoice_type
    ,i.invoice_date
    ,i.due_date
    ,i.invoice_status
    ,i.currency
    ,i.invoice_month
    ,i.invoice_quarter
    ,i.invoice_year

    -- customer context (joined in gold)
    ,c.customer_id
    ,c.company_name
    ,c.segment
    ,c.region
    ,c.billing_email
    ,c.credit_limit
    ,c.is_active                                    as customer_is_active

    -- amounts
    ,i.gross_amount
    ,i.invoice_header_total
    ,i.calculated_line_net_amount                   as net_amount
    ,i.line_discount_amount                         as discount_amount

    -- aging
    ,i.ar_aging_bucket
    ,i.days_past_due
    ,i.payment_term_days_window
    ,i.is_paid_invoice

    -- audit
    ,current_timestamp                              as _loaded_at

from {{ ref('fact_invoices') }}                     i
left join {{ ref('dim_customers') }}                c on i.customer_id = c.customer_id
order by i.days_past_due desc, i.invoice_date
