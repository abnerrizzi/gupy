#!/bin/sh

if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <timestamp> <folder>"
  exit 1
fi

ts=$1
shift
folder=$1
shift


filename=$ts-gupy_from_csv.db
temp_sqlfile="${ts}-sqlite-init.sql"

sed "s#\${ts}#${folder}/${ts}#g" sqlite-init.sql > $temp_sqlfile


sqlite3 $filename < $temp_sqlfile

rm $temp_sqlfile