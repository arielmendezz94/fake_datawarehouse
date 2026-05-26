{{
    config(
        materialized='incremental',
        unique_key='product_id'
    )
}}


with source as (
        select * from {{ source('raw', 'raw_products') }}
  ),
  renamed as (
      select
          {{ adapter.quote("product_id") }},
        {{ adapter.quote("product_name") }},
        {{ adapter.quote("product_category") }},
        {{ adapter.quote("unit_price") }},
        {{ adapter.quote("description") }},
        {{ adapter.quote("is_active") }},
        {{ adapter.quote("created_at") }},
        current_timestamp as ingestion_timestamp

      from source
  )
  select * from renamed
    