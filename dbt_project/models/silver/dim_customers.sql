select

    customer_id
    ,company_name
    ,upper(COALESCE( trim(industry), 'Unknown' )) as Industry
    ,upper(segment) as segment
    ,upper(COALESCE(trim(region),'Unknown')) as region
    ,upper(billing_email) as billing_email
    ,upper(split_part(billing_email,'@',2)) as email_domain
    ,credit_limit::double precision as credit_limit
    ,created_at::date as created_at
    ,is_active

from

{{ref("stg_customers")}}

