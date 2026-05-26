SELECT

account_id
,account_code::int as account_code
,upper(trim(account_name)) as account_name
,upper(trim(account_type)) as account_type
,upper(trim(account_subtype)) as account_subtype
,is_active

FROM

{{ref('stg_chart_of_accounts')}}
