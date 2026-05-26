{{
    config(
        materialized='incremental',
        unique_key='subscription_id'
    )
}}

with source as (
        select * from {{ source('raw', 'raw_subscriptions') }}
  ),
  renamed as (
      select
          {{ adapter.quote("subscription_id") }},
        {{ adapter.quote("customer_id") }},
        {{ adapter.quote("product_id") }},
        {{ adapter.quote("plan_name") }},
        {{ adapter.quote("status") }},
        {{ adapter.quote("mrr") }},
        {{ adapter.quote("start_date") }},
        {{ adapter.quote("end_date") }},
        {{ adapter.quote("created_at") }},
        {{ adapter.quote("updated_at") }},
        current_timestamp as ingestion_timestamp

      from source
  )
  select * from renamed
    