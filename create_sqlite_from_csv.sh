#!/bin/sh

ts=$(date +%Y%m%d-%H%M%S)
filename=$ts-gupy_from_csv.db
sqlfile=$ts-sqlite-init.sql

sqlite3 $filename < $sqlfile
