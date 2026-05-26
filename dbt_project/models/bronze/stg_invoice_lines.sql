{{
    config(
        materialized='incremental',
        unique_key=['line_id','invoice_id']
    )
}}


with source as (
        select * from {{ source('raw', 'raw_invoice_lines') }}
  ),
  renamed as (
      select
          {{ adapter.quote("line_id") }},
        {{ adapter.quote("invoice_id") }},
        {{ adapter.quote("product_id") }},
        {{ adapter.quote("description") }},
        {{ adapter.quote("quantity") }},
        {{ adapter.quote("unit_price") }},
        {{ adapter.quote("discount_pct") }},
        {{ adapter.quote("line_total") }},
        current_timestamp as ingestion_timestamp

      from source
  )
  select * from renamed
    