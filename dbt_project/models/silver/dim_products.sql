SELECT

    product_id
    ,upper(trim(product_name)) as product_name
    ,upper(trim(product_category)) as product_category
    ,unit_price::double precision as unit_price
    ,upper(trim(description)) as product_description
    ,is_active
    ,created_at::date as created_at

FROM

{{ref('stg_products')}}

