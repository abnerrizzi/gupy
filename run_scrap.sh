#!/bin/bash

ts=$(date +%Y%m%d-%H%M%S)
folder=${1:-out/}

ts="20240803-112933"

app/main.py $ts $folder

./create_sqlite_from_csv.sh "$ts" "$folder"
