# Synthetic Dataset — CloudBridge Inc.

> **Purpose:** This folder contains nothing but fake data. It exists solely to simulate a realistic source system so the dbt pipeline in this repository has something to work with. No real company, customer, or financial figure is represented here.

---

## What this is

`generate.py` produces 12 CSV files that look like raw exports from the operational systems of a fictional B2B SaaS company called **CloudBridge Inc.** The data covers four full fiscal years (2021 – 2024) and is sized to feel like a real early-stage growth company: ~$3–5M ARR, 500 customers, 55 employees, 15 vendors.

The dataset is intentionally **not clean**. Categorical fields carry realistic source-system grime — inconsistent casing, trailing whitespace, nulls, HTML entity leakage — because that is what raw data looks like before a transformation layer touches it. **ID fields are always clean.**

---

## How it was built

The script uses two Python libraries:

- **`faker`** — generates realistic names, company names, and email addresses
- **`pandas`** — assembles DataFrames and writes CSVs

Generation is **deterministic**: a fixed random seed (`SEED = 42`) means every run produces the exact same output.

### Generation order

Entities are generated in dependency order so that every foreign key is valid before it is referenced:

```
1. chart_of_accounts   static — 27 accounts across Asset / Liability / Equity / Revenue / COGS / OpEx
2. customers           500 B2B companies — 4 cohorts reflecting YoY acquisition growth
3. products            5 subscription plans + 3 professional services SKUs
4. employees           55 people across Engineering, Sales, CS, and G&A
5. vendors             15 software and services vendors (AWS, Stripe, Salesforce, etc.)
──────────────────────────────────────────────────────────────────────────────────────────
6. subscriptions       1 per customer — Active or Churned, starts 0–45 days after creation
7. invoices            monthly subscription renewals + ~600 one-off PS invoices
8. invoice_lines       1 line per invoice (subscription) or 1–3 lines (PS)
9. payments            ~85% of invoices — paid 4–32 days after invoice date
10. vendor_bills        1 bill per vendor per month for 48 months — seasonal + YoY scaling
11. payroll             1 record per employee per month + December bonus records
12. journal_entries     double-entry GL pairs for every invoice, payment, bill, and payroll run
```

---

## Design features

### Customer acquisition growth curve

Customers are distributed across four annual cohorts to simulate a typical SaaS ramp:

| Cohort | Customers | Created between |
|---|---|---|
| 2021 | 60 | Jan 2021 – Dec 2021 |
| 2022 | 110 | Jan 2022 – Dec 2022 |
| 2023 | 175 | Jan 2023 – Dec 2023 |
| 2024 | 155 | Jan 2024 – Jun 2024 |

Each subscription starts 0–45 days after customer creation, so early cohorts have longer invoice histories.

### Negotiated MRR

Subscription MRR is not always list price. Segment-based discounts are applied at signing:

| Segment | Discount |
|---|---|
| SMB | 0% (list price) |
| Mid-Market | 0–10% |
| Enterprise | 10–25% |

This makes the `mrr` column in `raw_subscriptions` diverge from `unit_price` in `raw_products` — a realistic pattern that dbt must reconcile.

### Seasonality

Vendor bill amounts are scaled by a per-vendor seasonal profile and year-over-year growth. Key patterns:

- **AWS / Datadog** — peak in Q4 (year-end usage spike)
- **HubSpot / LinkedIn / Indeed** — peak in Q1 (new year pipeline push) and Q4
- **Legal fees** — peak in Q1 (annual filings) and Q4 (year-end deals)
- **All vendors** — scaled by YoY growth factor (2021: 42%, 2022: 61%, 2023: 82%, 2024: 100%)

Invoice payments also close faster in Q4 — shorter collection lags simulate end-of-year urgency.

### December bonus payroll

Each employee receives a `pay_type = 'Bonus'` payroll record in December of every year (≈25% of monthly salary, taxed at 37%). The regular monthly records have `pay_type = 'Salary'`. The dbt model needs to handle both.

### Data grime (text fields only — never IDs)

| Field | Type of grime | Rate |
|---|---|---|
| `status` (invoices, bills) | lowercase, UPPERCASE, trailing space | ~4% |
| `currency` | `usd` instead of `USD` | ~2% |
| `payment_method` | `ach`, `wire`, `credit card`, `check` | ~3% |
| `company_name` | ALL CAPS, leading/trailing spaces, double spaces | ~3% |
| `billing_email` | leading space, extra dot before `@` | ~2.5% |
| `region` | `N/A`, `Unknown`, `n/a`, empty string, null | ~5% |
| `industry` | `N/A`, `Unknown`, empty string, null | ~4% |
| `description` (bills, lines) | HTML entities, double spaces, ALL CAPS | ~3% |
| `role` (employees) | null | ~2% |

The dbt bronze layer is where you clean all of this up.

---

## What the data enables

| Layer | What happens |
|---|---|
| **Bronze** | Land CSVs as-is into PostgreSQL; add ingestion timestamp; no business logic |
| **Silver** | Normalize casing, cast types, apply business rules, build dimension tables |
| **Gold** | Star schema facts + report aggregations |

The four reports this dataset is designed to support:

| Report | Primary source tables |
|---|---|
| Sales Report | `raw_invoices`, `raw_invoice_lines`, `raw_customers`, `raw_products` |
| P&L | `raw_journal_entries` + `raw_chart_of_accounts` (Revenue / COGS / OpEx types) |
| Balance Sheet | `raw_journal_entries` + `raw_chart_of_accounts` (Asset / Liability / Equity) cumulative |
| Cash Flow | `raw_journal_entries` filtered to account `1010` (Cash) by `transaction_type` |

---

## Usage

```bash
# Install dependencies (project venv already has these)
pip install -r requirements.txt

# Generate all 12 CSVs into faker/data/
python generate.py

# Load into PostgreSQL
export DATABASE_URL=postgres://postgres:password@localhost:5432/dbt_db
bash load.sh
```

The `load.sh` script runs `schema.sql` first (creates the `raw` schema and all 12 tables), then bulk-loads each CSV via `psql \COPY`.

---

## Row counts (SEED = 42)

| Table | Rows |
|---|---|
| raw_chart_of_accounts | 27 |
| raw_customers | 500 |
| raw_products | 8 |
| raw_employees | 55 |
| raw_vendors | 15 |
| raw_subscriptions | 500 |
| raw_invoices | 9,862 |
| raw_invoice_lines | 9,862 |
| raw_payments | 8,413 |
| raw_vendor_bills | 720 |
| raw_payroll | 2,860 |
| raw_journal_entries | 47,880 |
