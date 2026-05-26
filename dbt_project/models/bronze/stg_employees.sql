{{
    config(
        materialized='incremental',
        unique_key='employee_id'
    )
}}


with source as (
        select * from {{ source('raw', 'raw_employees') }}
  ),
  renamed as (
      select
          {{ adapter.quote("employee_id") }},
        {{ adapter.quote("first_name") }},
        {{ adapter.quote("last_name") }},
        {{ adapter.quote("department") }},
        {{ adapter.quote("role") }},
        {{ adapter.quote("salary") }},
        {{ adapter.quote("hire_date") }},
        {{ adapter.quote("is_active") }},
        {{ adapter.quote("created_at") }},
        {{ adapter.quote("manager_id") }},
        current_timestamp as ingestion_timestamp

      from source
  )
  select * from renamed
    