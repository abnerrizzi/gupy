# AGENTS.md - Development Guidelines for Agentic Coding

This file contains critical guidelines for AI agents working in this repository.

## Project Overview

A job scraping and visualization system for the Gupy platform.
- `app/main.py`: Scraper using requests, BeautifulSoup, and ThreadPoolExecutor.
- `api/app.py`: Flask REST API serving job data from SQLite.
- `web/`: React frontend for job search and filtering.
- `run_scrap.sh`: Orchestrates scraping, CSV generation, and SQLite initialization.

## Build, Lint, and Test Commands

### Development Pipeline
- **Full Scrape**: `./run_scrap.sh out` (creates `out/gupy.db`)
- **Scraper Only**: `python3 app/main.py <timestamp> <folder> <db_name>`
- **Database Init**: `./create_sqlite_from_csv.sh <timestamp> <folder>`

### Docker Commands
- **Build All**: `docker-compose build`
- **Start Services**: `docker-compose up -d` (starts API at :5000 and Web at :8080)
- **Run Scraper in Container**: `docker-compose run --rm scraper`

### Linting and Verification
- **Python Lint**: `flake8 app/main.py api/app.py`
- **Static Check**: `python3 -m py_compile app/main.py api/app.py`
- **React Lint**: `cd web && npm run lint` (if configured)

### Testing Strategy
Since there are no unit tests, verify changes manually:
1. **Scraper**: Check `out/gupy.db` for new records.
   `sqlite3 out/gupy.db "SELECT COUNT(*) FROM jobs;"`
2. **API**: `curl http://localhost:5000/api/jobs?limit=1`
3. **Frontend**: Check browser console for fetch errors.

## Code Style Guidelines

### Python (Scraper & API)
- **Formatting**: 4 spaces, snake_case for functions/vars, UPPER_SNAKE_CASE for constants.
- **Imports**: 
  1. Standard library (`os`, `sys`, `json`)
  2. Third-party (`requests`, `flask`)
  3. Local modules
- **Environment Variables**: Use `os.environ.get()` with sensible defaults.
  - `GUPY_COMPANY_LIMIT`: Total companies to fetch.
  - `GUPY_THREADS`: Concurrency level.
- **Error Handling**: Use `try...except` blocks in threads to prevent pipeline crashes. Log errors with `print()` or proper logging.
- **SQLite**: Use thread locks (`threading.Lock`) when writing to SQLite from multiple threads.

### React (Web)
- **Architecture**: Functional components with hooks (`useState`, `useEffect`).
- **State Management**: Local state; use `URLSearchParams` for API queries.
- **Styling**: Component-based CSS or standard CSS.
- **Naming**: PascalCase for components, camelCase for functions/variables.

### Shell Scripts
- **Portability**: Use `#!/bin/sh`.
- **Paths**: Normalize paths (remove trailing slashes) using `${var%/}`.
- **Safety**: Check for executable bits and file existence before running.

## Git Conventions
- **Commits**: Concise, descriptive messages (e.g., `feat: ...`, `fix: ...`).
- **Branching**: `feature/*` for new work.

## Common Agent Tasks
- **Adding Fields**: 
  1. Update `app/main.py` extraction logic.
  2. Update `sqlite-init.sql` schema.
  3. Update `api/app.py` mapping/query if necessary.
  4. Update `web/src/App.js` and components to display the field.
- **Fixing Paths**: Ensure `folder` variable in scripts does not have a trailing slash to avoid double-slashes in logs/file paths.
