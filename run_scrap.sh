#!/bin/sh
set -eu

ts=$(date +%Y%m%d%H%M%S)
folder=${1:-out}

# Pre-flight checks: verify required files exist before starting
if [ ! -f "sqlite-init.sql" ]; then
  echo "Error: sqlite-init.sql not found"
  exit 1
fi

if [ ! -x "app/main.py" ]; then
  echo "Error: app/main.py not found or not executable"
  exit 1
fi

# Validate timestamp is numeric only (prevent SQL injection via table names)
case "$ts" in
  *[!0-9]*) echo "Error: timestamp must be numeric, got: $ts"; exit 1 ;;
esac

# Ensure folder does NOT end with a slash and create it 
folder="${folder%/}"
mkdir -p "$folder"

db_file="jobhubmine.db"

echo "Starting job scraping..."

# Phase 1: Ensure database schema exists (Initial run safety for API)
if [ ! -f "$folder/$db_file" ]; then
  echo "Initializing database schema..."
  # Use /tmp for temporary files to avoid permission issues in mounted volumes
  temp_init_sql="/tmp/init-schema.sql"
  # Use '0' as a dummy timestamp for initialization
  sed "s#\${ts}#0#g" sqlite-init.sql > "$temp_init_sql"
  sqlite3 "$folder/$db_file" < "$temp_init_sql"
  rm -f "$temp_init_sql"
fi

# Phase 1b: One-shot migration from pre-split schema (jobs_all/companies_all as TABLES)
# No-op on fresh or already-migrated DBs.
jobs_all_type=$(sqlite3 "$folder/$db_file" "SELECT type FROM sqlite_master WHERE name='jobs_all'" 2>/dev/null || echo "")
if [ "$jobs_all_type" = "table" ]; then
  echo "Migrating pre-split schema to per-source tables..."
  if ! sqlite3 "$folder/$db_file" < migrate-to-per-source.sql; then
    echo "Error: migration from pre-split schema failed"
    exit 1
  fi
fi

# Run the Python script (creates SQLite with data)
python3 app/main.py "$ts" "$folder" "$db_file"

# Check if the database was created successfully
if [ ! -f "${folder}/${db_file}" ]; then
  echo "Error: Database file was not created successfully"
  exit 1
fi

echo "Applying database schema and creating views..."
# Apply the SQL initialization script (Liquibase-like approach) 
temp_sqlfile="/tmp/${ts}-sqlite-init.sql"
sed "s#\${ts}#${ts}#g" sqlite-init.sql > "$temp_sqlfile"


if ! (sqlite3 "$folder/$db_file" < "$temp_sqlfile"); then 
  echo "Error: Failed to execute SQL commands on $db_file"
  rm -f "$temp_sqlfile"
  exit 1
fi

rm -f "$temp_sqlfile"

# Cleanup: keep only the last 10 timestamped SQL files if they exist (prevents bloat)
# This only works if we don't delete them immediately above, but let's keep it for safety
# or if user wants to keep some logs. Actually, let's just clean up old ones.
(ls -t "$folder"/*-sqlite-init.sql 2>/dev/null | tail -n +11 | xargs rm -f) || true

echo "Job scraping completed successfully!"
echo "${temp_sqlfile}"
