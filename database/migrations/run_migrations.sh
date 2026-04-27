#!/usr/bin/env bash
# Apply all DevIndex migrations to a Supabase Postgres in numeric order.
#
# Usage:
#   DATABASE_URL='postgresql://postgres.<ref>:<PASSWORD>@<host>:<port>/postgres' \
#     ./run_migrations.sh
#
# The DATABASE_URL is shown in Supabase dashboard at:
#   Project Settings → Database → Connection string (use "Transaction pooler"
#   on port 6543 for one-shot scripts, or "Session pooler"/Direct on 5432).
#
# Idempotency: every CREATE uses IF NOT EXISTS / OR REPLACE, every CREATE POLICY
# is preceded by DROP POLICY IF EXISTS — re-running is safe.

set -euo pipefail

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "ERROR: DATABASE_URL is not set." >&2
  exit 1
fi

cd "$(dirname "$0")"

for f in $(ls 0[0-9][0-9]_*.sql | sort); do
  echo "==> Applying $f"
  psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$f"
done

echo "==> All migrations applied."
