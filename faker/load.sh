#!/usr/bin/env bash
# Load CloudBridge Inc. raw CSVs into PostgreSQL.
# Run from the faker/ directory.
#
# Usage:
#   export DATABASE_URL=postgres://user:password@localhost:5432/your_db
#   bash load.sh

set -euo pipefail

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "Error: DATABASE_URL is not set."
  echo "Example: export DATABASE_URL=postgres://postgres:password@localhost:5432/dbt_db"
  exit 1
fi

echo "==> Creating raw schema and tables..."
psql "$DATABASE_URL" -f schema.sql

echo "==> Loading CSVs..."

TABLES=(
  raw_chart_of_accounts
  raw_customers
  raw_products
  raw_employees
  raw_vendors
  raw_subscriptions
  raw_invoices
  raw_invoice_lines
  raw_payments
  raw_vendor_bills
  raw_payroll
  raw_journal_entries
)

for table in "${TABLES[@]}"; do
  echo "    $table..."
  psql "$DATABASE_URL" -c "\COPY raw.${table} FROM 'data/${table}.csv' CSV HEADER NULL '';"
done

echo ""
echo "==> Done. Row counts:"
for table in "${TABLES[@]}"; do
  count=$(psql "$DATABASE_URL" -t -c "SELECT COUNT(*) FROM raw.${table};" | tr -d ' ')
  printf "    %-35s %s rows\n" "$table" "$count"
done
