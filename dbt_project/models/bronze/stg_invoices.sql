{{
    config(
        materialized='incremental',
        unique_key='invoice_id'
    )
}}



with source as (
        select * from {{ source('raw', 'raw_invoices') }}
  ),
  renamed as (
      select
          {{ adapter.quote("invoice_id") }},
        {{ adapter.quote("customer_id") }},
        {{ adapter.quote("subscription_id") }},
        {{ adapter.quote("sales_rep_id") }},
        {{ adapter.quote("invoice_type") }},
        {{ adapter.quote("invoice_date") }},
        {{ adapter.quote("due_date") }},
        {{ adapter.quote("status") }},
        {{ adapter.quote("total_amount") }},
        {{ adapter.quote("currency") }},
        {{ adapter.quote("created_at") }},
        current_timestamp as ingestion_timestamp

      from source
  )
  select * from renamed
    