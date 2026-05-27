# CloudBridge Inc. — End-to-End SaaS Data Warehouse

A fully self-contained portfolio project demonstrating a production-grade analytics stack built from scratch: synthetic data generation, a containerized PostgreSQL warehouse, a three-layer dbt transformation project, and a Power BI dashboard on top.

The fictional company is **CloudBridge Inc.**, a B2B SaaS startup covering four fiscal years (2021–2024). Every number, name, and email is synthetic — there is no real customer data anywhere in this repo.

---

## What This Project Demonstrates

| Skill area | Evidence in this repo |
|---|---|
| Data modeling strategy | Kimball-style bronze → silver → gold layers, explicit fact/dim separation |
| SQL craftsmanship | Window functions (LAG, YTD running totals), calendar spine cross-joins, double-entry GL accounting logic |
| dbt best practices | Incremental models on bronze, `ref()` lineage, YAML column-level tests, config tags & meta |
| Realistic dataset design | Seasonality curves, YoY cost growth, data grime (casing noise, trailing spaces) on text fields only |
| Financial domain knowledge | Chart of accounts, COGS vs OpEx split, standard_balance_amount sign convention, closed-period flag |
| Visualization | Power BI dashboard connected to gold layer reports |

---

## Repository Layout

```
01-new-dbt-warehouse/
├── db/
│   └── docker-compose.yml          # PostgreSQL 16 container
├── faker/
│   ├── 01-generate.py              # First-generation synthetic dataset script
│   ├── 02-generate.py              # Revised dataset with fixed financials
│   └── data/                       # Output CSVs (git-ignored)
├── dbt_project/
│   ├── dbt_project.yml             # Project config: 3-schema materialization strategy
│   ├── models/
│   │   ├── bronze/                 # Staging (incremental ingestion from raw CSVs)
│   │   ├── silver/                 # Dimensions + Facts (cleaned, typed, enriched)
│   │   └── gold/                   # Report marts (BI-ready aggregations)
│   └── seeds/                      # (optional) static seed overrides
└── viz/
    └── dashboard.pbix              # Power BI report
```

---

## 1. The Database — PostgreSQL via Docker Compose

The warehouse runs locally in a Docker container defined in [db/docker-compose.yml](db/docker-compose.yml).

```yaml
services:
  db:
    image: postgres:16-alpine
    container_name: dbt_db
    environment:
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: admin
      POSTGRES_DB: dbt_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
```

**Key decisions:**
- **Postgres 16-alpine** — lightweight image, full SQL feature parity with the window functions used in the dbt models.
- **Named volume** (`postgres_data`) — data survives container restarts during development without needing to re-seed every session.
- **Standard port 5432** — drop-in compatible with the dbt profile and any local SQL client (DBeaver, TablePlus, psql).

**To start the warehouse:**
```bash
cd db
docker compose up -d
```

The dbt profile connects to `localhost:5432 / dbt_db` with the credentials above. Raw CSVs are loaded via `psql \copy` or a simple Python loader before running dbt.

---

## 2. Synthetic Data Generation — The Faker Scripts

Both scripts in [faker/](faker/) generate the CloudBridge Inc. dataset. They were built iteratively and reflect real design thinking about what makes synthetic financial data actually useful for testing analytics pipelines.

### Design goals

- **Referential integrity** — every foreign key in a child table resolves to a record in the parent table. No orphan rows.
- **Financial realism** — revenue grows on an S-curve, costs start above revenue (startup burn) and converge by 2024, gross margin lands in the 68–74% range expected for early-stage SaaS.
- **Data grime on text only** — status fields, email addresses, and descriptions carry realistic noise (random casing, leading spaces, HTML entity swaps). IDs and numeric amounts are always clean.
- **Reproducibility** — `SEED = 42` on both `random` and `Faker` so the dataset is deterministic and dbt tests always pass.

### Tables generated (12 total)

| Table | Rows (approx.) | Description |
|---|---|---|
| `raw_chart_of_accounts` | 27 | Static GL account definitions with codes, types, subtypes |
| `raw_customers` | 500 | YoY acquisition cohorts: 60 / 110 / 175 / 155 per year |
| `raw_products` | 8 | 5 subscription tiers + 3 professional services SKUs |
| `raw_employees` | 55 | Engineering, Sales, Customer Success, G&A departments |
| `raw_vendors` | 15 | AWS, Stripe, HubSpot, Salesforce, legal, recruiting, etc. |
| `raw_subscriptions` | 500 | One subscription per customer; churn applied per-month |
| `raw_invoices` | ~24 000 | Monthly subscription renewals + lumpy PS milestone invoices |
| `raw_invoice_lines` | ~24 000 | Line-item detail for each invoice |
| `raw_payments` | ~20 000 | Cash collections for Paid invoices only |
| `raw_vendor_bills` | 720 | Monthly bills per vendor (15 vendors × 48 months) |
| `raw_payroll` | ~2 700 | Monthly salary + December year-end bonus per employee |
| `raw_journal_entries` | ~160 000 | Double-entry GL: every invoice, payment, bill, and payroll run produces balanced debit/credit pairs |

### The two scripts

**`01-generate.py`** — the initial version. Established the schema design, all seasonality multipliers, data grime functions, and the double-entry GL generation pattern. The churn model pre-assigned a random end date to 22% of subscriptions at creation time.

**`02-generate.py`** — a corrected version that fixed several financial modeling issues discovered after loading into the warehouse:
- Churn is now applied as a **2% monthly probability** during invoice generation rather than pre-assigned at creation. This produces a realistic MRR S-curve instead of a cliff.
- Engineering headcount is **split 40% COGS / 60% OpEx**, routed to account codes `5300` and `6000` respectively. This drops gross margin from an unrealistic 93% to 68–74%.
- Annual **3–5% salary raises** are applied each January, compounding over four years.
- The GL generation includes a **double-entry integrity assertion** — if any `transaction_ref` has debits ≠ credits, the script prints the violations before writing, making data quality failures visible.
- PS invoices are **lumpy milestone billing** (1–4 invoices per customer at full unit prices) rather than smooth monthly charges.

The final business sanity check printed at script completion:

```
Year   Sub Rev    PS Rev  Total Rev      COGS  Gross Profit   GM%  Payroll OpEx  Vendors OpEx       Net  Active Subs
2021   1,187,432  312,500 1,499,932  456,210    1,043,722  69.6%    2,187,440      652,100  -1,795,818          52
2022   2,341,180  498,000 2,839,180  712,440    2,126,740  74.9%    3,012,210      891,230  -1,776,700         143
2023   3,892,440  621,500 4,513,940  998,120    3,515,820  77.9%    3,876,550    1,122,080  -1,482,810         271
2024   5,187,330  710,000 5,897,330 1,287,660   4,609,670  78.2%    4,210,880    1,332,040    -933,250         382
```

---

## 3. The dbt Project — Core Modeling Strategy

The project follows a **three-layer medallion architecture** configured in [dbt_project/dbt_project.yml](dbt_project/dbt_project.yml):

```yaml
models:
  dbt_project:
    bronze:
      +materialized: incremental
      +schema: bronze
    silver:
      +materialized: table
      +schema: silver
    gold:
      +materialized: table
      +schema: gold
```

Each layer has a distinct contract with the layers above and below it.

---

### Layer 1 — Bronze (Staging)

**Purpose:** Ingest raw CSV data with minimal transformation. The only work done here is column renaming, adding an `ingestion_timestamp`, and setting up incremental loading.

**Materialization:** `incremental` — new rows from the source are appended without reprocessing the full history. The `unique_key` prevents duplicates on re-runs.

**Models (one per raw table):**

| Model | Source table |
|---|---|
| `stg_chart_of_accounts` | `raw_chart_of_accounts` |
| `stg_customers` | `raw_customers` |
| `stg_employees` | `raw_employees` |
| `stg_products` | `raw_products` |
| `stg_vendors` | `raw_vendors` |
| `stg_subscriptions` | `raw_subscriptions` |
| `stg_invoices` | `raw_invoices` |
| `stg_invoice_lines` | `raw_invoice_lines` |
| `stg_payments` | `raw_payments` |
| `stg_vendor_bills` | `raw_vendor_bills` |
| `stg_payroll` | `raw_payroll` |
| `stg_journal_entries` | `raw_journal_entries` |

Bronze models are declared as sources in `bronze_sources.yml` with `not_null` and `unique` tests on every primary key. The `stg_journal_entries` model uses a composite unique key `[entry_id, transaction_ref]` to guard against partial re-loads.

---

### Layer 2 — Silver (Dimensions and Facts)

**Purpose:** Clean, type-cast, enrich, and conform. Silver is where business logic lives. Models here are consumed both by the gold layer and directly by ad-hoc analysts.

**Materialization:** `table` — rebuilt on every dbt run, ensuring silver always reflects the full clean history without incremental complexity.

#### Dimension models

**`dim_accounts`** — Chart of accounts with typed account codes and UPPERCASE normalization. The `account_type` field (`ASSET`, `LIABILITY`, `EQUITY`, `REVENUE`, `COGS`, `OPEX`) is the master classification used throughout every financial model downstream.

**`dim_customers`** — Cleanses company names and emails, extracts `email_domain` via `split_part(billing_email, '@', 2)`, coalesces NULL industry/region to `'UNKNOWN'`. Provides the customer spine for all revenue reporting.

**`dim_employees`** — Self-join on `manager_id` to produce `manager_name` and `manager_role` on every employee row. Avoids separate lookups in fact models.

**`dim_products`** — Trimmed product catalog. Separates subscription tiers from professional services SKUs, enabling clean revenue type splits downstream.

**`dim_vendors`** — UPPERCASE vendor names and categories, integer-cast `payment_terms_days` and `expense_account_code`. Feeds into `fact_vendor_bills` for AP aging.

#### Fact models

**`fct_invoices`** — The revenue fact table. Joins invoice headers to invoice lines, computes:
- `gross_amount`, `line_discount_amount`, `calculated_line_net_amount`
- `ar_aging_bucket` — classifies unpaid invoices as Current, 1–30 Days Overdue, 31–60, 61–90, or 90+ Days
- `days_past_due` — `current_date - due_date` for open/overdue invoices
- Time dimensions: `invoice_month`, `invoice_quarter`, `invoice_year` pre-truncated for fast BI aggregation

**`fact_subscriptions`** — Subscription lifecycle model. Adds:
- `mrr` (raw) and `arr` (MRR × 12)
- `tenure_months` — months active from start to today or churn date
- `lifetime_revenue_to_date` — MRR × tenure_months
- `account_lifecycle_stage` — buckets into `NEW_CUSTOMER`, `RAMPING`, `MATURE_LOYAL`, or `CHURNED` based on tenure
- `active_mrr_baseline` — MRR for active subs, 0.0 for churned, enabling clean MRR forecasting

**`fact_journal_entries`** — The core general ledger fact. This is the financial source of truth for all P&L, balance sheet, and cash flow reports. Key columns:
- `standard_balance_amount` — applies the standard accounting sign convention automatically. Revenue and liability accounts return `credit - debit`; asset and expense accounts return `debit - credit`. This means a plain `SUM()` in any BI tool produces the correct signed P&L without extra CASE logic.
- `is_debit` — boolean for entry-level drill-down
- `is_closed_accounting_period` — true if the entry date is before the current month, enforcing read-only protection on historical books
- `net_amount` — raw `debit - credit` for reconciliation audits

**`fact_payments`** — Cash collections ledger. Standardizes payment method strings to UPPERCASE, truncates dates. Feeds the cash flow report.

**`fact_payroll`** — Employee payroll distributions with `effective_tax_rate` derived as `tax_withheld / gross_pay`. The `pay_type` column carries a YAML `accepted_values` test enforcing `['SALARY', 'BONUS', 'HOURLY', 'COMMISSION', 'SEVERANCE']`.

**`fact_vendor_bills`** — Accounts payable model. Computes:
- `is_overdue` — boolean flag for unpaid bills past due date
- `days_past_due` — aging velocity relative to `current_date`
- `bill_month`, `bill_quarter`, `bill_year` — time dimensions for spend analysis

---

### Layer 3 — Gold (Report Marts)

**Purpose:** Pre-aggregated, BI-ready report tables. Every gold model is built on silver refs only — no raw source touches. Gold models carry `config(tags=[...], meta={owner:..., sla:...})` to document ownership and freshness expectations.

#### `rpt_pl_statement` — Corporate P&L

The flagship model. Built on a **calendar × account spine cross-join** pattern that guarantees no gaps in the time series — even if a given account has zero activity in a month, it still appears with `$0` rather than a missing row. This is critical for YTD window functions.

```sql
-- SPINE: all months × all P&L accounts
report_base_matrix as (
    select c.entry_month, a.account_name, a.account_type ...
    from calendar_spine c
    cross join account_spine a
)
```

Key outputs:
- `period_amount` — monthly actuals per account
- `signed_period_amount` — revenue positive, COGS/OpEx negative (enables plain SUM for subtotals)
- `ytd_cumulative_amount` — `SUM() OVER (PARTITION BY account_name, entry_year ORDER BY entry_month)` — resets to zero every January
- `mom_variance_abs` / `mom_variance_pct` — month-over-month using `LAG(1)`
- `yoy_variance_abs` / `yoy_variance_pct` — year-over-year using `LAG(12)`
- `pct_of_revenue` — common-size P&L (each line as % of total revenue for the month)
- `budget_amount` — stubbed at `0.0` with a documented `-- BUDGET STUB` comment for when a `fact_budget` source is added
- `surrogate_key` — `md5(entry_month || '|' || account_name)` for idempotent loads

#### `rpt_balance_sheet` — Balance Sheet

Same calendar spine pattern as the P&L but scoped to `ASSET`, `LIABILITY`, `EQUITY` accounts. Uses a **running total window** to compute `closing_balance` — the cumulative sum of all period movements from the beginning of history to the current month. This correctly models that balance sheet accounts carry forward their balances across periods (unlike P&L accounts which reset each year).

```sql
closing_balance as (
    sum(period_movement) over (
        partition by account_name
        order by entry_month
        rows between unbounded preceding and current row
    )
)
```

#### `rpt_mrr` — MRR Snapshot

Joins `fact_subscriptions` → `dim_customers` → `dim_products` to produce one row per subscription with full customer and product context. Exposes `active_mrr_baseline` for forward-looking MRR models and `account_lifecycle_stage` for cohort segmentation in Power BI.

#### `rpt_revenue_summary` — Revenue by Customer & Sales Rep

Aggregated from `fct_invoices`, filtered to `PAID` status only. Joins `dim_customers` for segment/region breakdowns and `dim_employees` for sales rep attribution. Produces `gross_revenue`, `total_discounts`, `net_revenue`, and `avg_invoice_amount` per customer-month-rep combination.

#### `rpt_ar_aging` — Accounts Receivable Aging

Pivots the `ar_aging_bucket` from `fct_invoices` into a classic aging waterfall report (Current, 30, 60, 90, 90+ days). Used for cash flow forecasting and DSO calculation in Power BI.

#### `rpt_cash_flow` — Cash Flow Statement

Derived from `fact_journal_entries` scoped to cash-affecting accounts (1010 Cash, 1100 AR, 2000 AP). Groups transactions into Operating, Investing, and Financing activities using account type + transaction type classification.

#### `rpt_opex_by_vendor` — OpEx by Vendor

Joins `fact_vendor_bills` → `dim_vendors` → `dim_accounts` to break down monthly operating spend by vendor, category, and GL account. Used for vendor contract reviews and budget monitoring.

#### `rpt_payroll_burn` — Payroll Burn

Aggregates `fact_payroll` by department and cost center (COGS vs OpEx), month by month. Produces gross pay, tax withheld, net pay, and headcount figures. Supports the engineering COGS split visible in the P&L.

---

## 4. Model Lineage

```
raw CSVs (PostgreSQL)
    │
    ▼  bronze (incremental)
stg_chart_of_accounts   stg_customers   stg_employees   stg_products
stg_vendors   stg_subscriptions   stg_invoices   stg_invoice_lines
stg_payments   stg_vendor_bills   stg_payroll   stg_journal_entries
    │
    ▼  silver (table)
dim_accounts ──┐
dim_customers ─┤
dim_employees ─┤──► fact_journal_entries ──► rpt_pl_statement
dim_products ──┤                         ──► rpt_balance_sheet
dim_vendors ───┤                         ──► rpt_cash_flow
               │──► fct_invoices ──────────► rpt_revenue_summary
               │──► fact_subscriptions ────► rpt_mrr
               │──► fact_vendor_bills ─────► rpt_opex_by_vendor
               │──► fact_payroll ──────────► rpt_payroll_burn
               └──► fct_invoices ──────────► rpt_ar_aging
                                              │
                                              ▼  gold (table)
                                         Power BI (dashboard.pbix)
```

---

## 5. Visualization — Power BI

A Power BI report ([viz/dashboard.pbix](viz/dashboard.pbix)) is connected to the gold layer tables. It consumes the report marts directly — no transformations happen inside Power BI; all business logic stays in dbt. The dashboard is included in the repo as a binary artifact to demonstrate the full end-to-end stack.

---

## Quick Start

```bash
# 1. Start the database
cd db && docker compose up -d

# 2. Generate synthetic data
cd ../faker
pip install faker pandas
python 02-generate.py          # outputs CSVs to faker/data/

# 3. Load raw CSVs into PostgreSQL
# (use psql \copy, a Python loader, or DBeaver import)

# 4. Install dbt dependencies and run
cd ../dbt_project
dbt deps
dbt build                      # runs all tests + models in DAG order

# 5. Open viz/dashboard.pbix in Power BI Desktop
```

---

## Tech Stack

| Component | Technology |
|---|---|
| Database | PostgreSQL 16 (Docker) |
| Data generation | Python 3.11 + Faker + pandas |
| Transformation | dbt-core + dbt-postgres |
| Visualization | Power BI Desktop |

---

*All data is synthetic. CloudBridge Inc. does not exist. Built as a portfolio project by Ariel Mendez.*
