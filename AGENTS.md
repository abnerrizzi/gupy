# AGENTS.md - Development Guidelines

This file contains critical instructions and guidelines for agentic coding agents (AI) working in this repository.

## Project Overview

JobHubMine is a multi-source job scraping and visualization system.
- **Scraper (`app/`):** Python-based crawler for Gupy, Inhire, etc.
- **API (`api/`):** Flask REST API serving SQLite data.
- **Web (`web/`):** React functional UI for browsing jobs.
- **Data (`out/`):** SQLite database (`jobhubmine.db`) populated via `run_scrap.sh`.

## Core Mandates

1.  **DOCKER ONLY:** Agents MUST NOT run the application locally. Always use Docker Compose.
2.  **CONVENTIONAL COMMITS:** Use `type(scope): description`. Types: `feat`, `fix`, `refactor`, `chore`, `docs`.
3.  **SOURCE AGNOSTIC:** Use generic "data source" terminology. Config via `<SOURCE>_` prefix env vars.
4.  **ABSOLUTE PATHS:** Always use absolute paths (e.g., `/home/abner.smartdb/src/jobhubmine/app/main.py`).

## Build/Lint/Test Commands

### Docker Execution
```bash
# Full build and start (API at 5000, Web at 8080)
docker-compose build && docker-compose up -d

# Run Scraper (manually trigger)
docker-compose run --rm scraper

# View Logs
docker-compose logs -f [api|web|scraper]
```

### Linting & Quality
```bash
# Python (Lint/Type Check)
python3 -m py_compile /home/abner.smartdb/src/jobhubmine/app/main.py
flake8 /home/abner.smartdb/src/jobhubmine/app/main.py

# React
cd /home/abner.smartdb/src/jobhubmine/web && npm run lint
```

### Testing
There is no automated test suite. Perform manual validation:
```bash
# API Health Check
curl http://localhost:5000/api/health

# Verify Data in DB
sqlite3 /home/abner.smartdb/src/jobhubmine/out/jobhubmine.db "SELECT source, COUNT(*) FROM jobs_all GROUP BY source;"

# If pytest/jest are added:
# pytest /home/abner.smartdb/src/jobhubmine/tests/test_file.py
# npm test -- /home/abner.smartdb/src/jobhubmine/web/src/Component.test.js
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
