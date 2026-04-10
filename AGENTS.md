# AGENTS.md - Development Guidelines

This file contains guidelines for agentic coding agents working in this repository.

## Project Overview

This repository contains a job scraping system with three main components:

- `app/main.py` - Python scraper for Gupy API
- `api/` - Flask REST API serving job data
- `web/` - React web UI for searching/filtering jobs
- `run_scrap.sh` - Shell script to run the full scraping pipeline

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Scraper    │────▶│   SQLite     │◀────│    API      │
│  (Python)   │     │   Database  │     │  (Flask)    │
└──────────────┘     └──────────────┘     └──────────────┘
                                                  │
                                                  ▼
                                         ┌──────────────┐
                                         │    Web      │
                                         │  (React)    │
                                         └──────────────┘
```

## Build/Lint/Test Commands

### Running Locally

```bash
# Run full pipeline (scraper + SQLite)
./run_scrap.sh out/

# Run only scraper
python3 app/main.py "<timestamp>" "<folder>"

# Create SQLite from CSV
./create_sqlite_from_csv.sh "<timestamp>" "<folder>"
```

### Docker Compose (Recommended)

```bash
# Build all services
docker-compose build

# Start API and Web (no scraper)
docker-compose up -d

# Run scraper manually (only when needed)
docker-compose run --rm scraper
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GUPY_COMPANY_LIMIT` | `3` | Number of companies to fetch |
| `GUPY_THREADS` | `16` | Parallel worker threads |
| `GUPY_OUTPUT_FOLDER` | CLI arg | Output directory |

### Linting

```bash
# Python syntax check
python3 -m py_compile app/main.py api/app.py

# With flake8
pip install flake8
flake8 app/main.py api/app.py
```

### Testing

Manual testing by running the scraper and verifying:

```bash
# Verify CSV output
ls -la out/

# Verify SQLite data
sqlite3 out/*.db ".tables"
sqlite3 out/*.db "SELECT COUNT(*) FROM jobs;"

# Test API
curl http://localhost:5000/api/filters

# Test Web UI
curl http://localhost:8080/api/filters
```

## Code Style Guidelines

### Python (app/main.py, api/app.py)

- Use f-strings for string interpolation
- 4 spaces for indentation
- snake_case for functions/variables
- UPPER_SNAKE_CASE for constants
- Type hints for function signatures

```python
import os
import sys
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

def fetch_and_process_job_data(company: dict) -> tuple:
    company_id: str = company.get('companyId', '')
    return company_data, job_data_list
```

### React (web/src/)

- Functional components with hooks
- PascalCase for component names
- CSS modules or styled-components

```jsx
function JobSearch({ value, onChange }) {
  return <input value={value} onChange={onChange} />;
}
```

### Shell Scripts

- Use `#!/bin/sh` for portability
- Check file existence and executability
- Proper variable quoting

```bash
if [ ! -x "app/main.py" ]; then
  echo "Error: app/main.py not found"
  exit 1
fi
folder="${folder%/}/"
```

### Imports Order

1. Standard library
2. Third-party packages
3. Local modules

## Git Conventions

- Branch naming: `feature/*`, `dev`, `main`
- CI runs on push to `main`, `dev`, `feature/*`
- No pre-commit hooks

## File Organization

```
/home/abner.smartdb/src/gupy/
├── app/              # Scraper
│   ├── main.py
│   └── requirements.txt
├── api/              # Flask API
│   ├── app.py
│   ├── Dockerfile
│   └── requirements.txt
├── web/              # React UI
│   ├── src/
│   ├── public/
│   ├── package.json
│   ├── Dockerfile
│   └── nginx.conf
├── docker-compose.yml
├── run_scrap.sh
└── out/             # Output (created at runtime)
```

## Common Tasks

### Adding a New Field

1. `app/main.py`: Add field extraction
2. `sqlite-init.sql`: Add column
3. `api/app.py`: Update endpoint if needed
4. `web/src/App.js`: Add to UI if needed

### Changing API Configuration

```bash
# Via environment
GUPY_COMPANY_LIMIT=10 docker-compose run --rm scraper

# Via .env file
cp .env_sample .env
# Edit .env then:
docker-compose --env-file .env up -d
```

### Rebuilding After Code Changes

```bash
# Rebuild specific service
docker-compose build web
docker-compose up -d --force-recreate web
```

## CI/CD

GitHub Actions (`.github/workflows/ci.yml`):
1. Builds scraper, API, and web images
2. Pushes to GHCR
3. Runs scraper in CI
4. Uploads SQLite as artifact