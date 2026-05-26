{{
    config(
        materialized='incremental',
        unique_key='account_id'
    )
}}


with source as (
        select * from {{ source('raw', 'raw_chart_of_accounts') }}
  ),
  renamed as (
      select
          
          *,
          current_timestamp as ingestion_timestamp

      from source
  )
  select * from renamed
    