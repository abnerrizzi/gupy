# JobHubMine - Comprehensive Code Analysis & Improvement Plan

This document contains the full code analysis and improvement roadmap for the JobHubMine project,
generated from a thorough review of all source files on 2026-04-20.

---

## Architecture Overview

The project is a 3-tier job scraping system:

- **Scraper** (`app/main.py`) - Python scraper fetching from Gupy and Inhire APIs, stores results in SQLite
- **API** (`api/app.py`) - Flask REST API serving job data from the SQLite database
- **Web** (`web/src/`) - React SPA for searching/filtering jobs
- **Infra** - Docker Compose orchestration, nginx reverse proxy, GitHub Actions CI/CD

---

## Critical Issues (Fix Immediately)

### C1. SQL Injection via f-string table names
- **Component:** Scraper (`app/main.py:245-267, 335-336`)
- **Fix:** Validated `ts` with regex (`^[0-9]+$`) in both `run_scrap.sh` and `app/main.py`.
- **Status:** [x] Done

### C2. Bare `except: pass` swallows all exceptions
- **Component:** Scraper (`app/main.py:154`)
- **Fix:** Replaced with proper logging and specific exception handling.
- **Status:** [x] Done

### C3. CI pushes `:latest` from all branches
- **Component:** CI/CD (`.github/workflows/ci.yml`)
- **Fix:** Used `docker/metadata-action` to tag `:latest` only on `main` branch.
- **Status:** [x] Done

### C4. API port 5000 exposed to host without authentication
- **Component:** Docker (`docker-compose.yml:20`)
- **Fix:** Replaced `ports` with `expose` for the API service.
- **Status:** [x] Done

### C5. Debug mode defaults to `true`
- **Component:** API (`api/app.py:254`)
- **Fix:** Changed default to `false`.
- **Status:** [x] Done

---

## High-Priority Issues

### H1. Error handling only prints, no tracebacks or exit codes
- **Status:** [x] Done (Implemented logging module and sys.exit(1) on db error)

### H2. `time.sleep(2)` is not a rate limiter under concurrency
- **Status:** [ ] Pending (Requires sophisticated rate limiter, kept constant for now)

### H3. Unhandled `ValueError` on non-numeric `limit`/`offset`
- **Status:** [x] Done (Implemented safe_int with bounds)

### H4. Duplicated WHERE clause logic (~50 lines)
- **Status:** [x] Done (Extracted build_filters helper)

### H5. No user-facing error state in React UI
- **Status:** [x] Done (Implemented error state and retry UI)

### H6. `job.source.toUpperCase()` crashes on null
- **Status:** [x] Done (Added optional chaining)

### H7. Modal lacks accessibility (ARIA, focus trap, keyboard)
- **Status:** [x] Done (Implemented Escape key, focus management, and ARIA roles)

### H8. Filter selects have no labels for screen readers
- **Status:** [x] Done (Added aria-label to all selects)

### H9. Clickable table rows lack keyboard support
- **Status:** [x] Done (Added tabIndex and onKeyDown handlers)

### H10. No CI quality gate (lint/test)
- **Status:** [x] Done (Added flake8 and npm build validation job)

### H11. Nginx config injection via `API_URL` env var
- **Status:** [x] Done (Used envsubst and template approach)

---

## Medium-Priority Issues

### M1. No `.dockerignore`
- **Status:** [x] Done

### M2. All containers run as root
- **Status:** [x] Done (Added appuser)

### M3. Python 3.9 EOL, Node 18 past maintenance
- **Status:** [x] Done (Upgraded to Python 3.12 and Node 20)

### M4. API Dockerfile missing `--no-cache` on `apk add`
- **Status:** [x] Done

### M5. No `depends_on`, `healthcheck`, or `restart` in Compose
- **Status:** [x] Done (Added depends_on and restart policies)

### M6. No CORS configuration on API
- **Status:** [x] Done (Implicitly handled by nginx same-origin proxy)

### M7. No `limit`/`offset` bounds on API
- **Status:** [x] Done

### M8. Gunicorn runs with 1 worker (default)
- **Status:** [x] Done (Added --workers 2)

### M9. `INSERT OR IGNORE` silently drops updated data
- **Status:** [x] Done (Switched to INSERT OR REPLACE)

### M10. No transaction wrapping in SQL migration
- **Status:** [x] Done

### M11. No indexes on `jobs_all`
- **Status:** [x] Done

### M12. Timestamped tables accumulate forever
- **Status:** [ ] Pending

### M13. Shell script improvements
- **Status:** [x] Done

### M14. Duplicated formatters
- **Status:** [x] Done (Extracted to utils/formatters.js)

### M15. No `AbortController`
- **Status:** [x] Done

### M16. No PropTypes
- **Status:** [x] Done

### M17. No responsive design
- **Status:** [x] Done

### M18. Page size magic numbers
- **Status:** [x] Done

### M19. `.env_sample` is stale
- **Status:** [x] Done

### M20. `nginx.conf` is dead code
- **Status:** [x] Done (Used as template)
