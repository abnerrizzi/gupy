#!/bin/bash

declare filename=gupy_from_csv.db
declare sqlfile=sqlite.sql
sqlite3 $filename < $sqlfile