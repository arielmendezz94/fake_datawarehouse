# dbt Project Consultation Notes
**Project:** CloudBridge Inc. — Synthetic SaaS dbt Warehouse
**Date:** 2026-05-26

---

## Session Summary

Full design walkthrough of the bronze → silver → gold medallion architecture for a 12-table synthetic SaaS financial dataset.

---

## Schema Overview

**12 raw tables in `raw` schema:**

| Table | PK | Type |
|---|---|---|
| raw_chart_of_accounts | account_id | dimension |
| raw_customers | customer_id | dimension |
| raw_products | product_id | dimension |
| raw_employees | employee_id | dimension |
| raw_vendors | vendor_id | dimension |
| raw_subscriptions | subscription_id | fact |
| raw_invoices | invoice_id | fact |
| raw_invoice_lines | line_id | fact |
| raw_payments | payment_id | fact |
| raw_vendor_bills | bill_id | fact |
| raw_payroll | payroll_id | fact |
| raw_journal_entries | entry_id | fact |

All IDs are UUIDs.

---

## Foreign Key Map

```
raw_customers        ← raw_subscriptions.customer_id
                     ← raw_invoices.customer_id
                     ← raw_payments.customer_id

raw_products         ← raw_subscriptions.product_id
                     ← raw_invoice_lines.product_id

raw_employees        ← raw_invoices.sales_rep_id        (column name mismatch — NOT employee_id)
                     ← raw_payroll.employee_id
                     ← raw_employees.manager_id         (self-join)

raw_vendors          ← raw_vendor_bills.vendor_id

raw_chart_of_accounts ← raw_vendor_bills.expense_account_id
                      ← raw_journal_entries.account_id

raw_subscriptions    ← raw_invoices.subscription_id

raw_invoices         ← raw_invoice_lines.invoice_id
                     ← raw_payments.invoice_id
                     ← raw_journal_entries.transaction_ref (only when transaction_type = 'INVOICE')
```

**Key gotchas:**
- `raw_invoices.sales_rep_id` joins to `raw_employees.employee_id` (names differ)
- `raw_journal_entries.transaction_ref` is polymorphic — always filter by `transaction_type` before joining

---

## Bronze Layer (stg_*)

**Status:** 12 SQL models built. All use `materialized='incremental'`.

**Pattern:** select * from source + `current_timestamp as ingestion_timestamp`

**Bugs found:**
- `stg_chart_of_accounts.sql` line 4: `unique_key='customer_id'` should be `unique_key='account_id'`
- `stg_schema.yml`: broken (3 duplicate `models:` blocks, no sources block, only 1 of 12 models documented)

**dbt_project.yml fix needed:**
```yaml
models:
  dbt_project:
    bronze:
      +materialized: incremental
    silver:
      +materialized: table
    gold:
      +materialized: table
```

---

## Silver Layer

### Architecture decisions

- **Kimball star schema** — facts keep IDs + measures only, NO text attributes from dims
- Silver dims: cleaned dimension tables (single source, no joins)
- Silver facts: cleaned measures, UPPER strings, cast types, derived flags — NO joins to dims
- Gold: joins dims to facts + aggregates for reports

### What silver adds vs. bronze

| Problem in raw | Fix in silver |
|---|---|
| `status` casing grime | `UPPER(TRIM(status))` |
| `currency` sometimes `'usd'` | `UPPER(TRIM(currency))` |
| `payment_method` lowercase | `UPPER(TRIM(payment_method))` |
| `industry` / `region` nulls | `COALESCE(field, 'Unknown')` |
| Dates as strings | `::date` cast |
| Split first/last name | `first_name || ' ' || last_name as full_name` |

### Silver dims (built)

| File | Source | Key additions |
|---|---|---|
| dim_customers.sql ✅ | stg_customers | COALESCE nulls, email_domain derived |
| dim_products.sql ✅ | stg_products | UPPER(product_category) |
| dim_employees.sql ✅ | stg_employees | full_name, self-join for manager_name |
| dim_vendors.sql ✅ | stg_vendors | UPPER(vendor_category) |
| dim_accounts.sql ✅ | stg_chart_of_accounts | UPPER(account_type) — critical for P&L filters |

### Silver facts (built)

| File | Source | Key derivations |
|---|---|---|
| fact_invoices.sql ✅ | stg_invoices + stg_invoice_lines | UPPER(status), ar_aging_bucket, days_past_due, is_paid, date spine |
| fact_payments.sql ✅ | stg_payments | UPPER(payment_method), ::date casts |
| fact_journal_entries.sql ✅ | stg_journal_entries + dim_accounts | standard_balance_amount (sign-flipped), is_closed_accounting_period, net_amount, date spine |
| fact_subscriptions.sql ✅ | stg_subscriptions | UPPER(status), arr = mrr*12, is_churned, tenure_months, date spine |
| fact_vendor_bills.sql | stg_vendor_bills | UPPER(status), is_overdue, days_past_due, date spine |
| fact_payroll.sql | stg_payroll | UPPER(pay_type), is_bonus, effective_tax_rate, date spine |

### fact_journal_entries — key design note

Backbone for P&L, Balance Sheet, and Cash Flow. Joins `dim_accounts` to bring in `account_type`.

`standard_balance_amount` sign convention:
- Debit-normal (ASSET, OPEX, COGS): `debit - credit`
- Credit-normal (LIABILITY, EQUITY, REVENUE): `credit - debit`

**Bug:** Line 31 uses `'EXPENSE'` — should be `'OPEX'` (dim_accounts outputs OPEX after UPPER).

`transaction_ref` is polymorphic — never join in silver, only in gold with a `transaction_type` filter.

---

## Gold Layer (rpt_*)

**Strategy:** `rpt_` prefix, `materialized: table`, pre-aggregated. One model per dashboard tab.

### Build order and readiness

| Report | Silver needed | Status |
|---|---|---|
| rpt_pl_statement | fact_journal_entries | unblocked |
| rpt_ar_aging | fact_invoices + dim_customers | unblocked |
| rpt_revenue_summary | fact_invoices + dim_customers + dim_employees | unblocked |
| rpt_balance_sheet | fact_journal_entries | unblocked |
| rpt_cash_flow | fact_journal_entries | unblocked |
| rpt_mrr | fact_subscriptions + dim_customers + dim_products | unblocked |
| rpt_opex_by_vendor | fact_vendor_bills + dim_vendors + dim_accounts | needs fact_vendor_bills |
| rpt_payroll_burn | fact_payroll + dim_employees | needs fact_payroll |

### Gold patterns

**P&L:**
```sql
select entry_month, entry_quarter, entry_year,
       account_type, account_subtype, account_name,
       sum(standard_balance_amount) as period_amount
from {{ ref('fact_journal_entries') }}
where account_type in ('REVENUE', 'COGS', 'OPEX')
group by 1,2,3,4,5,6
```

**AR Aging:**
```sql
select i.*, c.company_name, c.segment, c.region
from {{ ref('fact_invoices') }} i
left join {{ ref('dim_customers') }} c on i.customer_id = c.customer_id
where i.invoice_status != 'PAID'
```

**Balance Sheet:** Same source as P&L, filter `account_type in ('ASSET', 'LIABILITY', 'EQUITY')`, use cumulative SUM window function.

**Cash Flow:** Filter `account_code = 1010` (Cash), group by `entry_month, transaction_type`.

### GL Reconciliation
```sql
with subledger as (
    select invoice_month, sum(gross_amount) as subledger_revenue
    from {{ ref('fact_invoices') }} where invoice_status = 'PAID' group by 1
),
gl as (
    select entry_month, sum(credit_amount) as gl_revenue
    from {{ ref('fact_journal_entries') }}
    where transaction_type = 'INVOICE' and account_type = 'REVENUE' group by 1
)
select s.invoice_month, s.subledger_revenue, g.gl_revenue,
       (s.subledger_revenue - g.gl_revenue) as variance
from subledger s left join gl g on s.invoice_month = g.entry_month
```

---

## Concepts Covered

- **Medallion architecture:** Bronze (raw + timestamp) → Silver (clean + typed + derived) → Gold (aggregated + report-ready)
- **Kimball star schema:** Facts hold IDs + measures only. Dims hold attributes. Joins happen in gold, not silver.
- **Double-entry bookkeeping:** Every invoice/payment/bill/payroll generates debit+credit journal entry rows. Sub-ledger reconciles to GL.
- **Normal balance sign convention:** Assets/Expenses debit-normal; Liabilities/Equity/Revenue credit-normal.
- **Polymorphic FK:** `transaction_ref` in journal_entries can be any source ID — always filter by `transaction_type` before joining.
- **dbt incremental:** Bronze uses `unique_key` for idempotent loads. Silver/Gold use `table`.
