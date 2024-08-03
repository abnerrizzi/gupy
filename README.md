# Data Scraping and SQLite Management

This repository contains scripts and tools for scraping job data from an API, creating an SQLite database from CSV files, and managing data.

## Overview

- `run_scrap.sh`: A shell script to run the data scraping process and create an SQLite database.
- `create_sqlite_from_csv.sh`: A shell script to initialize an SQLite database using CSV files.
- `sqlite-init.sql`: An SQL template used by `create_sqlite_from_csv.sh` to set up the SQLite database and import data.
- `app/main.py`: A Python script that scrapes job data from an API and writes it to CSV files.
- `app/requirements.txt`: Python package dependencies required for `app/main.py`.

## Scripts

### `run_scrap.sh`

This script runs the Python scraper and creates the SQLite database.

#### Usage

```bash
./run_scrap.sh [folder]
