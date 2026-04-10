# AGENTS.md - Development Guidelines

This file contains guidelines for agentic coding agents working in this repository.

## Project Overview

This repository contains scripts for scraping job data from the Gupy API, creating CSV files, and populating an SQLite database. The main components are:

- `app/main.py` - Python scraper that fetches job data from the Gupy API
- `run_scrap.sh` - Shell script to run the full scraping pipeline
- `create_sqlite_from_csv.sh` - Creates SQLite database from CSV files
- `sqlite-init.sql` - SQL template for database initialization

## Build/Lint/Test Commands

### Running the scraper

```bash
# Run the full pipeline (uses defaults)
./run_scrap.sh [output_folder]

# With environment variables
GUPY_COMPANY_LIMIT=10 GUPY_THREADS=8 ./run_scrap.sh out/

# Or run components separately:
python3 app/main.py "<timestamp>" "<folder>"
./create_sqlite_from_csv.sh "<timestamp>" "<folder>"
```

### Docker

```bash
# Build Docker image
docker build -t gupy-scraper .

# Run with defaults
docker run -v ./out/:/app/out/ gupy-scraper

# Run with custom environment variables
docker run -e GUPY_COMPANY_LIMIT=10 -e GUPY_THREADS=8 \
  -v ./out/:/app/out/ gupy-scraper

# Run with .env file
docker run --env-file .env -v ./out/:/app/out/ gupy-scraper
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GUPY_COMPANY_LIMIT` | `3` | Number of companies to fetch from API |
| `GUPY_THREADS` | `16` | Parallel worker threads |
| `GUPY_OUTPUT_FOLDER` | CLI arg | Output directory (overrides CLI second arg) |

### Linting

This project uses basic Python. Run with:

```bash
# Basic syntax check
python3 -m py_compile app/main.py

# Install dependencies for more thorough checks
pip install flake8
flake8 app/main.py
```

### Testing

No formal test suite exists. Manual testing can be done by running the scraper and verifying:
- CSV files are created in the output folder
- SQLite database is populated with correct data

```bash
# Verify CSV output
ls -la out/

# Verify SQLite data
sqlite3 out/*.db ".tables"
sqlite3 out/*.db "SELECT COUNT(*) FROM jobs;"
```

## Code Style Guidelines

### General Structure

- Python 3.9+ (see Dockerfile)
- Simple scripts, no heavy framework dependencies
- Dependencies: `requests`, `beautifulsoup4`, `tqdm`

### Imports

```python
# Standard library first, then third-party, then local
import requests
import csv
import json
import os
import sys
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import tqdm
```

### Formatting

- Use f-strings for string interpolation
- Use 4 spaces for indentation (no tabs)
- Limit lines to reasonable length (~80-120 characters)

```python
# Good
companies_csv_path = f'{folder}/{ts}-companies.csv'
job_url = f'https://portal.api.gupy.io/api/company?limit={company_limit}'

# Avoid
companies_csv_path = folder + "/" + ts + "-companies.csv"
```

### Naming Conventions

- Functions and variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Files: `snake_case.py`

```python
# Good
def fetch_and_process_job_data(company):
    company_id = company['companyId']
    company_limit = 3

# Avoid
def fetchAndProcessJobData(company):
    companyId = company['companyId']
```

### Type Hints

Add type hints where helpful, especially for function signatures:

```python
def fetch_and_process_job_data(company: dict) -> tuple:
    """Fetch job data for a company."""
    company_id: str = company['companyId']
    return company_data, job_data_list
```

### Error Handling

Use try/except blocks with meaningful error messages:

```python
try:
    company_data, job_data_list = future.result()
    companies_writer.writerow(company_data)
except Exception as exc:
    print(f"Generated an exception: {exc}")
```

Always handle key errors gracefully and provide defaults:

```python
job_id = job.get('id', '')
job_title = job.get('title', 'N/A')
```

### Database/SQL

- Use parameterized queries via sqlite3 CLI
- Template variables in SQL: `${ts}` (replaced via `sed`)
- Always write headers before data in CSV

```sql
-- In sqlite-init.sql
INSERT INTO companies SELECT * FROM companies_csv;
```

### Shell Scripts

- Use `#!/bin/sh` for portability
- Check file existence and executability
- Use proper quoting for variables

```bash
# Good
if [ ! -x "app/main.py" ]; then
  echo "Error: app/main.py not found or not executable"
  exit 1
fi

# Good variable handling
folder="${folder%/}/"
```

### Git Conventions

- Branch naming: `feature/*`, `dev`, `main`
- CI runs on push to `main`, `dev`, and `feature/*`
- No pre-commit hooks configured

## File Organization

```
/home/abner.smartdb/src/gupy/
├── AGENTS.md              # This file
├── README.md             # Project documentation
├── Dockerfile            # Docker image definition
├── app/
│   ├── main.py           # Main Python scraper
│   └── requirements.txt  # Python dependencies
├── run_scrap.sh          # Main entry point script
├── create_sqlite_from_csv.sh
├── sqlite-init.sql
└── out/                 # Output directory (created at runtime)
```

## CI/CD

GitHub Actions workflow (`.github/workflows/ci.yml`):
1. Builds Docker image
2. Runs scraper in container
3. Stores SQLite database as artifact

## Common Tasks

### Adding a new field to scrape

1. Modify `app/main.py`:
   - Add field extraction in `fetch_and_process_job_data()`
   - Add column to jobs CSV header
2. Modify `sqlite-init.sql`:
   - Add column to jobs table
3. Update CSV header in `main.py`

### Changing API limits

Edit `company_limit` or `threads` in `app/main.py`:

```python
company_limit = 3  # Number of companies to fetch
threads = 16       # Parallel workers
```