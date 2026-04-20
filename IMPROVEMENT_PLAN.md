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
- **Issue:** `ts` from `sys.argv[1]` is interpolated directly into SQL DDL/DML without validation. An attacker or misconfigured caller could inject arbitrary SQL via the timestamp argument.
- **Fix:** Validate `ts` with regex (`^[0-9]+$`) in both `run_scrap.sh` and `app/main.py`.
- **Status:** [ ] Pending

### C2. Bare `except: pass` swallows all exceptions
- **Component:** Scraper (`app/main.py:154`)
- **Issue:** Catches and silently discards ALL exceptions including `KeyboardInterrupt` and `SystemExit`. This is the worst anti-pattern in Python error handling.
- **Fix:** Replace with `except Exception as e: logging.warning(...)`.
- **Status:** [ ] Pending

### C3. CI pushes `:latest` from all branches
- **Component:** CI/CD (`.github/workflows/ci.yml`)
- **Issue:** All three build jobs push `:latest` tags on pushes to `main`, `dev`, `feature/*`, and `feat/*`. A feature branch push overwrites the production image tag.
- **Fix:** Use `${{ github.sha }}` or branch-name tags for non-main branches, only tag `:latest` on `main`.
- **Status:** [ ] Pending

### C4. API port 5000 exposed to host without authentication
- **Component:** Docker (`docker-compose.yml:20`)
- **Issue:** `ports: "5000:5000"` makes the unauthenticated API reachable from any network interface. Should be internal-only since nginx already proxies `/api/`.
- **Fix:** Replace `ports` with `expose` for the API service.
- **Status:** [ ] Pending

### C5. Debug mode defaults to `true`
- **Component:** API (`api/app.py:254`)
- **Issue:** `os.environ.get('DEBUG', 'true')` exposes the Werkzeug interactive debugger (allows remote code execution) when running outside gunicorn.
- **Fix:** Change default to `'false'`.
- **Status:** [ ] Pending

---

## High-Priority Issues

### H1. Error handling only prints, no tracebacks or exit codes
- **Component:** Scraper (`app/main.py` throughout)
- **Issue:** All `except Exception` blocks only `print()` -- no tracebacks, no structured logging, process always exits 0.
- **Fix:** Use Python `logging` module with `logging.exception()` for tracebacks. Set non-zero exit code on failure.
- **Status:** [ ] Pending

### H2. `time.sleep(2)` is not a rate limiter under concurrency
- **Component:** Scraper (`app/main.py:126`)
- **Issue:** With 16 threads, all sleep/wake simultaneously -- no actual rate limiting.
- **Fix:** Use `threading.Semaphore` or token-bucket pattern for proper rate limiting.
- **Status:** [ ] Pending

### H3. Unhandled `ValueError` on non-numeric `limit`/`offset`
- **Component:** API (`api/app.py:116-117`)
- **Issue:** `int(request.args.get('limit', 100))` raises `ValueError` on `?limit=abc` producing a raw 500 error.
- **Fix:** Add try/except with defaults, enforce bounds (max 1000, min 0).
- **Status:** [ ] Pending

### H4. Duplicated WHERE clause logic (~50 lines)
- **Component:** API (`api/app.py:64-146`)
- **Issue:** Filter logic is built twice independently for data query vs. count query. Will diverge silently.
- **Fix:** Extract shared `build_filters()` function.
- **Status:** [ ] Pending

### H5. No user-facing error state in React UI
- **Component:** Web (`web/src/App.js` all fetch calls)
- **Issue:** API failures are swallowed with `console.error`, users see a blank/loading page.
- **Fix:** Add `error` state variable and error UI rendering. Check `res.ok` before `res.json()`.
- **Status:** [ ] Pending

### H6. `job.source.toUpperCase()` crashes on null
- **Component:** Web (`web/src/components/JobTable.jsx:91`)
- **Issue:** Will throw `TypeError` if `source` is null. `JobDetails.jsx` correctly uses `?.` but `JobTable.jsx` does not.
- **Fix:** Use optional chaining: `job.source?.toUpperCase()`.
- **Status:** [ ] Pending

### H7. Modal lacks accessibility (ARIA, focus trap, keyboard)
- **Component:** Web (`web/src/components/JobDetails.jsx`)
- **Issue:** No `role="dialog"`, no `aria-modal`, no focus trapping, no `Escape` key handler, close button has no `aria-label`.
- **Fix:** Add proper ARIA attributes and keyboard event handlers.
- **Status:** [ ] Pending

### H8. Filter selects have no labels for screen readers
- **Component:** Web (`web/src/components/FilterBar.jsx`)
- **Issue:** All `<select>` elements lack `<label>` or `aria-label`.
- **Fix:** Add `aria-label` attributes to all selects.
- **Status:** [ ] Pending

### H9. Clickable table rows lack keyboard support
- **Component:** Web (`web/src/components/JobTable.jsx:69`)
- **Issue:** `<tr onClick>` but no `tabIndex`, `role="button"`, or `onKeyDown`.
- **Fix:** Add `tabIndex="0"`, `role="button"`, and `onKeyDown` for Enter/Space.
- **Status:** [ ] Pending

### H10. No CI quality gate (lint/test)
- **Component:** CI/CD (`.github/workflows/ci.yml`)
- **Issue:** Code is pushed to the container registry without any linting, type checking, or tests.
- **Fix:** Add `flake8` for Python, `npm run build` validation, and syntax checks.
- **Status:** [ ] Pending

### H11. Nginx config injection via `API_URL` env var
- **Component:** Nginx (`web/entrypoint.sh:4-28`)
- **Issue:** `API_URL` is interpolated into nginx config heredoc without sanitization.
- **Fix:** Validate URL format before interpolation.
- **Status:** [ ] Pending

---

## Medium-Priority Issues

### M1. No `.dockerignore` -- build context includes `.git/`, `out/`, `node_modules/`
- **Component:** Docker (root and `web/`)
- **Fix:** Add `.dockerignore` files to exclude unnecessary files (100MB+ bloat reduction).
- **Status:** [ ] Pending

### M2. All containers run as root
- **Component:** Docker (all 3 Dockerfiles)
- **Fix:** Add `RUN adduser -D appuser` and `USER appuser` directives.
- **Status:** [ ] Pending

### M3. Python 3.9 EOL, Node 18 past maintenance
- **Component:** Docker (all Dockerfiles)
- **Fix:** Upgrade to `python:3.12-alpine` and `node:20-alpine`.
- **Status:** [ ] Pending

### M4. API Dockerfile missing `--no-cache` on `apk add`
- **Component:** Docker (`api/Dockerfile:3`)
- **Fix:** Change to `apk add --no-cache sqlite`.
- **Status:** [ ] Pending

### M5. No `depends_on`, `healthcheck`, or `restart` in Compose
- **Component:** Docker (`docker-compose.yml`)
- **Fix:** Add `depends_on: api` for web, health checks using `/api/health`, restart policies.
- **Status:** [ ] Pending

### M6. No CORS configuration on API
- **Component:** API (`api/app.py`)
- **Fix:** Add `flask-cors` for development mode or document nginx-only approach.
- **Status:** [ ] Pending

### M7. No `limit`/`offset` bounds on API
- **Component:** API (`api/app.py:116-117`)
- **Fix:** Enforce max limit (e.g., 1000) and non-negative offset.
- **Status:** [ ] Pending

### M8. Gunicorn runs with 1 worker (default)
- **Component:** Docker (`api/Dockerfile:12`)
- **Fix:** Add `--workers 2` or use `WEB_CONCURRENCY` env var.
- **Status:** [ ] Pending

### M9. `INSERT OR IGNORE` silently drops updated data
- **Component:** SQL (`sqlite-init.sql:57-61`)
- **Fix:** Use `INSERT OR REPLACE` or `ON CONFLICT DO UPDATE` for data freshness.
- **Status:** [ ] Pending

### M10. No transaction wrapping in SQL migration
- **Component:** SQL (`sqlite-init.sql`)
- **Fix:** Wrap in `BEGIN; ... COMMIT;` to prevent partial state on interruption.
- **Status:** [ ] Pending

### M11. No indexes on `jobs_all` -- every API query is a full table scan
- **Component:** SQL (`sqlite-init.sql`)
- **Fix:** Add indexes on `company_id`, `workplace_city`, `workplace_state`, `department`, `workplace_type`, `type`, `source`, `title`.
- **Status:** [ ] Pending

### M12. Timestamped tables accumulate forever (49+ already)
- **Component:** SQL + Shell (`sqlite-init.sql`, `run_scrap.sh`)
- **Fix:** Add cleanup step to drop tables older than N runs or N days.
- **Status:** [ ] Pending

### M13. Shell script: existence check after first use, no `set -e`
- **Component:** Shell (`run_scrap.sh:23 vs 37`)
- **Fix:** Add `set -e`, move `sqlite-init.sql` check before first use.
- **Status:** [ ] Pending

### M14. Duplicated `formatWorkplaceType` / `formatJobType` functions
- **Component:** Web (`JobTable.jsx:9-43`, `JobDetails.jsx:6-40`)
- **Fix:** Extract to shared `utils/formatters.js`.
- **Status:** [ ] Pending

### M15. No `AbortController` -- rapid filter changes cause race conditions
- **Component:** Web (`web/src/App.js`)
- **Fix:** Add `AbortController` to `fetchJobs` with cleanup in useEffect.
- **Status:** [ ] Pending

### M16. No PropTypes or TypeScript on any component
- **Component:** Web (`web/src/`)
- **Fix:** Add PropTypes validation to all components.
- **Status:** [ ] Pending

### M17. No responsive design -- table unusable on mobile
- **Component:** Web (`web/src/App.css`)
- **Fix:** Add media queries for mobile breakpoints.
- **Status:** [ ] Pending

### M18. Page size `100` is magic number in two places
- **Component:** Web (`App.js:76,147`)
- **Fix:** Extract to `const PAGE_SIZE = 100`.
- **Status:** [ ] Pending

### M19. `.env_sample` is stale
- **Component:** Config (`.env_sample`)
- **Fix:** Add `GUPY_ENABLED`, `INHIRE_ENABLED`, `INHIRE_COMPANY_LIMIT`. Fix default mismatch.
- **Status:** [ ] Pending

### M20. `nginx.conf` is dead code -- never copied into Docker image
- **Component:** Web (`web/nginx.conf`)
- **Fix:** Remove or use as template instead of inline heredoc.
- **Status:** [ ] Pending

---

## Low-Priority / Code Quality Issues

### L1. No docstrings, no type hints in scraper (violates project style guide)
### L2. Hardcoded `yandeh` company injected unconditionally
### L3. Debug `print()` statements instead of `logging` module
### L4. Repeated `.get('workplace', {}).get('address', {})` chain
### L5. Unpinned `requirements.txt` (non-reproducible builds)
### L6. `SELECT *` everywhere in API -- fetches unnecessary columns
### L7. Magic number `8` for URL scheme length instead of `urlparse`
### L8. No global error handlers (`@app.errorhandler`) in API
### L9. `state`/`setState` variable name shadows React concept
### L10. All API logic inline in `App.js` instead of a service module
### L11. CSS classes referenced in JSX but never defined (`.type-*`, `.JobDetails-logo`)
### L12. No memoization (`React.memo`, `useCallback`, `useMemo`)
### L13. `companies.find()` linear search on every render per row
### L14. CI artifact named `jobhubmine_from_csv.db` (stale name)
### L15. No job timeout on CI `run-scraper`
### L16. `.gitignore` missing `node_modules/`, `__pycache__/`, `.DS_Store`
### L17. Unused `threading` import in scraper

---

## Implementation Phases

### Phase 1 -- Security & Correctness (Critical)
1. Validate `ts` input with regex in `run_scrap.sh` and `app/main.py`
2. Replace bare `except: pass` with proper exception handling
3. Fix CI tagging strategy
4. Remove exposed API port from docker-compose
5. Change debug default to `false`
6. Add `.dockerignore` files

### Phase 2 -- Robustness (High)
7. Add `set -e` to `run_scrap.sh`, reorder checks
8. Replace `print()` with Python `logging` module
9. Add error states to React UI
10. Fix `int()` casting and add bounds in API
11. Extract shared WHERE clause builder in API
12. Add `USER` directives to Dockerfiles
13. Fix null-safety for `job.source` in JobTable.jsx

### Phase 3 -- Performance & Maintainability (Medium)
14. Add database indexes
15. Use `INSERT OR REPLACE` for data freshness
16. Wrap SQL migration in transaction
17. Add `AbortController` to React fetch calls
18. Extract shared formatters to `utils/formatters.js`
19. Add PropTypes to all components
20. Add CI lint/test step
21. Upgrade Python/Node base images

### Phase 4 -- Polish (Low)
22. Add accessibility attributes (labels, ARIA, keyboard)
23. Add responsive media queries
24. Extract API service layer in React
25. Add constants for magic numbers, clean up dead code
26. Pin dependency versions, update `.env_sample`, `.gitignore`
