{{ config(materialized='table', tags=['finance', 'saas', 'mrr']) }}

-- ============================================================
-- MODEL: rpt_mrr
-- PURPOSE: Monthly recurring revenue snapshot per subscription.
--          One row per subscription per month it was active.
--          Joins dim_customers and dim_products in gold.
-- ============================================================

select

    -- subscription identifiers
    s.subscription_id
    ,s.plan_name
    ,s.status
    ,s.account_lifecycle_stage

    -- customer context
    ,c.customer_id
    ,c.company_name
    ,c.segment
    ,c.region

    -- product context
    ,p.product_id
    ,p.product_name
    ,p.product_category

    -- revenue metrics
    ,s.mrr
    ,s.arr
    ,s.active_mrr_baseline
    ,s.lifetime_revenue_to_date

    -- subscription dates
    ,s.start_date
    ,s.end_date
    ,s.start_month
    ,s.end_month
    ,s.start_year
    ,s.tenure_months
    ,s.days_until_renewal_or_expiration

    -- flags
    ,s.is_active
    ,s.is_churned

    -- audit
    ,current_timestamp                              as _loaded_at

from {{ ref('fact_subscriptions') }}                s
left join {{ ref('dim_customers') }}                c on s.customer_id = c.customer_id
left join {{ ref('dim_products') }}                 p on s.product_id  = p.product_id
order by s.start_month, c.company_name
