{{
    config(
        materialized='incremental',
        unique_key=['payroll_id']
    )
}}

with source as (
        select * from {{ source('raw', 'raw_payroll') }}
  ),
  renamed as (
      select
          {{ adapter.quote("payroll_id") }},
        {{ adapter.quote("employee_id") }},
        {{ adapter.quote("department") }},
        {{ adapter.quote("pay_period_start") }},
        {{ adapter.quote("pay_period_end") }},
        {{ adapter.quote("gross_pay") }},
        {{ adapter.quote("tax_withheld") }},
        {{ adapter.quote("net_pay") }},
        {{ adapter.quote("payment_date") }},
        {{ adapter.quote("pay_type") }},
        {{ adapter.quote("created_at") }},
        current_timestamp as ingestion_timestamp

      from source
  )
  select * from renamed
    