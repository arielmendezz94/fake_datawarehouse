select

    payroll_id
    ,employee_id
    ,department
    ,pay_period_start::date                                    as pay_period_start
    ,pay_period_end::date                                      as pay_period_end
    ,payment_date::date                                        as payment_date
    ,gross_pay::double precision                               as gross_pay
    ,tax_withheld::double precision                            as tax_withheld
    ,net_pay::double precision                                 as net_pay
    ,upper(trim(pay_type))                                     as pay_type
    ,created_at::date                                          as created_at

    -- flags
    ,case when upper(trim(pay_type)) = 'BONUS'  then true else false end  as is_bonus
    ,case when upper(trim(pay_type)) = 'SALARY' then true else false end  as is_salary

    -- derived
    ,(tax_withheld::double precision
        / nullif(gross_pay::double precision, 0))              as effective_tax_rate

    -- date spine
    ,date_trunc('month',   payment_date::date)::date          as pay_month
    ,date_trunc('quarter', payment_date::date)::date          as pay_quarter
    ,extract(year from     payment_date::date)::int           as pay_year

    ,current_timestamp                                         as silver_inserted_at

from {{ ref('stg_payroll') }}