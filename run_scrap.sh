#!/bin/sh

ts=$(date +%Y%m%d-%H%M%S)
folder=${1:-out/}

# Ensure folder ends with a slash and create it
folder="${folder%/}/"
mkdir -p "$folder"

# Check if `app/main.py` exists and is executable
if [ ! -x "app/main.py" ]; then
  echo "Error: app/main.py not found or not executable"
  exit 1
fi

echo "Starting job scraping..."
# Run the Python script (creates SQLite with data)
python3 app/main.py "$ts" "$folder"

# Check if the database was created successfully
db_file="${folder}${ts}-gupy_direct.db"
if [ ! -f "$db_file" ]; then
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
temp_sqlfile="${ts}-sqlite-init.sql"
sed "s#\${ts}#${ts}#g" sqlite-init.sql > "$temp_sqlfile"

if ! sqlite3 "$db_file" < "$temp_sqlfile"; then
  echo "Error: Failed to execute SQL commands on $db_file"
  rm -f "$temp_sqlfile"
  exit 1
fi

rm -f "$temp_sqlfile"
echo "Job scraping completed successfully!"
echo $db_file
