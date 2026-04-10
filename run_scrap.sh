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

# Run the Python script
python3 app/main.py "$ts" "$folder"

# Check if `create_sqlite_from_csv.sh` exists and is executable
if [ ! -x "./create_sqlite_from_csv.sh" ]; then
  echo "Error: create_sqlite_from_csv.sh not found or not executable"
  exit 1
fi

# Run the shell script to create SQLite database
./create_sqlite_from_csv.sh "$ts" "$folder"
