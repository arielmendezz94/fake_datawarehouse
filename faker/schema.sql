-- CloudBridge Inc. — Raw schema for PostgreSQL
-- Run once before loading CSVs with load.sh
-- All IDs are stored as VARCHAR(36) to accept pre-generated UUIDs from generate.py

CREATE SCHEMA IF NOT EXISTS raw;

-- ── Dimensions ────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS raw.raw_chart_of_accounts (
    account_id      VARCHAR(36)  PRIMARY KEY,
    account_code    VARCHAR(10)  NOT NULL,
    account_name    VARCHAR(150) NOT NULL,
    account_type    VARCHAR(20)  NOT NULL,   -- Asset | Liability | Equity | Revenue | COGS | OpEx
    account_subtype VARCHAR(50)  NOT NULL,
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS raw.raw_customers (
    customer_id   VARCHAR(36)  PRIMARY KEY,
    company_name  VARCHAR(200) NOT NULL,
    industry      VARCHAR(50),
    segment       VARCHAR(20),              -- SMB | Mid-Market | Enterprise
    region        VARCHAR(50),
    billing_email VARCHAR(200),
    credit_limit  NUMERIC(15, 2),
    created_at    DATE,
    is_active     BOOLEAN
);

CREATE TABLE IF NOT EXISTS raw.raw_products (
    product_id       VARCHAR(36)  PRIMARY KEY,
    product_name     VARCHAR(100) NOT NULL,
    product_category VARCHAR(50),           -- Subscription | Professional Services
    unit_price       NUMERIC(15, 2),
    description      TEXT,
    is_active        BOOLEAN,
    created_at       DATE
);

CREATE TABLE IF NOT EXISTS raw.raw_employees (
    employee_id VARCHAR(36)  PRIMARY KEY,
    first_name  VARCHAR(100),
    last_name   VARCHAR(100),
    department  VARCHAR(50),
    role        VARCHAR(100),
    salary      NUMERIC(15, 2),
    hire_date   DATE,
    is_active   BOOLEAN,
    created_at  DATE,
    manager_id  VARCHAR(36)                 -- self-referencing FK (not enforced at load time)
);

CREATE TABLE IF NOT EXISTS raw.raw_vendors (
    vendor_id            VARCHAR(36)  PRIMARY KEY,
    vendor_name          VARCHAR(200) NOT NULL,
    vendor_category      VARCHAR(100),
    payment_terms_days   INTEGER,
    expense_account_code VARCHAR(10),
    is_active            BOOLEAN,
    created_at           DATE
);

-- ── Facts ─────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS raw.raw_subscriptions (
    subscription_id VARCHAR(36) PRIMARY KEY,
    customer_id     VARCHAR(36),            -- FK → raw_customers
    product_id      VARCHAR(36),            -- FK → raw_products (subscription plans only)
    plan_name       VARCHAR(100),
    status          VARCHAR(20),            -- Active | Churned
    mrr             NUMERIC(15, 2),
    start_date      DATE,
    end_date        DATE,                   -- NULL for active subscriptions
    created_at      DATE,
    updated_at      DATE
);

CREATE TABLE IF NOT EXISTS raw.raw_invoices (
    invoice_id      VARCHAR(36) PRIMARY KEY,
    customer_id     VARCHAR(36),            -- FK → raw_customers
    subscription_id VARCHAR(36),            -- FK → raw_subscriptions (NULL for PS invoices)
    sales_rep_id    VARCHAR(36),            -- FK → raw_employees
    invoice_type    VARCHAR(50),            -- Subscription | Professional Services
    invoice_date    DATE,
    due_date        DATE,
    status          VARCHAR(20),            -- Paid | Open | Overdue
    total_amount    NUMERIC(15, 2),
    currency        CHAR(3),
    created_at      DATE
);

CREATE TABLE IF NOT EXISTS raw.raw_invoice_lines (
    line_id      VARCHAR(36) PRIMARY KEY,
    invoice_id   VARCHAR(36),               -- FK → raw_invoices
    product_id   VARCHAR(36),               -- FK → raw_products
    description  TEXT,
    quantity     INTEGER,
    unit_price   NUMERIC(15, 2),
    discount_pct NUMERIC(6, 4),
    line_total   NUMERIC(15, 2)
);

CREATE TABLE IF NOT EXISTS raw.raw_payments (
    payment_id     VARCHAR(36) PRIMARY KEY,
    invoice_id     VARCHAR(36),             -- FK → raw_invoices
    customer_id    VARCHAR(36),             -- FK → raw_customers
    payment_date   DATE,
    amount         NUMERIC(15, 2),
    payment_method VARCHAR(50),             -- ACH | Wire | Credit Card | Check
    currency       CHAR(3),
    created_at     DATE
);

CREATE TABLE IF NOT EXISTS raw.raw_vendor_bills (
    bill_id            VARCHAR(36) PRIMARY KEY,
    vendor_id          VARCHAR(36),          -- FK → raw_vendors
    expense_account_id VARCHAR(36),          -- FK → raw_chart_of_accounts
    bill_date          DATE,
    due_date           DATE,
    amount             NUMERIC(15, 2),
    status             VARCHAR(20),          -- Paid | Open
    description        TEXT,
    currency           CHAR(3),
    created_at         DATE
);

CREATE TABLE IF NOT EXISTS raw.raw_payroll (
    payroll_id       VARCHAR(36) PRIMARY KEY,
    employee_id      VARCHAR(36),            -- FK → raw_employees
    department       VARCHAR(50),
    pay_period_start DATE,
    pay_period_end   DATE,
    gross_pay        NUMERIC(15, 2),
    tax_withheld     NUMERIC(15, 2),
    net_pay          NUMERIC(15, 2),
    payment_date     DATE,
    pay_type         VARCHAR(20),            -- Salary | Bonus
    created_at       DATE
);

CREATE TABLE IF NOT EXISTS raw.raw_journal_entries (
    entry_id         VARCHAR(36)  PRIMARY KEY,
    transaction_ref  VARCHAR(100),           -- links to invoice_id, payment_id, bill_id, etc.
    transaction_type VARCHAR(50),            -- INVOICE | PAYMENT | VENDOR_BILL | BILL_PAYMENT | PAYROLL
    account_id       VARCHAR(36),            -- FK → raw_chart_of_accounts
    account_code     VARCHAR(10),            -- denormalized for convenience
    entry_date       DATE,
    debit_amount     NUMERIC(15, 2),
    credit_amount    NUMERIC(15, 2),
    description      TEXT,
    created_at       DATE
);
