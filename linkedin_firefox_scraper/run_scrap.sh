#!/bin/sh
set -eu

ts=$(date +%Y%m%d%H%M%S)
folder=${1:-out}

if [ ! -f "sqlite-init.sql" ]; then
  echo "Error: sqlite-init.sql not found"
  exit 1
fi

if [ ! -f "main.py" ]; then
  echo "Error: main.py not found"
  exit 1
fi

if ! python3 -c "import selenium" 2>/dev/null; then
  echo "Error: selenium not installed"
  exit 1
fi

case "$ts" in
  *[!0-9]*) echo "Error: timestamp must be numeric, got: $ts"; exit 1 ;;
esac

folder="${folder%/}"
mkdir -p "$folder"

db_file="jobhubmine.db"

echo "DEBUG env var value: [$DEBUG]"
echo "Starting LinkedIn Firefox scraper..."

# Start VNC for visual debugging if DEBUG=1
if [ "$DEBUG" = "1" ]; then
  echo "Starting VNC for visual debugging..."
  Xvfb :99 -screen 0 1024x768x24 &
  XVFB_PID=$!
  export DISPLAY=:99
  sleep 1
  x11vnc -display :99 -forever -shared -bg
  echo "VNC available on port 5900"
fi

if [ ! -f "$folder/$db_file" ]; then
  echo "Initializing database schema..."
  temp_init_sql="/tmp/init-schema.sql"
  sed "s#\${ts}#0#g" sqlite-init.sql > "$temp_init_sql"
  sqlite3 "$folder/$db_file" < "$temp_init_sql"
  rm -f "$temp_init_sql"
fi

python3 main.py "$ts" "$folder" "$db_file"

if [ ! -f "${folder}/${db_file}" ]; then
  echo "Error: Database file was not created successfully"
  exit 1
fi

echo "Applying database schema and creating views..."
temp_sqlfile="/tmp/${ts}-sqlite-init.sql"
sed "s#\${ts}#${ts}#g" sqlite-init.sql > "$temp_sqlfile"

if ! (sqlite3 "$folder/$db_file" < "$temp_sqlfile"); then
  echo "Error: Failed to execute SQL commands on $db_file"
  rm -f "$temp_sqlfile"
  exit 1
fi

rm -f "$temp_sqlfile"

(ls -t "$folder"/*-sqlite-init.sql 2>/dev/null | tail -n +11 | xargs rm -f) || true

echo "LinkedIn Firefox scraper completed successfully!"