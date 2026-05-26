
{{
    config(
        materialized='incremental',
        unique_key='vendor_id'
    )
}}

with source as (
        select * from {{ source('raw', 'raw_vendors') }}
  ),
  renamed as (
      select
          {{ adapter.quote("vendor_id") }},
        {{ adapter.quote("vendor_name") }},
        {{ adapter.quote("vendor_category") }},
        {{ adapter.quote("payment_terms_days") }},
        {{ adapter.quote("expense_account_code") }},
        {{ adapter.quote("is_active") }},
        {{ adapter.quote("created_at") }},
        current_timestamp as ingestion_timestamp

      from source
  )
  select * from renamed
    