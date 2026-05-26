WITH prepared_employees AS (
    SELECT
        employee_id
        ,upper(trim(first_name)) as first_name
        ,upper(trim(last_name)) as last_name
        ,first_name || ' ' || last_name as full_name
        ,upper(trim(department)) as employee_department
        ,upper(trim(role)) as employee_role
        ,salary::double precision as salary
        ,hire_date::date as hire_date
        ,is_active
        ,created_at::date as created_at
        ,manager_id
    FROM
        {{ref("stg_employees")}}
)

SELECT
    emp.employee_id
    ,emp.first_name
    ,emp.last_name
    ,emp.full_name
    ,emp.employee_department
    ,emp.employee_role
    ,emp.salary
    ,emp.hire_date
    ,emp.is_active
    ,emp.created_at
    ,emp.manager_id
    -- Pulls the manager's pre-concatenated full name from the CTE
    ,mgr.full_name as manager_name
    -- Pulls the manager's pre-trimmed role from the CTE
    ,mgr.employee_role as manager_role
FROM
    prepared_employees emp
LEFT JOIN
    prepared_employees mgr ON emp.manager_id = mgr.employee_id