{{
    config(
        materialized='incremental',
        unique_key=['entry_id','transaction_ref']
    )
}}


with source as (
        select * from {{ source('raw', 'raw_journal_entries') }}
  ),
  renamed as (
      select
          {{ adapter.quote("entry_id") }},
        {{ adapter.quote("transaction_ref") }},
        {{ adapter.quote("transaction_type") }},
        {{ adapter.quote("account_id") }},
        {{ adapter.quote("account_code") }},
        {{ adapter.quote("entry_date") }},
        {{ adapter.quote("debit_amount") }},
        {{ adapter.quote("credit_amount") }},
        {{ adapter.quote("description") }},
        {{ adapter.quote("created_at") }},
        current_timestamp as ingestion_timestamp

      from source
  )
  select * from renamed
    