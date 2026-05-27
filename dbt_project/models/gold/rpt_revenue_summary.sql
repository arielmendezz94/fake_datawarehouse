{{ config(materialized='table', tags=['finance', 'revenue', 'sales']) }}

-- ============================================================
-- MODEL: rpt_revenue_summary
-- PURPOSE: Monthly revenue aggregated by customer and sales rep.
--          Joins dim_customers and dim_employees in gold.
--          Filters to PAID invoices only.
-- ============================================================

select

    -- time
    i.invoice_month
    ,i.invoice_quarter
    ,i.invoice_year

    -- customer
    ,c.customer_id
    ,c.company_name
    ,c.segment
    ,c.region

    -- sales rep (sales_rep_id in fact_invoices maps to employee_id)
    ,i.sales_rep_id
    ,e.full_name                                    as sales_rep_name
    ,e.employee_department                          as sales_rep_department

    -- invoice type breakdown
    ,i.invoice_type

    -- aggregated amounts
    ,count(distinct i.invoice_id)                   as invoice_count
    ,sum(i.gross_amount)::numeric                   as gross_revenue
    ,sum(i.line_discount_amount)::numeric           as total_discounts
    ,sum(i.calculated_line_net_amount)::numeric     as net_revenue
    ,avg(i.gross_amount)::numeric                   as avg_invoice_amount

    -- audit
    ,current_timestamp                              as _loaded_at

from {{ ref('fact_invoices') }}                     i
left join {{ ref('dim_customers') }}                c on i.customer_id  = c.customer_id
left join {{ ref('dim_employees') }}                e on i.sales_rep_id = e.employee_id
where i.invoice_status = 'PAID'
group by 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11
order by i.invoice_month, c.company_name
