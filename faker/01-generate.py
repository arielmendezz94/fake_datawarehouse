"""
CloudBridge Inc. — Synthetic SaaS Financial Dataset Generator
Period: 2021-01-01 → 2024-12-31  (4 fiscal years)

Design principles:
  - YoY customer acquisition growth curve (60 / 110 / 175 / 155 cohorts)
  - Q4 subscription buying seasonality + AWS/marketing spend seasonality
  - Negotiated MRR by segment (Enterprise discounts, SMB list price)
  - Year-over-year infrastructure cost growth (company scales)
  - December bonus payroll records
  - Realistic source-system data grime on text/categorical fields (never on IDs)

Usage:
    pip install -r requirements.txt
    python generate.py
"""

import os
import uuid
import random
from datetime import date, timedelta

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
# Index 0 = January. Q4 is highest for most SaaS companies (buying season).

_BASE_SEASON    = [0.82, 0.83, 0.90, 0.90, 0.94, 0.95, 0.98, 1.00, 1.04, 1.08, 1.16, 1.28]
_MKTG_SEASON    = [1.35, 1.15, 1.00, 0.88, 0.84, 0.84, 0.88, 0.94, 1.04, 1.10, 1.22, 1.35]
_LEGAL_SEASON   = [1.30, 1.10, 1.05, 0.95, 0.90, 0.90, 0.90, 0.90, 0.95, 1.00, 1.10, 1.25]

_VENDOR_SEASON = {
    "Amazon Web Services": _BASE_SEASON,
    "Datadog":             _BASE_SEASON,
    "HubSpot":             _MKTG_SEASON,
    "LinkedIn":            _MKTG_SEASON,
    "Indeed":              _MKTG_SEASON,
    "Smith & Associates LLP": _LEGAL_SEASON,
}

def seasonal_mult(month: int, vendor_name: str) -> float:
    profile = _VENDOR_SEASON.get(vendor_name, _BASE_SEASON)
    return profile[month - 1]

# Infrastructure + headcount costs scale with company size YoY.
_YOY_GROWTH = {2021: 0.42, 2022: 0.61, 2023: 0.82, 2024: 1.00}

def yoy_growth(year: int) -> float:
    return _YOY_GROWTH.get(year, 1.00)

# ── Data Grime ────────────────────────────────────────────────────────────────
# Applied ONLY to text/categorical fields — never to any *_id column.

def dirty_status(value: str, rate: float = 0.04) -> str:
    """Randomly lowercase, uppercase, or add trailing space."""
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
    """Leading whitespace, ALL CAPS, double spaces, or HTML entity swap."""
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
    """Leading space or rogue extra dot before the @."""
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

# ── 1. Chart of Accounts (static) ────────────────────────────────────────────

ACCOUNT_DEFS = [
    ("1010", "Cash and Cash Equivalents",      "Asset",     "Current Asset"),
    ("1100", "Accounts Receivable",             "Asset",     "Current Asset"),
    ("1200", "Prepaid Expenses",                "Asset",     "Current Asset"),
    ("1500", "Equipment",                       "Asset",     "Non-Current Asset"),
    ("1510", "Accumulated Depreciation",        "Asset",     "Non-Current Asset"),
    ("2000", "Accounts Payable",                "Liability", "Current Liability"),
    ("2100", "Accrued Expenses",                "Liability", "Current Liability"),
    ("2200", "Deferred Revenue",                "Liability", "Current Liability"),
    ("2300", "Loan Payable",                    "Liability", "Non-Current Liability"),
    ("3000", "Common Stock",                    "Equity",    "Equity"),
    ("3100", "Additional Paid-in Capital",      "Equity",    "Equity"),
    ("3200", "Retained Earnings",               "Equity",    "Equity"),
    ("4000", "Subscription Revenue",            "Revenue",   "Operating Revenue"),
    ("4100", "Professional Services Revenue",   "Revenue",   "Operating Revenue"),
    ("4200", "Setup Fees",                      "Revenue",   "Operating Revenue"),
    ("5000", "Hosting and Infrastructure",      "COGS",      "Cost of Revenue"),
    ("5100", "Third-party Software Costs",      "COGS",      "Cost of Revenue"),
    ("5200", "Professional Services Delivery",  "COGS",      "Cost of Revenue"),
    ("6000", "Salaries - Engineering",          "OpEx",      "Personnel"),
    ("6010", "Salaries - Sales",                "OpEx",      "Personnel"),
    ("6020", "Salaries - Customer Success",     "OpEx",      "Personnel"),
    ("6030", "Salaries - G&A",                  "OpEx",      "Personnel"),
    ("6100", "Sales and Marketing",             "OpEx",      "Sales & Marketing"),
    ("6200", "Office and Facilities",           "OpEx",      "Overhead"),
    ("6300", "Professional Fees",               "OpEx",      "Overhead"),
    ("6400", "Software and Tools",              "OpEx",      "Overhead"),
    ("6500", "Depreciation Expense",            "OpEx",      "Overhead"),
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

acct: dict[str, str]         = dict(zip(accounts_df["account_code"], accounts_df["account_id"]))
acct_id_to_code: dict[str, str] = dict(zip(accounts_df["account_id"], accounts_df["account_code"]))

save(accounts_df, "raw_chart_of_accounts")


# ── 2. Customers — YoY acquisition growth curve ───────────────────────────────
# Cohorts reflect a typical early-stage SaaS growth ramp.

INDUSTRIES = [
    "FinTech", "HealthTech", "EdTech", "E-Commerce",
    "Legal Tech", "HR Tech", "InsurTech", "PropTech",
]
SEGMENTS = ["SMB", "Mid-Market", "Enterprise"]
REGIONS  = ["Northeast", "Southeast", "Midwest", "West", "Southwest", "International"]

COHORTS = [
    # (n_customers, created_from, created_to)
    (60,  date(2021, 1, 1),  date(2021, 12, 31)),
    (110, date(2022, 1, 1),  date(2022, 12, 31)),
    (175, date(2023, 1, 1),  date(2023, 12, 31)),
    (155, date(2024, 1, 1),  date(2024, 6, 30)),
]  # total = 500

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
            "is_active":     random.choices([True, False], weights=[85, 15])[0],
        })

customers_df = pd.DataFrame(cust_rows)
save(customers_df, "raw_customers")
customer_ids: list[str] = customers_df["customer_id"].tolist()


# ── 3. Products ───────────────────────────────────────────────────────────────

PRODUCT_DEFS = [
    ("Starter",    "Subscription",            99.00,   "Monthly plan — up to 5 seats"),
    ("Growth",     "Subscription",           299.00,   "Monthly plan — up to 25 seats"),
    ("Pro",        "Subscription",           599.00,   "Monthly plan — up to 100 seats"),
    ("Business",   "Subscription",         1_199.00,   "Monthly plan — unlimited seats"),
    ("Enterprise", "Subscription",         2_499.00,   "Custom enterprise subscription"),
    ("Onboarding", "Professional Services", 2_500.00,  "Guided onboarding — 10 hours"),
    ("Training",   "Professional Services", 1_500.00,  "Live training workshop — 4 hours"),
    ("Custom Dev", "Professional Services", 5_000.00,  "Custom feature development"),
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

sub_product_ids: list[str] = products_df[
    products_df["product_category"] == "Subscription"
]["product_id"].tolist()

ps_product_ids: list[str] = products_df[
    products_df["product_category"] == "Professional Services"
]["product_id"].tolist()

product_price: dict[str, float] = dict(zip(products_df["product_id"], products_df["unit_price"]))
product_name:  dict[str, str]   = dict(zip(products_df["product_id"], products_df["product_name"]))

save(products_df, "raw_products")


# ── 4. Employees ──────────────────────────────────────────────────────────────

DEPT_CONFIG = {
    "Engineering":      {
        "roles":     ["Software Engineer", "Senior Engineer", "Tech Lead", "Staff Engineer", "Engineering Manager"],
        "salary":    (90_000, 180_000),
        "count":     22,
        "acct_code": "6000",
    },
    "Sales":            {
        "roles":     ["Account Executive", "Sales Manager", "SDR", "Enterprise AE", "VP of Sales"],
        "salary":    (70_000, 160_000),
        "count":     14,
        "acct_code": "6010",
    },
    "Customer Success": {
        "roles":     ["CSM", "Senior CSM", "CS Director", "Implementation Specialist", "Technical CSM"],
        "salary":    (65_000, 120_000),
        "count":     10,
        "acct_code": "6020",
    },
    "G&A":              {
        "roles":     ["Controller", "HR Manager", "Operations Mgr", "CEO", "CFO", "COO", "Executive Assistant", "Recruiter", "Finance Analyst"],
        "salary":    (80_000, 240_000),
        "count":     9,
        "acct_code": "6030",
    },
}

emp_rows = []
for dept, cfg in DEPT_CONFIG.items():
    for i in range(cfg["count"]):
        emp_rows.append({
            "employee_id": uid(),
            "first_name":  fake.first_name(),
            "last_name":   fake.last_name(),
            "department":  dept,
            "role":        maybe_null(cfg["roles"][i % len(cfg["roles"])], rate=0.02),
            "salary":      round(random.uniform(*cfg["salary"]), -2),
            "hire_date":   rand_date(start=date(2019, 1, 1), end=date(2023, 6, 30)),
            "is_active":   True,
            "created_at":  date(2021, 1, 1),
        })

employees_df = pd.DataFrame(emp_rows)
ceo_id: str = employees_df[employees_df["department"] == "G&A"].iloc[0]["employee_id"]
employees_df["manager_id"] = employees_df["employee_id"].apply(
    lambda eid: None if eid == ceo_id else ceo_id
)

dept_salary_acct: dict[str, str] = {dept: cfg["acct_code"] for dept, cfg in DEPT_CONFIG.items()}
sales_rep_ids: list[str] = employees_df[employees_df["department"] == "Sales"]["employee_id"].tolist()

save(employees_df, "raw_employees")


# ── 5. Vendors ────────────────────────────────────────────────────────────────

VENDOR_DEFS = [
    # (name, category, terms_days, expense_acct_code, monthly_lo, monthly_hi)
    ("Amazon Web Services",    "Infrastructure",      30, "5000",  6_000, 14_000),
    ("Stripe",                 "Payment Processing",  15, "5100",    400,  1_100),
    ("Salesforce",             "CRM Software",        30, "6400",  2_000,  2_000),
    ("HubSpot",                "Marketing Tools",     30, "6100",    900,  1_000),
    ("Slack",                  "Collaboration",       30, "6400",    500,    600),
    ("Google Workspace",       "Productivity",        30, "6400",    350,    450),
    ("Zendesk",                "Support",             30, "6400",    700,    900),
    ("Datadog",                "Monitoring",          30, "5000",  1_200,  2_800),
    ("Smith & Associates LLP", "Legal",               45, "6300",  2_500,  9_000),
    ("Deloitte",               "Accounting",          30, "6300",  3_500,  4_500),
    ("WeWork",                 "Office Space",        30, "6200",  4_500,  5_500),
    ("Indeed",                 "Recruiting",          15, "6100",    400,  2_200),
    ("LinkedIn",               "Sales & Marketing",   30, "6100",    700,  1_600),
    ("Gusto",                  "Payroll Software",    30, "6400",    280,    320),
    ("Silicon Valley Bank",    "Banking",              0, "6300",    180,    220),
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


# ── 6. Subscriptions — start near customer creation, negotiated MRR ───────────

def negotiated_mrr(base_price: float, segment: str) -> float:
    """Enterprise and Mid-Market often negotiate below list price."""
    if segment == "SMB":
        return base_price
    elif segment == "Mid-Market":
        discount = random.uniform(0.0, 0.10)
    else:  # Enterprise
        discount = random.uniform(0.10, 0.25)
    return round(base_price * (1 - discount), 2)

seg_map: dict[str, str] = dict(zip(customers_df["customer_id"], customers_df["segment"]))
created_map: dict[str, date] = {
    row["customer_id"]: pd.Timestamp(row["created_at"]).date()
    for _, row in customers_df.iterrows()
}

sub_rows = []
for cust_id in customer_ids:
    plan_id    = random.choice(sub_product_ids)
    segment    = seg_map[cust_id]
    mrr        = negotiated_mrr(product_price[plan_id], segment)
    cust_cre   = created_map[cust_id]

    # Sub starts 0–45 days after customer creation; never past END_DATE - 60 days
    sub_start  = cust_cre + timedelta(days=random.randint(0, 45))
    sub_start  = min(sub_start, END_DATE - timedelta(days=60))

    is_churned = random.random() < 0.22
    if is_churned:
        churn_lo = sub_start + timedelta(days=90)
        churn_hi = min(END_DATE, sub_start + timedelta(days=36 * 30))
        if churn_lo >= churn_hi:
            churn_hi = churn_lo + timedelta(days=30)
        end = rand_date(start=churn_lo, end=churn_hi)
    else:
        end = None

    sub_rows.append({
        "subscription_id": uid(),
        "customer_id":     cust_id,
        "product_id":      plan_id,
        "plan_name":       product_name[plan_id],
        "status":          "Churned" if is_churned else "Active",
        "mrr":             mrr,
        "start_date":      sub_start,
        "end_date":        end,
        "created_at":      sub_start,
        "updated_at":      end if end else END_DATE,
    })

subscriptions_df = pd.DataFrame(sub_rows)
save(subscriptions_df, "raw_subscriptions")


# ── 7. Invoices + Invoice Lines ───────────────────────────────────────────────

invoice_rows:      list[dict] = []
invoice_line_rows: list[dict] = []

for _, sub in subscriptions_df.iterrows():
    sub_start_ts = pd.Timestamp(sub["start_date"])
    sub_end_ts   = pd.Timestamp(sub["end_date"]) if pd.notna(sub["end_date"]) else END_TS

    # Start from the first of the subscription's start month, but never before 2021-01
    current = max(sub_start_ts.replace(day=1), START_TS)

    while current <= sub_end_ts and current <= END_TS:
        inv_id = uid()
        inv_dt = current.date()
        due_dt = (current + timedelta(days=30)).date()
        amount = float(sub["mrr"])
        # Slight Q4 payment-speed uplift (customers pay faster end-of-year)
        pay_lag = random.randint(3, 20) if current.month in (10, 11, 12) else random.randint(5, 35)
        status  = dirty_status(
            random.choices(["Paid", "Overdue", "Open"], weights=[85, 10, 5])[0],
            rate=0.04,
        )
        label = current.strftime("%B %Y")

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

        current = next_month(current)

# Pro-services: ~300 customers, 1-2 invoices each
ps_customers = random.sample(customer_ids, min(300, len(customer_ids)))
for cust_id in ps_customers:
    for _ in range(random.randint(1, 2)):
        inv_id     = uid()
        ps_pid     = random.choice(ps_product_ids)
        qty        = random.randint(1, 3)
        unit_price = product_price[ps_pid]
        total      = round(qty * unit_price, 2)
        inv_dt     = rand_date()
        due_dt     = inv_dt + timedelta(days=30)
        status     = dirty_status(
            random.choices(["Paid", "Open", "Overdue"], weights=[80, 12, 8])[0],
            rate=0.04,
        )

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
            "description":  dirty_text(product_name[ps_pid], rate=0.03),
            "quantity":     qty,
            "unit_price":   unit_price,
            "discount_pct": 0.00,
            "line_total":   total,
        })

invoices_df      = pd.DataFrame(invoice_rows)
invoice_lines_df = pd.DataFrame(invoice_line_rows)

save(invoices_df, "raw_invoices")
save(invoice_lines_df, "raw_invoice_lines")


# ── 8. Payments ───────────────────────────────────────────────────────────────

paid_df = invoices_df[invoices_df["status"].str.strip().str.capitalize() == "Paid"].copy()

payments_df = pd.DataFrame([
    {
        "payment_id":     uid(),
        "invoice_id":     row["invoice_id"],
        "customer_id":    row["customer_id"],
        "payment_date":   row["invoice_date"] + timedelta(days=random.randint(4, 32)),
        "amount":         row["total_amount"],
        "payment_method": dirty_method(
            random.choice(["ACH", "Wire", "Credit Card", "Check"]),
            rate=0.03,
        ),
        "currency":       dirty_currency("USD", rate=0.02),
        "created_at":     row["invoice_date"] + timedelta(days=random.randint(4, 32)),
    }
    for _, row in paid_df.iterrows()
])

save(payments_df, "raw_payments")


# ── 9. Vendor Bills — seasonal + YoY scaling ─────────────────────────────────

all_months = pd.date_range(start="2021-01-01", end="2024-12-01", freq="MS")
bill_rows:  list[dict] = []

for _, vendor in vendors_df.iterrows():
    vname    = vendor["vendor_name"]
    lo, hi   = vendor_monthly_range[vname]

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


# ── 10. Payroll — monthly salary + December bonus ─────────────────────────────

payroll_rows: list[dict] = []

for _, emp in employees_df.iterrows():
    monthly_gross = round(float(emp["salary"]) / 12, 2)
    tax_rate      = random.uniform(0.22, 0.32)

    for month_ts in all_months:
        period_end   = (month_ts + pd.offsets.MonthEnd(0)).date()
        taxes        = round(monthly_gross * tax_rate, 2)
        net          = round(monthly_gross - taxes, 2)
        payroll_rows.append({
            "payroll_id":       uid(),
            "employee_id":      emp["employee_id"],
            "department":       emp["department"],
            "pay_period_start": month_ts.date(),
            "pay_period_end":   period_end,
            "gross_pay":        monthly_gross,
            "tax_withheld":     taxes,
            "net_pay":          net,
            "payment_date":     period_end + timedelta(days=2),
            "pay_type":         "Salary",
            "created_at":       period_end,
        })

    # December year-end bonus — ~25 % of monthly salary, taxed at flat 37 %
    for year in [2021, 2022, 2023, 2024]:
        bonus      = round(monthly_gross * 0.25, 2)
        bonus_date = date(year, 12, 31)
        payroll_rows.append({
            "payroll_id":       uid(),
            "employee_id":      emp["employee_id"],
            "department":       emp["department"],
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


# ── 11. Journal Entries (double-entry GL) ────────────────────────────────────

je_rows: list[dict] = []

def je(ref: str, txn_type: str, code: str, debit: float, credit: float, entry_dt, desc: str) -> None:
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


# Invoices: DR Accounts Receivable / CR Revenue
for _, inv in invoices_df.iterrows():
    rev_code = "4000" if inv["invoice_type"] == "Subscription" else "4100"
    amt  = float(inv["total_amount"])
    desc = f"Invoice {str(inv['invoice_id'])[:8]} — {inv['invoice_type']}"
    je(inv["invoice_id"], "INVOICE", "1100",     amt, 0.0, inv["invoice_date"], desc)
    je(inv["invoice_id"], "INVOICE", rev_code,   0.0, amt, inv["invoice_date"], desc)

# Payments: DR Cash / CR AR
for _, pmt in payments_df.iterrows():
    amt  = float(pmt["amount"])
    desc = f"Payment {str(pmt['payment_id'])[:8]} — {pmt['payment_method']}"
    je(pmt["payment_id"], "PAYMENT", "1010", amt, 0.0, pmt["payment_date"], desc)
    je(pmt["payment_id"], "PAYMENT", "1100", 0.0, amt, pmt["payment_date"], desc)

# Vendor bills: DR Expense / CR AP
for _, bill in vendor_bills_df.iterrows():
    exp_code = acct_id_to_code[bill["expense_account_id"]]
    amt  = float(bill["amount"])
    desc = f"Bill {str(bill['bill_id'])[:8]} — {str(bill['description'])[:60]}"
    je(bill["bill_id"], "VENDOR_BILL", exp_code, amt, 0.0, bill["bill_date"], desc)
    je(bill["bill_id"], "VENDOR_BILL", "2000",   0.0, amt, bill["bill_date"], desc)

# Bill payments: DR AP / CR Cash
for _, bill in vendor_bills_df[vendor_bills_df["status"].str.strip().str.capitalize() == "Paid"].iterrows():
    amt  = float(bill["amount"])
    ref  = str(bill["bill_id"]) + "_pmt"
    desc = f"Bill payment {str(bill['bill_id'])[:8]}"
    je(ref, "BILL_PAYMENT", "2000", amt, 0.0, bill["due_date"], desc)
    je(ref, "BILL_PAYMENT", "1010", 0.0, amt, bill["due_date"], desc)

# Payroll: DR Salary/Bonus Expense / CR Cash (net) + CR Accrued Expenses (taxes)
for _, pr in payroll_df.iterrows():
    sal_code = dept_salary_acct.get(pr["department"], "6030")
    desc     = f"Payroll {str(pr['payroll_id'])[:8]} — {pr['department']} ({pr['pay_type']})"
    je(pr["payroll_id"], f"PAYROLL_{pr['pay_type'].upper()}", sal_code, float(pr["gross_pay"]),    0.0,                      pr["payment_date"], desc)
    je(pr["payroll_id"], f"PAYROLL_{pr['pay_type'].upper()}", "1010",   0.0,                       float(pr["net_pay"]),     pr["payment_date"], desc)
    je(pr["payroll_id"], f"PAYROLL_{pr['pay_type'].upper()}", "2100",   0.0,                       float(pr["tax_withheld"]),pr["payment_date"], desc)

journal_entries_df = pd.DataFrame(je_rows)
save(journal_entries_df, "raw_journal_entries")


# ── Summary ───────────────────────────────────────────────────────────────────

print("\nCloudBridge Inc. dataset generated: 2021-01-01 to 2024-12-31")
print(f"Output directory: {OUT_DIR}")
