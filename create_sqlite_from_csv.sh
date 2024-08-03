#!/bin/sh

if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <timestamp> <folder>"
  exit 1
fi

ts="$1"
folder="$2"
folder="${folder%/}/"
filename="${folder}${ts}-gupy_from_csv.db"
temp_sqlfile="${ts}-sqlite-init.sql"

sed "s#\${ts}#${folder}${ts}#g" sqlite-init.sql > "$temp_sqlfile"

if ! sqlite3 "$filename" < "$temp_sqlfile"; then
  echo "Error: Failed to execute SQL commands on $filename"
  rm "$temp_sqlfile"
  exit 1
fi

rm "$temp_sqlfile"
