{{ config(materialized='table', tags=['finance', 'payroll', 'headcount']) }}

-- ============================================================
-- MODEL: rpt_payroll_burn
-- PURPOSE: Monthly payroll cost by employee and department.
--          Joins dim_employees in gold for name and role context.
-- ============================================================

select

    -- time
    p.pay_month
    ,p.pay_quarter
    ,p.pay_year
    ,p.pay_period_start
    ,p.pay_period_end
    ,p.payment_date

    -- employee context
    ,e.employee_id
    ,e.full_name
    ,e.employee_department                          as department
    ,e.employee_role                                as role
    ,e.manager_name
    ,e.is_active                                    as employee_is_active

    -- payroll details
    ,p.pay_type
    ,p.is_salary
    ,p.is_bonus
    ,p.gross_pay
    ,p.tax_withheld
    ,p.net_pay
    ,p.effective_tax_rate

    -- department rollup (window — no GROUP BY needed in BI tool)
    ,sum(p.gross_pay) over (
        partition by p.pay_month, p.department
    )::numeric                                      as dept_gross_pay_this_month

    ,count(distinct p.employee_id) over (
        partition by p.pay_month, p.department
    )                                               as dept_headcount_this_month

    ,sum(p.gross_pay) over (
        partition by p.pay_month
    )::numeric                                      as total_payroll_this_month

    -- audit
    ,current_timestamp                              as _loaded_at

from {{ ref('fact_payroll') }}                      p
left join {{ ref('dim_employees') }}                e on p.employee_id = e.employee_id
order by p.pay_month, e.employee_department, e.full_name
