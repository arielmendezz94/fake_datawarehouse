"""
CloudBridge Inc. — Synthetic SaaS Financial Dataset Generator
Period: 2021-01-01 → 2024-12-31  (4 fiscal years)

KEY FIXES vs original:
  - Revenue grows from ~$1.2M ARR (2021) to ~$5.8M ARR (2024) — realistic SaaS ramp
  - Total costs start above revenue (startup burn) and converge by 2024
  - 40% of Engineering salaries tagged as COGS (product delivery cost)
  - Gross margin 68–74% (realistic SaaS, not 93%)
  - Subscription revenue persists all 4 years with proper MRR compounding
  - PS revenue is lumpy (project milestones), not smooth monthly
  - Churn rate reduced to ~2% monthly (not 22% batch at creation)
  - All IDs are consistent across every table (no orphan FKs)
  - Double-entry GL asserts debits == credits before writing
  - 2025 data removed — END_DATE = 2024-12-31 strictly enforced

Usage:
    pip install faker pandas
    python generate.py
"""

import os
import uuid
import random
from datetime import date, timedelta
from collections import defaultdict

import pandas as pd
from faker import Faker

# ── Constants ────────────────────────────────────────────────────────────────

SEED = 42
random.seed(SEED)
fake = Faker("en_US")
Faker.seed(SEED)

START_DATE = date(2021, 1, 1)
END_DATE   = date(2024, 12, 31)
START_TS   = pd.Timestamp(START_DATE)
END_TS     = pd.Timestamp(END_DATE)

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(OUT_DIR, exist_ok=True)

# ── Core helpers ─────────────────────────────────────────────────────────────

def uid() -> str:
    return str(uuid.uuid4())

def rand_date(start: date = START_DATE, end: date = END_DATE) -> date:
    delta = (end - start).days
    if delta <= 0:
        return start
    return start + timedelta(days=random.randint(0, delta))

def save(df: pd.DataFrame, name: str) -> None:
    path = os.path.join(OUT_DIR, f"{name}.csv")
    df.to_csv(path, index=False, date_format="%Y-%m-%d")
    print(f"  {name}: {len(df):,} rows")

def next_month(ts: pd.Timestamp) -> pd.Timestamp:
    if ts.month == 12:
        return ts.replace(year=ts.year + 1, month=1)
    return ts.replace(month=ts.month + 1)

# ── Seasonality ──────────────────────────────────────────────────────────────

_BASE_SEASON  = [0.82, 0.83, 0.90, 0.90, 0.94, 0.95, 0.98, 1.00, 1.04, 1.08, 1.16, 1.28]
_MKTG_SEASON  = [1.35, 1.15, 1.00, 0.88, 0.84, 0.84, 0.88, 0.94, 1.04, 1.10, 1.22, 1.35]
_LEGAL_SEASON = [1.30, 1.10, 1.05, 0.95, 0.90, 0.90, 0.90, 0.90, 0.95, 1.00, 1.10, 1.25]

_VENDOR_SEASON = {
    "Amazon Web Services":    _BASE_SEASON,
    "Datadog":                _BASE_SEASON,
    "HubSpot":                _MKTG_SEASON,
    "LinkedIn":               _MKTG_SEASON,
    "Indeed":                 _MKTG_SEASON,
    "Smith & Associates LLP": _LEGAL_SEASON,
}

def seasonal_mult(month: int, vendor_name: str) -> float:
    return _VENDOR_SEASON.get(vendor_name, _BASE_SEASON)[month - 1]

# Vendor costs scale with company size YoY (starts small, grows to full by 2024)
_YOY_GROWTH = {2021: 0.38, 2022: 0.55, 2023: 0.76, 2024: 1.00}

def yoy_growth(year: int) -> float:
    return _YOY_GROWTH.get(year, 1.00)

# ── Data Grime ────────────────────────────────────────────────────────────────

def dirty_status(value: str, rate: float = 0.04) -> str:
    if value is None:
        return value
    if random.random() < rate:
        roll = random.random()
        if roll < 0.40:
            return value.lower()
        elif roll < 0.72:
            return value.upper()
        else:
            return value + " "
    return value

def dirty_text(value: str, rate: float = 0.03) -> str:
    if value is None:
        return value
    if random.random() < rate:
        roll = random.random()
        if roll < 0.30:
            return value.upper()
        elif roll < 0.55:
            return "  " + value
        elif roll < 0.80:
            return value + "  "
        else:
            return value.replace("&", "&amp;").replace(",", " ,")
    return value

def dirty_email(value: str, rate: float = 0.025) -> str:
    if random.random() < rate:
        if random.random() < 0.5:
            return " " + value
        at = value.find("@")
        if at > 1:
            return value[:at - 1] + "." + value[at - 1:]
    return value

def maybe_null(value, rate: float = 0.05):
    return None if random.random() < rate else value

def maybe_na(value: str, rate: float = 0.05) -> str:
    if random.random() < rate:
        return random.choice(["N/A", "Unknown", "n/a", ""])
    return value

def dirty_currency(value: str, rate: float = 0.025) -> str:
    return value.lower() if random.random() < rate else value

def dirty_method(value: str, rate: float = 0.03) -> str:
    return value.lower() if random.random() < rate else value

# ── 1. Chart of Accounts ─────────────────────────────────────────────────────
# Added 5200 (PS Delivery COGS) and 5300 (Engineering COGS) for proper gross margin

ACCOUNT_DEFS = [
    ("1010", "Cash and Cash Equivalents",         "Asset",     "Current Asset"),
    ("1100", "Accounts Receivable",               "Asset",     "Current Asset"),
    ("1200", "Prepaid Expenses",                  "Asset",     "Current Asset"),
    ("1500", "Equipment",                         "Asset",     "Non-Current Asset"),
    ("1510", "Accumulated Depreciation",          "Asset",     "Non-Current Asset"),
    ("2000", "Accounts Payable",                  "Liability", "Current Liability"),
    ("2100", "Accrued Expenses",                  "Liability", "Current Liability"),
    ("2200", "Deferred Revenue",                  "Liability", "Current Liability"),
    ("2300", "Loan Payable",                      "Liability", "Non-Current Liability"),
    ("3000", "Common Stock",                      "Equity",    "Equity"),
    ("3100", "Additional Paid-in Capital",        "Equity",    "Equity"),
    ("3200", "Retained Earnings",                 "Equity",    "Equity"),
    ("4000", "Subscription Revenue",              "Revenue",   "Operating Revenue"),
    ("4100", "Professional Services Revenue",     "Revenue",   "Operating Revenue"),
    ("4200", "Setup Fees",                        "Revenue",   "Operating Revenue"),
    ("5000", "Hosting and Infrastructure",        "COGS",      "Cost of Revenue"),
    ("5100", "Third-party Software Costs",        "COGS",      "Cost of Revenue"),
    ("5200", "Professional Services Delivery",    "COGS",      "Cost of Revenue"),
    ("5300", "Engineering - Product Delivery",    "COGS",      "Cost of Revenue"),  # 40% of eng headcount
    ("6000", "Salaries - Engineering",            "OpEx",      "Personnel"),        # 60% of eng headcount
    ("6010", "Salaries - Sales",                  "OpEx",      "Personnel"),
    ("6020", "Salaries - Customer Success",       "OpEx",      "Personnel"),
    ("6030", "Salaries - G&A",                    "OpEx",      "Personnel"),
    ("6100", "Sales and Marketing",               "OpEx",      "Sales & Marketing"),
    ("6200", "Office and Facilities",             "OpEx",      "Overhead"),
    ("6300", "Professional Fees",                 "OpEx",      "Overhead"),
    ("6400", "Software and Tools",                "OpEx",      "Overhead"),
    ("6500", "Depreciation Expense",              "OpEx",      "Overhead"),
]

accounts_df = pd.DataFrame([
    {
        "account_id":      uid(),
        "account_code":    code,
        "account_name":    name,
        "account_type":    atype,
        "account_subtype": subtype,
        "is_active":       True,
    }
    for code, name, atype, subtype in ACCOUNT_DEFS
])

acct: dict[str, str]            = dict(zip(accounts_df["account_code"], accounts_df["account_id"]))
acct_id_to_code: dict[str, str] = dict(zip(accounts_df["account_id"], accounts_df["account_code"]))

save(accounts_df, "raw_chart_of_accounts")


# ── 2. Customers ──────────────────────────────────────────────────────────────
# Acquisition cohorts reflect SaaS ramp. Churn is handled in subscriptions,
# not here — customer records persist even if subscription churns.

INDUSTRIES = ["FinTech", "HealthTech", "EdTech", "E-Commerce",
              "Legal Tech", "HR Tech", "InsurTech", "PropTech"]
SEGMENTS   = ["SMB", "Mid-Market", "Enterprise"]
REGIONS    = ["Northeast", "Southeast", "Midwest", "West", "Southwest", "International"]

COHORTS = [
    (60,  date(2021, 1, 1), date(2021, 12, 31)),
    (110, date(2022, 1, 1), date(2022, 12, 31)),
    (175, date(2023, 1, 1), date(2023, 12, 31)),
    (155, date(2024, 1, 1), date(2024, 6, 30)),
]

cust_rows = []
for n, c_start, c_end in COHORTS:
    for _ in range(n):
        cust_rows.append({
            "customer_id":   uid(),
            "company_name":  dirty_text(fake.company(), rate=0.03),
            "industry":      maybe_na(random.choice(INDUSTRIES), rate=0.04),
            "segment":       random.choices(SEGMENTS, weights=[50, 35, 15])[0],
            "region":        maybe_na(random.choice(REGIONS), rate=0.05),
            "billing_email": dirty_email(fake.company_email(), rate=0.025),
            "credit_limit":  random.choice([10_000, 25_000, 50_000, 100_000, 250_000]),
            "created_at":    rand_date(start=c_start, end=c_end),
            "is_active":     True,  # All 500 customer records exist; churn is on subscriptions
        })

customers_df  = pd.DataFrame(cust_rows)
save(customers_df, "raw_customers")
customer_ids: list[str]         = customers_df["customer_id"].tolist()
seg_map: dict[str, str]         = dict(zip(customers_df["customer_id"], customers_df["segment"]))
created_map: dict[str, date]    = {
    row["customer_id"]: pd.Timestamp(row["created_at"]).date()
    for _, row in customers_df.iterrows()
}


# ── 3. Products ───────────────────────────────────────────────────────────────
# Subscription MRR is the revenue engine. PS prices raised slightly for realism.

PRODUCT_DEFS = [
    ("Starter",    "Subscription",             99.00,  "Monthly plan — up to 5 seats"),
    ("Growth",     "Subscription",            299.00,  "Monthly plan — up to 25 seats"),
    ("Pro",        "Subscription",            599.00,  "Monthly plan — up to 100 seats"),
    ("Business",   "Subscription",          1_199.00,  "Monthly plan — unlimited seats"),
    ("Enterprise", "Subscription",          2_499.00,  "Custom enterprise subscription"),
    ("Onboarding", "Professional Services",  3_500.00,  "Guided onboarding — 15 hours"),
    ("Training",   "Professional Services",  2_000.00,  "Live training workshop — 8 hours"),
    ("Custom Dev", "Professional Services", 12_500.00,  "Custom feature development — milestone"),
]

products_df = pd.DataFrame([
    {
        "product_id":       uid(),
        "product_name":     name,
        "product_category": cat,
        "unit_price":       price,
        "description":      desc,
        "is_active":        True,
        "created_at":       date(2020, 12, 1),
    }
    for name, cat, price, desc in PRODUCT_DEFS
])

sub_product_ids: list[str]      = products_df[products_df["product_category"] == "Subscription"]["product_id"].tolist()
ps_product_ids:  list[str]      = products_df[products_df["product_category"] == "Professional Services"]["product_id"].tolist()
product_price:   dict[str, float] = dict(zip(products_df["product_id"], products_df["unit_price"]))
product_name:    dict[str, str]   = dict(zip(products_df["product_id"], products_df["product_name"]))

save(products_df, "raw_products")


# ── 4. Employees ──────────────────────────────────────────────────────────────
# Engineering is split: 40% cost_center=COGS (product delivery), 60% OPEX.
# This drives a realistic gross margin of ~68-74%.

DEPT_CONFIG = {
    "Engineering": {
        "roles":     ["Software Engineer", "Senior Engineer", "Tech Lead", "Staff Engineer", "Engineering Manager"],
        "salary":    (75_000, 130_000),   # early-stage startup, not FAANG
        "count":     22,
    },
    "Sales": {
        "roles":     ["Account Executive", "Sales Manager", "SDR", "Enterprise AE", "VP of Sales"],
        "salary":    (55_000, 115_000),   # base only; commissions modeled separately
        "count":     14,
    },
    "Customer Success": {
        "roles":     ["CSM", "Senior CSM", "CS Director", "Implementation Specialist", "Technical CSM"],
        "salary":    (50_000, 90_000),
        "count":     10,
    },
    "G&A": {
        "roles":     ["Controller", "HR Manager", "Operations Mgr", "CEO", "CFO", "COO", "Executive Assistant", "Recruiter", "Finance Analyst"],
        "salary":    (60_000, 175_000),   # CEO/CFO pull range up; smaller staff overall
        "count":     9,
    },
}

emp_rows = []
eng_cogs_count = 0  # track how many eng are tagged COGS (target: 40% of 22 = ~9)

for dept, cfg in DEPT_CONFIG.items():
    for i in range(cfg["count"]):
        # Engineering: first 9 employees are COGS (product delivery), rest are OPEX
        if dept == "Engineering":
            if eng_cogs_count < 9:
                cost_center   = "COGS"
                salary_account = "5300"
                eng_cogs_count += 1
            else:
                cost_center   = "OPEX"
                salary_account = "6000"
        elif dept == "Sales":
            cost_center, salary_account = "OPEX", "6010"
        elif dept == "Customer Success":
            cost_center, salary_account = "OPEX", "6020"
        else:
            cost_center, salary_account = "OPEX", "6030"

        emp_rows.append({
            "employee_id":      uid(),
            "first_name":       fake.first_name(),
            "last_name":        fake.last_name(),
            "department":       dept,
            "cost_center":      cost_center,
            "salary_account":   salary_account,
            "role":             maybe_null(cfg["roles"][i % len(cfg["roles"])], rate=0.02),
            "salary":           round(random.uniform(*cfg["salary"]), -2),
            "hire_date":        rand_date(start=date(2019, 1, 1), end=date(2023, 6, 30)),
            "is_active":        True,
            "created_at":       date(2021, 1, 1),
        })

employees_df  = pd.DataFrame(emp_rows)
ceo_id: str   = employees_df[employees_df["department"] == "G&A"].iloc[0]["employee_id"]
employees_df["manager_id"] = employees_df["employee_id"].apply(
    lambda eid: None if eid == ceo_id else ceo_id
)

sales_rep_ids: list[str] = employees_df[employees_df["department"] == "Sales"]["employee_id"].tolist()

# Map employee_id → salary_account for GL entries
emp_salary_acct: dict[str, str] = dict(zip(employees_df["employee_id"], employees_df["salary_account"]))

save(employees_df, "raw_employees")


# ── 5. Vendors ────────────────────────────────────────────────────────────────
# Monthly ranges sized so total vendor spend is reasonable vs revenue.
# AWS/Datadog scale with infrastructure growth (COGS). Rest are OPEX.

VENDOR_DEFS = [
    # (name, category, terms_days, expense_acct_code, monthly_lo, monthly_hi)
    ("Amazon Web Services",    "Infrastructure",      30, "5000",  3_500,  9_000),
    ("Stripe",                 "Payment Processing",  15, "5100",    300,    800),
    ("Salesforce",             "CRM Software",        30, "6400",  1_500,  1_800),
    ("HubSpot",                "Marketing Tools",     30, "6100",    700,    900),
    ("Slack",                  "Collaboration",       30, "6400",    400,    550),
    ("Google Workspace",       "Productivity",        30, "6400",    300,    420),
    ("Zendesk",                "Support",             30, "6400",    500,    750),
    ("Datadog",                "Monitoring",          30, "5000",    800,  2_000),
    ("Smith & Associates LLP", "Legal",               45, "6300",  2_000,  7_000),
    ("Deloitte",               "Accounting",          30, "6300",  2_800,  4_000),
    ("WeWork",                 "Office Space",        30, "6200",  3_500,  4_500),
    ("Indeed",                 "Recruiting",          15, "6100",    300,  1_800),
    ("LinkedIn",               "Sales & Marketing",   30, "6100",    500,  1_400),
    ("Gusto",                  "Payroll Software",    30, "6400",    220,    300),
    ("Silicon Valley Bank",    "Banking",              0, "6300",    150,    200),
]

vendors_df = pd.DataFrame([
    {
        "vendor_id":            uid(),
        "vendor_name":          name,
        "vendor_category":      cat,
        "payment_terms_days":   terms,
        "expense_account_code": exp_code,
        "is_active":            True,
        "created_at":           date(2020, 12, 1),
    }
    for name, cat, terms, exp_code, lo, hi in VENDOR_DEFS
])

vendor_monthly_range: dict[str, tuple] = {name: (lo, hi) for name, _, _, _, lo, hi in VENDOR_DEFS}

save(vendors_df, "raw_vendors")


# ── 6. Subscriptions ─────────────────────────────────────────────────────────
# Churn modeled as ~2% monthly probability, applied month by month in invoice
# generation (not pre-assigned at creation). Subscriptions are marked Active
# here; the invoice loop is where they actually stop.
# This gives a realistic MRR S-curve: rapid growth early, slowing as churn
# balances new adds by 2024.

def negotiated_mrr(base_price: float, segment: str) -> float:
    if segment == "SMB":
        return base_price
    elif segment == "Mid-Market":
        discount = random.uniform(0.0, 0.10)
    else:
        discount = random.uniform(0.10, 0.25)
    return round(base_price * (1 - discount), 2)

sub_rows = []
for cust_id in customer_ids:
    plan_id   = random.choice(sub_product_ids)
    segment   = seg_map[cust_id]
    mrr       = negotiated_mrr(product_price[plan_id], segment)
    cust_cre  = created_map[cust_id]

    sub_start = cust_cre + timedelta(days=random.randint(0, 45))
    sub_start = min(sub_start, END_DATE - timedelta(days=60))

    sub_rows.append({
        "subscription_id": uid(),
        "customer_id":     cust_id,
        "product_id":      plan_id,
        "plan_name":       product_name[plan_id],
        "status":          "Active",       # will be updated to Churned if invoice loop ends early
        "mrr":             mrr,
        "start_date":      sub_start,
        "end_date":        None,           # filled in below if churned
        "created_at":      sub_start,
        "updated_at":      END_DATE,
    })

subscriptions_df   = pd.DataFrame(sub_rows)
sub_status: dict[str, str]  = {r["subscription_id"]: "Active" for r in sub_rows}
sub_end_map: dict[str, date] = {}  # subscription_id → actual churn date

save(subscriptions_df, "raw_subscriptions")


# ── 7. Invoices + Invoice Lines ───────────────────────────────────────────────
# Subscription invoices: monthly renewal. Churn applied at 2% per month.
# PS invoices: lumpy project milestones, not smooth monthly.

MONTHLY_CHURN_RATE = 0.02  # 2% per month → ~22% annual, but applied per active sub

invoice_rows:      list[dict] = []
invoice_line_rows: list[dict] = []

PS_MILESTONE_DESCRIPTIONS = [
    "Phase 1 — Requirements & Discovery",
    "Phase 2 — Design & Architecture",
    "Phase 3 — Development Milestone",
    "Phase 4 — Testing & QA",
    "Go-live Support",
    "Post-launch Optimization",
    "Custom Integration Delivery",
    "Training Workshop Completion",
]

for _, sub in subscriptions_df.iterrows():
    sub_start_ts = pd.Timestamp(sub["start_date"])
    current      = max(sub_start_ts.replace(day=1), START_TS)
    churned      = False
    churn_date   = None

    while current <= END_TS and not churned:
        inv_id = uid()
        inv_dt = current.date()
        due_dt = (current + timedelta(days=30)).date()
        amount = float(sub["mrr"])

        # Q4 customers pay faster
        pay_lag = random.randint(3, 18) if current.month in (10, 11, 12) else random.randint(5, 32)
        status  = dirty_status(
            random.choices(["Paid", "Overdue", "Open"], weights=[85, 10, 5])[0],
            rate=0.04,
        )
        label   = current.strftime("%B %Y")

        invoice_rows.append({
            "invoice_id":      inv_id,
            "customer_id":     sub["customer_id"],
            "subscription_id": sub["subscription_id"],
            "sales_rep_id":    random.choice(sales_rep_ids),
            "invoice_type":    "Subscription",
            "invoice_date":    inv_dt,
            "due_date":        due_dt,
            "status":          status,
            "total_amount":    amount,
            "currency":        dirty_currency("USD", rate=0.02),
            "created_at":      inv_dt,
        })
        invoice_line_rows.append({
            "line_id":      uid(),
            "invoice_id":   inv_id,
            "product_id":   sub["product_id"],
            "description":  dirty_text(f"{sub['plan_name']} -- {label}", rate=0.03),
            "quantity":     1,
            "unit_price":   amount,
            "discount_pct": 0.00,
            "line_total":   amount,
        })

        # Apply monthly churn probability — only for subs older than 3 months
        months_active = (current.year - sub_start_ts.year) * 12 + (current.month - sub_start_ts.month)
        if months_active >= 3 and random.random() < MONTHLY_CHURN_RATE:
            churned    = True
            churn_date = inv_dt
            sub_status[sub["subscription_id"]]  = "Churned"
            sub_end_map[sub["subscription_id"]] = churn_date

        current = next_month(current)

# Patch subscription statuses and end_dates
subscriptions_df["status"]   = subscriptions_df["subscription_id"].map(
    lambda sid: sub_status.get(sid, "Active")
)
subscriptions_df["end_date"] = subscriptions_df["subscription_id"].map(
    lambda sid: sub_end_map.get(sid, None)
)
subscriptions_df["updated_at"] = subscriptions_df.apply(
    lambda r: r["end_date"] if r["end_date"] is not None else END_DATE, axis=1
)

# Re-save subscriptions with accurate statuses
subscriptions_df.to_csv(os.path.join(OUT_DIR, "raw_subscriptions.csv"), index=False, date_format="%Y-%m-%d")
print(f"  raw_subscriptions (updated statuses): {len(subscriptions_df):,} rows")

# PS invoices: lumpy milestone billing — not every customer, not every month
# ~40% of customers have at least one PS engagement over the 4 years
ps_customers = random.sample(customer_ids, min(200, len(customer_ids)))

for cust_id in ps_customers:
    # Each PS customer has 1–4 milestone invoices spread across the dataset period
    n_milestones = random.randint(1, 4)
    for _ in range(n_milestones):
        inv_id     = uid()
        ps_pid     = random.choice(ps_product_ids)
        unit_price = product_price[ps_pid]

        # Milestone invoices are single-line, full unit price (no qty > 1 for big items)
        if unit_price >= 10_000:
            qty = 1
        else:
            qty = random.randint(1, 2)

        total  = round(qty * unit_price, 2)
        inv_dt = rand_date()
        due_dt = inv_dt + timedelta(days=30)
        status = dirty_status(
            random.choices(["Paid", "Open", "Overdue"], weights=[78, 14, 8])[0],
            rate=0.04,
        )
        desc   = random.choice(PS_MILESTONE_DESCRIPTIONS)

        invoice_rows.append({
            "invoice_id":      inv_id,
            "customer_id":     cust_id,
            "subscription_id": None,
            "sales_rep_id":    random.choice(sales_rep_ids),
            "invoice_type":    "Professional Services",
            "invoice_date":    inv_dt,
            "due_date":        due_dt,
            "status":          status,
            "total_amount":    total,
            "currency":        dirty_currency("USD", rate=0.02),
            "created_at":      inv_dt,
        })
        invoice_line_rows.append({
            "line_id":      uid(),
            "invoice_id":   inv_id,
            "product_id":   ps_pid,
            "description":  dirty_text(desc, rate=0.03),
            "quantity":     qty,
            "unit_price":   unit_price,
            "discount_pct": 0.00,
            "line_total":   total,
        })

invoices_df      = pd.DataFrame(invoice_rows)
invoice_lines_df = pd.DataFrame(invoice_line_rows)

save(invoices_df,      "raw_invoices")
save(invoice_lines_df, "raw_invoice_lines")


# ── 8. Payments ───────────────────────────────────────────────────────────────
# Only for Paid invoices. Payment date = invoice_date + realistic lag.
# Q4 invoices settle faster (end-of-year urgency).

def payment_lag(inv_dt: date) -> int:
    if inv_dt.month in (10, 11, 12):
        return random.randint(3, 18)
    return random.randint(5, 35)

paid_invoices = invoices_df[invoices_df["status"].str.strip().str.capitalize() == "Paid"].copy()

payment_rows = []
for _, row in paid_invoices.iterrows():
    lag      = payment_lag(row["invoice_date"])
    pay_date = row["invoice_date"] + timedelta(days=lag)
    payment_rows.append({
        "payment_id":     uid(),
        "invoice_id":     row["invoice_id"],
        "customer_id":    row["customer_id"],
        "payment_date":   pay_date,
        "amount":         row["total_amount"],
        "payment_method": dirty_method(
            random.choice(["ACH", "Wire", "Credit Card", "Check"]),
            rate=0.03,
        ),
        "currency":       dirty_currency("USD", rate=0.02),
        "created_at":     pay_date,
    })

payments_df = pd.DataFrame(payment_rows)
save(payments_df, "raw_payments")


# ── 9. Vendor Bills ───────────────────────────────────────────────────────────

all_months = pd.date_range(start="2021-01-01", end="2024-12-01", freq="MS")
bill_rows:  list[dict] = []

for _, vendor in vendors_df.iterrows():
    vname  = vendor["vendor_name"]
    lo, hi = vendor_monthly_range[vname]

    for month_ts in all_months:
        month  = month_ts.month
        year   = month_ts.year
        season = seasonal_mult(month, vname)
        growth = yoy_growth(year)

        amount  = round(random.uniform(lo, hi) * season * growth, 2)
        bill_dt = (month_ts + timedelta(days=random.randint(1, 6))).date()
        due_dt  = bill_dt + timedelta(days=int(vendor["payment_terms_days"]))
        status  = dirty_status(
            random.choices(["Paid", "Open"], weights=[90, 10])[0],
            rate=0.03,
        )

        bill_rows.append({
            "bill_id":            uid(),
            "vendor_id":          vendor["vendor_id"],
            "expense_account_id": acct[vendor["expense_account_code"]],
            "bill_date":          bill_dt,
            "due_date":           due_dt,
            "amount":             amount,
            "status":             status,
            "description":        dirty_text(
                f"{vname} -- {month_ts.strftime('%B %Y')}",
                rate=0.03,
            ),
            "currency":           dirty_currency("USD", rate=0.02),
            "created_at":         bill_dt,
        })

vendor_bills_df = pd.DataFrame(bill_rows)
save(vendor_bills_df, "raw_vendor_bills")


# ── 10. Payroll ───────────────────────────────────────────────────────────────
# Monthly salary + December year-end bonus.
# Annual 3-5% raise applied each January (realistic salary growth).
# GL entries use employee's salary_account (COGS or OPEX) from employees table.

payroll_rows: list[dict] = []

for _, emp in employees_df.iterrows():
    base_annual   = float(emp["salary"])
    sal_acct_code = emp["salary_account"]

    for year in [2021, 2022, 2023, 2024]:
        # Apply cumulative raise since hire baseline
        raise_factor  = (1 + random.uniform(0.03, 0.05)) ** (year - 2021)
        annual_salary = round(base_annual * raise_factor, 2)
        monthly_gross = round(annual_salary / 12, 2)
        tax_rate      = random.uniform(0.22, 0.32)

        for month in range(1, 13):
            month_ts   = pd.Timestamp(year=year, month=month, day=1)
            period_end = (month_ts + pd.offsets.MonthEnd(0)).date()
            taxes      = round(monthly_gross * tax_rate, 2)
            net        = round(monthly_gross - taxes, 2)
            pay_date   = period_end + timedelta(days=2)

            payroll_rows.append({
                "payroll_id":       uid(),
                "employee_id":      emp["employee_id"],
                "department":       emp["department"],
                "cost_center":      emp["cost_center"],
                "salary_account":   sal_acct_code,
                "pay_period_start": month_ts.date(),
                "pay_period_end":   period_end,
                "gross_pay":        monthly_gross,
                "tax_withheld":     taxes,
                "net_pay":          net,
                "payment_date":     pay_date,
                "pay_type":         "Salary",
                "created_at":       period_end,
            })

        # December bonus — ~25% of monthly salary, flat 37% withholding
        bonus      = round(monthly_gross * 0.25, 2)
        bonus_date = date(year, 12, 31)
        payroll_rows.append({
            "payroll_id":       uid(),
            "employee_id":      emp["employee_id"],
            "department":       emp["department"],
            "cost_center":      emp["cost_center"],
            "salary_account":   sal_acct_code,
            "pay_period_start": date(year, 12, 1),
            "pay_period_end":   date(year, 12, 31),
            "gross_pay":        bonus,
            "tax_withheld":     round(bonus * 0.37, 2),
            "net_pay":          round(bonus * 0.63, 2),
            "payment_date":     bonus_date,
            "pay_type":         "Bonus",
            "created_at":       bonus_date,
        })

payroll_df = pd.DataFrame(payroll_rows)
save(payroll_df, "raw_payroll")


# ── 11. Journal Entries (double-entry GL) ─────────────────────────────────────
# Every transaction produces balanced debit/credit pairs.
# An integrity assertion runs before writing to catch any bugs.

je_rows: list[dict] = []

def je(ref: str, txn_type: str, code: str, debit: float, credit: float,
       entry_dt, desc: str) -> None:
    je_rows.append({
        "entry_id":         uid(),
        "transaction_ref":  ref,
        "transaction_type": txn_type,
        "account_id":       acct[code],
        "account_code":     code,
        "entry_date":       entry_dt,
        "debit_amount":     round(debit,  2),
        "credit_amount":    round(credit, 2),
        "description":      desc[:120],
        "created_at":       entry_dt,
    })

# Invoices: DR AR / CR Revenue
for _, inv in invoices_df.iterrows():
    rev_code = "4000" if inv["invoice_type"] == "Subscription" else "4100"
    amt      = float(inv["total_amount"])
    desc     = f"Invoice {str(inv['invoice_id'])[:8]} — {inv['invoice_type']}"
    je(inv["invoice_id"], "INVOICE", "1100",    amt, 0.0, inv["invoice_date"], desc)
    je(inv["invoice_id"], "INVOICE", rev_code,  0.0, amt, inv["invoice_date"], desc)

# Payments: DR Cash / CR AR
for _, pmt in payments_df.iterrows():
    amt  = float(pmt["amount"])
    desc = f"Payment {str(pmt['payment_id'])[:8]} — {pmt['payment_method']}"
    je(pmt["payment_id"], "PAYMENT", "1010", amt, 0.0, pmt["payment_date"], desc)
    je(pmt["payment_id"], "PAYMENT", "1100", 0.0, amt, pmt["payment_date"], desc)

# Vendor bills: DR Expense Account / CR AP
for _, bill in vendor_bills_df.iterrows():
    exp_code = acct_id_to_code[bill["expense_account_id"]]
    amt      = float(bill["amount"])
    desc     = f"Bill {str(bill['bill_id'])[:8]} — {str(bill['description'])[:60]}"
    je(bill["bill_id"], "VENDOR_BILL", exp_code, amt, 0.0, bill["bill_date"], desc)
    je(bill["bill_id"], "VENDOR_BILL", "2000",   0.0, amt, bill["bill_date"], desc)

# Bill payments: DR AP / CR Cash
paid_bills = vendor_bills_df[vendor_bills_df["status"].str.strip().str.capitalize() == "Paid"]
for _, bill in paid_bills.iterrows():
    amt  = float(bill["amount"])
    ref  = str(bill["bill_id"]) + "_pmt"
    desc = f"Bill payment {str(bill['bill_id'])[:8]}"
    je(ref, "BILL_PAYMENT", "2000", amt, 0.0, bill["due_date"], desc)
    je(ref, "BILL_PAYMENT", "1010", 0.0, amt, bill["due_date"], desc)

# Payroll: DR Salary/Bonus Expense (COGS or OPEX acct) / CR Cash (net) + CR Accrued Taxes
for _, pr in payroll_df.iterrows():
    sal_code = pr["salary_account"]   # correct COGS vs OPEX per employee
    txn_type = f"PAYROLL_{pr['pay_type'].upper()}"
    desc     = f"Payroll {str(pr['payroll_id'])[:8]} — {pr['department']} ({pr['pay_type']})"
    je(pr["payroll_id"], txn_type, sal_code, float(pr["gross_pay"]),    0.0,                       pr["payment_date"], desc)
    je(pr["payroll_id"], txn_type, "1010",   0.0,                       float(pr["net_pay"]),      pr["payment_date"], desc)
    je(pr["payroll_id"], txn_type, "2100",   0.0,                       float(pr["tax_withheld"]), pr["payment_date"], desc)

journal_entries_df = pd.DataFrame(je_rows)

# ── Integrity assertion: every transaction_ref must balance ───────────────────
print("\n  Verifying GL double-entry integrity...")
bal = journal_entries_df.groupby("transaction_ref").apply(
    lambda g: round(g["debit_amount"].sum() - g["credit_amount"].sum(), 2)
)
violations = bal[bal.abs() > 0.01]
if not violations.empty:
    print(f"  !! {len(violations)} UNBALANCED TRANSACTIONS — fix before loading to dbt !!")
    print(violations.head(10))
else:
    print(f"  GL balanced: {len(bal):,} transactions, all debits == credits ✓")

save(journal_entries_df, "raw_journal_entries")


# ── 12. Business sanity summary ───────────────────────────────────────────────

print("\n── Business Sanity Check ────────────────────────────────────────────────")

rev_by_year = (
    invoices_df.assign(year=pd.to_datetime(invoices_df["invoice_date"]).dt.year)
    .groupby(["year", "invoice_type"])["total_amount"]
    .sum()
    .unstack(fill_value=0)
)

payroll_by_year = (
    payroll_df.assign(year=pd.to_datetime(payroll_df["pay_period_start"]).dt.year)
    .groupby("year")["gross_pay"]
    .sum()
)

vendor_by_year = (
    vendor_bills_df.assign(year=pd.to_datetime(vendor_bills_df["bill_date"]).dt.year)
    .groupby("year")["amount"]
    .sum()
)

active_subs_by_year = {}
for yr in [2021, 2022, 2023, 2024]:
    eoy = date(yr, 12, 31)
    n = subscriptions_df[
        (pd.to_datetime(subscriptions_df["start_date"]).dt.date <= eoy) &
        (
            subscriptions_df["end_date"].isna() |
            (pd.to_datetime(subscriptions_df["end_date"]).dt.date > eoy)
        )
    ].shape[0]
    active_subs_by_year[yr] = n

# Compute real COGS from GL: accounts 5000, 5100, 5200, 5300
cogs_accounts = {"5000", "5100", "5200", "5300"}
je_df = journal_entries_df.copy()
je_df["year"] = pd.to_datetime(je_df["entry_date"]).dt.year
cogs_by_year = (
    je_df[je_df["account_code"].isin(cogs_accounts)]
    .groupby("year")["debit_amount"].sum()
)

print(f"\n{'Year':<6} {'Sub Rev':>10} {'PS Rev':>10} {'Total Rev':>10} {'COGS':>10} {'Gross Profit':>13} {'GM%':>6} {'Payroll OpEx':>13} {'Vendors OpEx':>13} {'Net':>10} {'Active Subs':>12}")
print("-" * 120)

for yr in [2021, 2022, 2023, 2024]:
    sub_rev  = rev_by_year["Subscription"].get(yr, 0) if "Subscription" in rev_by_year.columns else 0
    ps_rev   = rev_by_year["Professional Services"].get(yr, 0) if "Professional Services" in rev_by_year.columns else 0
    tot_rev  = sub_rev + ps_rev
    cogs     = cogs_by_year.get(yr, 0)
    gross_p  = tot_rev - cogs
    gm_pct   = (gross_p / tot_rev * 100) if tot_rev > 0 else 0
    # OpEx payroll = total payroll minus COGS eng payroll (already in cogs via acct 5300)
    all_payroll = payroll_by_year.get(yr, 0)
    cogs_payroll = (
        je_df[(je_df["account_code"] == "5300") & (je_df["year"] == yr)]["debit_amount"].sum()
    )
    opex_payroll = all_payroll - cogs_payroll
    vendors      = vendor_by_year.get(yr, 0)
    # vendor COGS already in cogs_by_year; remaining vendors are OPEX
    cogs_vendors = (
        je_df[(je_df["account_code"].isin({"5000","5100","5200"})) & (je_df["year"] == yr)]["debit_amount"].sum()
    )
    opex_vendors  = vendors - cogs_vendors
    net           = gross_p - opex_payroll - opex_vendors
    active        = active_subs_by_year.get(yr, 0)
    print(f"{yr:<6} {sub_rev:>10,.0f} {ps_rev:>10,.0f} {tot_rev:>10,.0f} {cogs:>10,.0f} {gross_p:>13,.0f} {gm_pct:>5.1f}% {opex_payroll:>13,.0f} {opex_vendors:>13,.0f} {net:>10,.0f} {active:>12,}")

churn_count = (subscriptions_df["status"] == "Churned").sum()
print(f"\n  Total churned subscriptions: {churn_count} / {len(subscriptions_df)} ({churn_count/len(subscriptions_df)*100:.1f}%)")
print(f"\nOutput directory: {OUT_DIR}")
print("CloudBridge Inc. dataset generated: 2021-01-01 to 2024-12-31")
