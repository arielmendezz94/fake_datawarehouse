{{
    config(
        materialized='incremental',
        unique_key=['bill_id','vendor_id']
    )
}}

with source as (
        select * from {{ source('raw', 'raw_vendor_bills') }}
  ),
  renamed as (
      select
          {{ adapter.quote("bill_id") }},
        {{ adapter.quote("vendor_id") }},
        {{ adapter.quote("expense_account_id") }},
        {{ adapter.quote("bill_date") }},
        {{ adapter.quote("due_date") }},
        {{ adapter.quote("amount") }},
        {{ adapter.quote("status") }},
        {{ adapter.quote("description") }},
        {{ adapter.quote("currency") }},
        {{ adapter.quote("created_at") }},
        current_timestamp as ingestion_timestamp

      from source
  )
  select * from renamed
    