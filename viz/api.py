"""
CloudBridge Inc. — Analytics API
Serves aggregated gold-layer data to the HTML dashboard.

Usage:
    pip install fastapi uvicorn sqlalchemy psycopg2-binary python-dotenv pandas
    uvicorn api:app --reload --port 8000
"""

from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import pandas as pd
import os

# ── Credentials ──────────────────────────────────────────────────────────────
# .env lives in db/ (two levels up from viz/)
load_dotenv(dotenv_path=Path(__file__).parent.parent / "db" / ".env")

DB_USER = os.getenv("POSTGRES_USER", "admin")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "admin")
DB_NAME = os.getenv("POSTGRES_DB", "dbt_db")
DB_HOST = os.getenv("POSTGRES_HOST", "127.0.0.1")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")

# dbt target schema is "dwh"; gold custom schema becomes "dwh_gold"
GOLD = "dwh_gold"

engine = create_engine(
    f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
    pool_pre_ping=True,
)

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="CloudBridge Analytics API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Serve index.html at root
@app.get("/", include_in_schema=False)
def root():
    return FileResponse(Path(__file__).parent / "index.html")


# ── Helper ────────────────────────────────────────────────────────────────────
def sql(query: str) -> list[dict]:
    """Run a query and return JSON-safe records."""
    try:
        with engine.connect() as conn:
            df = pd.read_sql(text(query), conn)
        # Coerce all date/timestamp cols to ISO strings
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = df[col].dt.strftime("%Y-%m-%d")
            elif df[col].dtype == object:
                df[col] = df[col].where(df[col].notna(), None)
        return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── /api/kpis ─────────────────────────────────────────────────────────────────
@app.get("/api/kpis")
def kpis():
    """Top-line KPI cards: ARR, active subs, churn, cash, gross margin."""
    return sql(f"""
        SELECT
            -- MRR / ARR
            ROUND(SUM(CASE WHEN is_active THEN mrr  ELSE 0 END)::numeric, 0)
                AS current_mrr,
            ROUND(SUM(CASE WHEN is_active THEN arr  ELSE 0 END)::numeric, 0)
                AS current_arr,
            COUNT(CASE WHEN is_active  THEN 1 END)  AS active_subs,
            COUNT(CASE WHEN is_churned THEN 1 END)  AS churned_subs,
            ROUND(
                COUNT(CASE WHEN is_churned THEN 1 END)::numeric
                / NULLIF(COUNT(*), 0) * 100
            , 1)                                    AS churn_rate_pct,

            -- Avg MRR per active sub
            ROUND(
                SUM(CASE WHEN is_active THEN mrr ELSE 0 END)::numeric
                / NULLIF(COUNT(CASE WHEN is_active THEN 1 END), 0)
            , 0)                                    AS avg_mrr_per_sub

        FROM {GOLD}.rpt_mrr
    """)


@app.get("/api/kpis/financials")
def kpis_financials():
    """Gross margin % and latest cash balance from the GL."""
    gm = sql(f"""
        SELECT
            entry_year,
            ROUND(
                SUM(CASE WHEN account_type = 'REVENUE' THEN signed_period_amount ELSE 0 END)::numeric
            , 0) AS total_revenue,
            ROUND(
                SUM(CASE WHEN account_type = 'COGS' THEN ABS(signed_period_amount) ELSE 0 END)::numeric
            , 0) AS total_cogs,
            ROUND(
                (1 - SUM(CASE WHEN account_type = 'COGS' THEN ABS(signed_period_amount) ELSE 0 END)
                   / NULLIF(SUM(CASE WHEN account_type = 'REVENUE' THEN signed_period_amount ELSE 0 END), 0)
                ) * 100
            , 1) AS gross_margin_pct
        FROM {GOLD}.rpt_pl_statement
        WHERE entry_year = (SELECT MAX(entry_year) FROM {GOLD}.rpt_pl_statement)
        GROUP BY entry_year
    """)

    cash = sql(f"""
        SELECT closing_balance AS cash_balance
        FROM {GOLD}.rpt_balance_sheet
        WHERE account_name = 'CASH AND CASH EQUIVALENTS'
        ORDER BY entry_month DESC
        LIMIT 1
    """)

    return {
        "financials": gm[0] if gm else {},
        "cash_balance": cash[0]["cash_balance"] if cash else 0,
    }


# ── /api/pnl ──────────────────────────────────────────────────────────────────
@app.get("/api/pnl")
def pnl():
    """Monthly P&L: Revenue, COGS, OpEx aggregated for charting."""
    return sql(f"""
        SELECT
            entry_month,
            entry_year,
            account_type,
            ROUND(SUM(signed_period_amount)::numeric, 0) AS amount
        FROM {GOLD}.rpt_pl_statement
        GROUP BY entry_month, entry_year, account_type
        ORDER BY entry_month, account_type
    """)


@app.get("/api/pnl/detail")
def pnl_detail():
    """Monthly P&L with account-level detail for drill-down."""
    return sql(f"""
        SELECT
            entry_month,
            entry_year,
            account_type,
            account_subtype,
            account_name,
            ROUND(period_amount::numeric, 0)         AS period_amount,
            ROUND(signed_period_amount::numeric, 0)  AS signed_period_amount,
            ROUND(ytd_cumulative_amount::numeric, 0) AS ytd_amount,
            mom_variance_pct,
            yoy_variance_pct,
            ROUND(pct_of_revenue::numeric, 1)        AS pct_of_revenue
        FROM {GOLD}.rpt_pl_statement
        ORDER BY entry_month, account_type_sort_key, account_name
    """)


# ── /api/mrr ──────────────────────────────────────────────────────────────────
@app.get("/api/mrr")
def mrr():
    """Monthly subscription revenue trend (proxy for MRR movement)."""
    return sql(f"""
        SELECT
            invoice_month,
            invoice_year,
            ROUND(SUM(gross_revenue)::numeric, 0)    AS sub_revenue,
            COUNT(DISTINCT customer_id)              AS paying_customers
        FROM {GOLD}.rpt_revenue_summary
        WHERE invoice_type = 'Subscription'
        GROUP BY invoice_month, invoice_year
        ORDER BY invoice_month
    """)


@app.get("/api/mrr/by-plan")
def mrr_by_plan():
    """Current ARR broken down by subscription plan."""
    return sql(f"""
        SELECT
            plan_name,
            COUNT(*)                                 AS sub_count,
            ROUND(SUM(mrr)::numeric, 0)              AS total_mrr,
            ROUND(SUM(arr)::numeric, 0)              AS total_arr
        FROM {GOLD}.rpt_mrr
        WHERE is_active
        GROUP BY plan_name
        ORDER BY total_arr DESC
    """)


@app.get("/api/mrr/lifecycle")
def mrr_lifecycle():
    """Active MRR grouped by account lifecycle stage."""
    return sql(f"""
        SELECT
            account_lifecycle_stage,
            COUNT(*)                                 AS sub_count,
            ROUND(SUM(mrr)::numeric, 0)              AS total_mrr
        FROM {GOLD}.rpt_mrr
        WHERE is_active
        GROUP BY account_lifecycle_stage
        ORDER BY total_mrr DESC
    """)


# ── /api/revenue ──────────────────────────────────────────────────────────────
@app.get("/api/revenue/by-segment")
def revenue_by_segment():
    """Total net revenue grouped by customer segment."""
    return sql(f"""
        SELECT
            segment,
            invoice_type,
            ROUND(SUM(gross_revenue)::numeric, 0)    AS gross_revenue,
            ROUND(SUM(net_revenue)::numeric, 0)      AS net_revenue,
            COUNT(DISTINCT customer_id)              AS customer_count
        FROM {GOLD}.rpt_revenue_summary
        GROUP BY segment, invoice_type
        ORDER BY gross_revenue DESC
    """)


@app.get("/api/revenue/by-rep")
def revenue_by_rep():
    """Top sales reps by net revenue (all time)."""
    return sql(f"""
        SELECT
            sales_rep_name,
            ROUND(SUM(gross_revenue)::numeric, 0)    AS gross_revenue,
            ROUND(SUM(net_revenue)::numeric, 0)      AS net_revenue,
            COUNT(DISTINCT customer_id)              AS customers,
            SUM(invoice_count)                       AS invoices
        FROM {GOLD}.rpt_revenue_summary
        GROUP BY sales_rep_name
        ORDER BY gross_revenue DESC
        LIMIT 15
    """)


@app.get("/api/revenue/monthly")
def revenue_monthly():
    """Monthly gross revenue split by Subscription vs Professional Services."""
    return sql(f"""
        SELECT
            invoice_month,
            invoice_type,
            ROUND(SUM(gross_revenue)::numeric, 0) AS gross_revenue
        FROM {GOLD}.rpt_revenue_summary
        GROUP BY invoice_month, invoice_type
        ORDER BY invoice_month, invoice_type
    """)


# ── /api/ar-aging ─────────────────────────────────────────────────────────────
@app.get("/api/ar-aging")
def ar_aging():
    """Open AR aging buckets: invoice count and dollar exposure."""
    return sql(f"""
        SELECT
            ar_aging_bucket,
            COUNT(*)                                 AS invoice_count,
            ROUND(SUM(gross_amount)::numeric, 0)     AS total_exposure,
            ROUND(AVG(days_past_due)::numeric, 0)    AS avg_days_past_due
        FROM {GOLD}.rpt_ar_aging
        WHERE NOT is_paid_invoice
        GROUP BY ar_aging_bucket
        ORDER BY avg_days_past_due
    """)


@app.get("/api/ar-aging/by-segment")
def ar_aging_by_segment():
    """Open AR exposure grouped by customer segment."""
    return sql(f"""
        SELECT
            segment,
            ar_aging_bucket,
            COUNT(*)                                 AS invoice_count,
            ROUND(SUM(gross_amount)::numeric, 0)     AS total_exposure
        FROM {GOLD}.rpt_ar_aging
        WHERE NOT is_paid_invoice
        GROUP BY segment, ar_aging_bucket
        ORDER BY segment, avg_days_past_due
    """)


# ── /api/balance-sheet ────────────────────────────────────────────────────────
@app.get("/api/balance-sheet")
def balance_sheet():
    """Monthly closing balance by account type (Assets / Liabilities / Equity)."""
    return sql(f"""
        SELECT
            entry_month,
            entry_year,
            account_type,
            bs_section,
            ROUND(SUM(closing_balance)::numeric, 0)  AS closing_balance
        FROM {GOLD}.rpt_balance_sheet
        GROUP BY entry_month, entry_year, account_type, bs_section
        ORDER BY entry_month, section_sort_key
    """)


@app.get("/api/balance-sheet/latest")
def balance_sheet_latest():
    """Latest month closing balance by individual account."""
    return sql(f"""
        SELECT
            account_type,
            account_subtype,
            account_name,
            bs_section,
            ROUND(closing_balance::numeric, 0)       AS closing_balance
        FROM {GOLD}.rpt_balance_sheet
        WHERE entry_month = (SELECT MAX(entry_month) FROM {GOLD}.rpt_balance_sheet)
        ORDER BY section_sort_key, account_name
    """)


# ── /api/cash-flow ────────────────────────────────────────────────────────────
@app.get("/api/cash-flow")
def cash_flow():
    """Monthly net cash movement by category."""
    return sql(f"""
        SELECT
            entry_month,
            entry_year,
            cash_flow_category,
            category_sort_key,
            ROUND(total_cash_inflow::numeric, 0)     AS total_inflow,
            ROUND(total_cash_outflow::numeric, 0)    AS total_outflow,
            ROUND(net_cash_movement::numeric, 0)     AS net_movement,
            ROUND(cumulative_cash_balance::numeric, 0) AS cumulative_balance
        FROM {GOLD}.rpt_cash_flow
        ORDER BY entry_month, category_sort_key
    """)


@app.get("/api/cash-flow/summary")
def cash_flow_summary():
    """Annual cash flow summary by category."""
    return sql(f"""
        SELECT
            entry_year,
            cash_flow_category,
            ROUND(SUM(net_cash_movement)::numeric, 0) AS net_movement
        FROM {GOLD}.rpt_cash_flow
        GROUP BY entry_year, cash_flow_category
        ORDER BY entry_year, cash_flow_category
    """)


# ── /api/opex-vendor ──────────────────────────────────────────────────────────
@app.get("/api/opex-vendor")
def opex_vendor():
    """Top vendors by total spend (all time)."""
    return sql(f"""
        SELECT
            vendor_name,
            vendor_category,
            expense_account_name,
            ROUND(SUM(amount)::numeric, 0)           AS total_spend,
            COUNT(*)                                 AS bill_count,
            ROUND(AVG(amount)::numeric, 0)           AS avg_monthly_spend
        FROM {GOLD}.rpt_opex_by_vendor
        GROUP BY vendor_name, vendor_category, expense_account_name
        ORDER BY total_spend DESC
        LIMIT 15
    """)


@app.get("/api/opex-vendor/monthly")
def opex_vendor_monthly():
    """Monthly total vendor spend trend."""
    return sql(f"""
        SELECT
            bill_month,
            bill_year,
            vendor_category,
            ROUND(SUM(amount)::numeric, 0)           AS total_spend
        FROM {GOLD}.rpt_opex_by_vendor
        GROUP BY bill_month, bill_year, vendor_category
        ORDER BY bill_month, vendor_category
    """)


# ── /api/payroll ──────────────────────────────────────────────────────────────
@app.get("/api/payroll")
def payroll():
    """Monthly payroll burn by department."""
    return sql(f"""
        SELECT
            pay_month,
            pay_year,
            department,
            pay_type,
            ROUND(SUM(gross_pay)::numeric, 0)        AS gross_pay,
            ROUND(SUM(tax_withheld)::numeric, 0)     AS tax_withheld,
            ROUND(SUM(net_pay)::numeric, 0)          AS net_pay,
            COUNT(DISTINCT employee_id)              AS headcount
        FROM {GOLD}.rpt_payroll_burn
        GROUP BY pay_month, pay_year, department, pay_type
        ORDER BY pay_month, department, pay_type
    """)


@app.get("/api/payroll/annual")
def payroll_annual():
    """Annual payroll cost by department."""
    return sql(f"""
        SELECT
            pay_year,
            department,
            pay_type,
            ROUND(SUM(gross_pay)::numeric, 0)        AS gross_pay,
            COUNT(DISTINCT employee_id)              AS headcount
        FROM {GOLD}.rpt_payroll_burn
        GROUP BY pay_year, department, pay_type
        ORDER BY pay_year, department, pay_type
    """)
