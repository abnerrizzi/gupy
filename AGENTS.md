# AGENTS.md - Development Guidelines

This file contains critical instructions and guidelines for agentic coding agents (AI) working in this repository.

## Project Overview

This repository contains a job scraping system with three main components:
- `app/main.py` - Python scraper for various data sources
- `api/` - Flask REST API serving job data
- `web/` - React web UI for searching/filtering jobs
- `run_scrap.sh` - Shell script to run the full scraping pipeline (via Docker)

## Core Mandates

1.  **DOCKER ONLY:** Agents MUST NOT run the application locally. Always use Docker Compose.
2.  **CONVENTIONAL COMMITS:** Use `type(scope): description`. Types: `feat`, `fix`, `refactor`, `chore`, `docs`.
3.  **SOURCE AGNOSTIC:** Use generic "data source" terminology. Config via `<SOURCE>_` prefix env vars.
4.  **ABSOLUTE PATHS:** Always use absolute paths (e.g., `/home/abner.smartdb/src/jobhubmine/app/main.py`).

## Build/Lint/Test Commands

**CRITICAL: Do not run locally. Always use Docker to build and run the application.**

### Docker Compose (Recommended)
```bash
# Build all services
docker-compose build

# Start API and Web
docker-compose up -d

# Run scraper manually
docker-compose run --rm scraper
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `<SOURCE>_COMPANY_LIMIT` | Varies | Number of companies/jobs to fetch for a data source |
| `<SOURCE>_THREADS` | `16` | Parallel worker threads for a data source |
| `<SOURCE>_ENABLED` | `true` | Toggle a specific data source |
| `LINKEDIN_KEYWORDS` | `Software Engineer` | Job title or skill keywords for LinkedIn |
| `LINKEDIN_LOCATION` | `Brazil` | Geographic filter for LinkedIn |
| `GUPY_OUTPUT_FOLDER` | CLI arg | Output directory |

### Linting
```bash
# Python (run via docker or locally if environment is setup)
python3 -m py_compile app/main.py api/app.py
flake8 app/main.py api/app.py

# React
cd /home/abner.smartdb/src/jobhubmine/web && npm run lint
```

### Testing
There is no automated test suite. Perform manual validation:
```bash
# Run Python tests
pytest
pytest path/to/specific_test.py  # Run a single test

# Run React tests
cd web && npm test
cd web && npm test -- specific.test.js  # Run a single test

# Manual Testing Validations
ls -la out/
sqlite3 out/jobhubmine.db "SELECT COUNT(*) FROM jobs;"
curl http://localhost:5000/api/filters
curl http://localhost:8080/api/filters
```

## Code Style Guidelines

### Python (Scraper & API)
- **Formatting:** 4 spaces, UTF-8.
- **Imports:** Standard Library -> Third-party -> Local. Use absolute imports if possible.
- **Naming:** `snake_case` (vars/funcs), `PascalCase` (classes), `UPPER_SNAKE_CASE` (constants).
- **Types:** REQUIRED for all function signatures. Use `typing` module (Dict, List, Optional).
- **Error Handling:** Use `try...except` with specific exceptions. Log errors with `logger.error(..., exc_info=True)`.
- **Logic:** Use `Scraper` base class for new sources. Respect `RATE_LIMIT_SLEEP`.

### React (Web UI)
- **Components:** Functional components with Hooks ONLY. No class components.
- **Naming:** `PascalCase` for files/components. `camelCase` for props.
- **Props:** Use `prop-types` for validation.
- **API Calls:** Use `fetch` inside `useEffect`. Handle loading/error states.

### SQL / Database
- **Schema:** Managed via `/home/abner.smartdb/src/jobhubmine/sqlite-init.sql`.
- **Conventions:** Dynamic tables use `_{timestamp}` suffix. Permanent views are `jobs_all` and `companies_all`.

## File Organization
```
/home/abner.smartdb/src/jobhubmine/
├── app/              # Scraper logic (main.py, requirements.txt)
├── api/              # Flask API (app.py, requirements.txt)
├── web/              # React Frontend (src/, public/, package.json)
├── out/              # Data output (SQLite, CSVs) - GIT IGNORED
├── run_scrap.sh      # Pipeline entry point
└── docker-compose.yml
```

## Security & Environment
- **NO SECRETS:** Do not commit `.env` or hardcoded keys.
- **ENV VARS:** Use `os.environ.get('VAR', default)` in Python.
- **TIMEOUTS:** Always set `timeout` on network requests (e.g., `requests.get(..., timeout=30)`).
