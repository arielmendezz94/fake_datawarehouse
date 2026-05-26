{{
    config(
        materialized='incremental',
        unique_key='customer_id'
    )
}}


with source as (
        select * from {{ source('raw', 'raw_customers') }}
  ),
  renamed as (
      select
          {{ adapter.quote("customer_id") }},
        {{ adapter.quote("company_name") }},
        {{ adapter.quote("industry") }},
        {{ adapter.quote("segment") }},
        {{ adapter.quote("region") }},
        {{ adapter.quote("billing_email") }},
        {{ adapter.quote("credit_limit") }},
        {{ adapter.quote("created_at") }},
        {{ adapter.quote("is_active") }},
        current_timestamp as ingestion_timestamp

      from source
  )
  select * from renamed
    