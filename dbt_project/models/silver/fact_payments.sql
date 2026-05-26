SELECT 
payment_id
,invoice_id
,customer_id
,payment_date::date as payment_date
,amount::double precision as amount
,upper(trim(payment_method)) as payment_method
,currency
,created_at::date as created_at


FROM {{ref("stg_payments")}}