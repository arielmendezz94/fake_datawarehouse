select
a.invoice_id
,a.customer_id
,a.subscription_id
,a.sales_rep_id
,upper(a.invoice_type) as invoice_type
,a.invoice_date::date as invoice_date
,a.due_date::date as due_date
,upper(trim(a.status)) as invoice_status
--,a.total_amount::double precision as total_amount
,a.currency
,a.created_at::date as invoice_created_at
,b.product_id
,upper(trim(b.description)) as product_description
,b.quantity::int as quantity
,b.unit_price::double precision as unit_price
,b.discount_pct::int as discount_pct
,b.line_total::double precision as gross_amount
,a.total_amount::double precision as invoice_header_total
,((b.quantity * b.unit_price) * (b.discount_pct / 100.0))::double precision as line_discount_amount

 -- Calculated clean line value (useful for double-checking source system math)
,((b.quantity * b.unit_price) * (1 - (b.discount_pct / 100.0)))::double precision as calculated_line_net_amount

,case when upper(trim(a.status)) = 'PAID' then true else false end as is_paid_invoice
--,c.payment_id
--,c.payment_date::date as payment_date
--,upper(trim(c.payment_method)) as payment_method
,(a.due_date::date - a.invoice_date::date) as payment_term_days_window
,case
        when upper(trim(a.status)) != 'PAID' and current_date > a.due_date::date 
        then (current_date - a.due_date::date) 
    else 0 end as days_past_due

,case 
    when upper(trim(a.status)) = 'PAID' then 'Paid'
    when (current_date - a.due_date::date) <= 0 then 'Current (Not Due)'
    when (current_date - a.due_date::date) <= 30 then '1-30 Days Overdue'
    when (current_date - a.due_date::date) <= 60 then '31-60 Days Overdue'
    when (current_date - a.due_date::date) <= 90 then '61-90 Days Overdue'
    else '91+ Days Overdue'
    end as ar_aging_bucket

-- 2. Audit & Lineage Fields (Tells you when the row was loaded into Silver)
,current_timestamp as silver_inserted_at

-- 3. Pre-extracted Dates (Speeds up GROUP BY queries in your Gold layer)
,date_trunc('month', a.invoice_date::date)::date as invoice_month
,date_trunc('quarter', a.invoice_date::date)::date as invoice_quarter
,extract(year from a.invoice_date::date)::int as invoice_year


from
{{ref("stg_invoices")}} as a
left join {{ref("stg_invoice_lines")}} as b on a.invoice_id = b.invoice_id

--left join {{ref("stg_payments")}} as c on a.invoice_id = c.invoice_id

order by a.invoice_id asc

