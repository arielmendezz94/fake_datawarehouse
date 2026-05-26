SELECT

vendor_id
,upper(trim(vendor_name)) as vendor_name
,upper(trim(vendor_category)) as vendor_category
,payment_terms_days::int as payment_terms_days
,expense_account_code::int as expense_account_code
,is_active
,created_at::date as created_at

FROM

{{ref('stg_vendors')}}