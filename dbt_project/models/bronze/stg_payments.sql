{{
    config(
        materialized='incremental',
        unique_key=['payment_id']
    )
}}



with source as (
        select * from {{ source('raw', 'raw_payments') }}
  ),
  renamed as (
      select
          {{ adapter.quote("payment_id") }},
        {{ adapter.quote("invoice_id") }},
        {{ adapter.quote("customer_id") }},
        {{ adapter.quote("payment_date") }},
        {{ adapter.quote("amount") }},
        {{ adapter.quote("payment_method") }},
        {{ adapter.quote("currency") }},
        {{ adapter.quote("created_at") }},
        current_timestamp as ingestion_timestamp

      from source
  )
  select * from renamed
    