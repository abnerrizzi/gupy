#!/bin/sh

ts=$(date +%Y%m%d%H%M%S)
folder=${1:-out}

# Ensure folder does NOT end with a slash and create it 
folder="${folder%/}"
mkdir -p "$folder"
db_file="gupy.db"

# Check if `app/main.py` exists and is executable
if [ ! -x "app/main.py" ]; then
  echo "Error: app/main.py not found or not executable"
  exit 1
fi

echo "Starting job scraping..."

# Phase 1: Ensure database schema exists (Initial run safety for API)
echo "Initializing database schema..."
temp_init_sql="$folder/init-schema.sql"
# Use '0' as a dummy timestamp for initialization
sed "s#\${ts}#0#g" sqlite-init.sql > "$temp_init_sql"
sqlite3 "$folder/$db_file" < "$temp_init_sql"
rm -f "$temp_init_sql"

# Run the Python script (creates SQLite with data)
python3 app/main.py "$ts" "$folder" "$db_file"

# Check if the database was created successfully
if [ ! -f "${folder}/${db_file}" ]; then
  echo "Error: Database file was not created successfully"
  exit 1
fi

# Check if sqlite-init.sql exists
if [ ! -f "sqlite-init.sql" ]; then
  echo "Error: sqlite-init.sql not found"
  exit 1
fi

echo "Applying database schema and creating views..."
# Apply the SQL initialization script (Liquibase-like approach) 
temp_sqlfile="$folder/${ts}-sqlite-init.sql"
sed "s#\${ts}#${ts}#g" sqlite-init.sql > "$temp_sqlfile"


if ! (sqlite3 "$folder/$db_file" < "$temp_sqlfile"); then 
  echo "Error: Failed to execute SQL commands on $db_file"
  # rm -f "$temp_sqlfile"
  exit 1
fi

# rm -f "$temp_sqlfile"
echo "Job scraping completed successfully!"
echo ${temp_sqlfile}