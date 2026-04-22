# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Core Mandates

1. **DOCKER ONLY:** Never run the application locally. Always use Docker Compose.
2. **CONVENTIONAL COMMITS:** `type(scope): description` — max 70 chars, one line. Types: `feat`, `fix`, `refactor`, `chore`, `docs`.
3. **SOURCE AGNOSTIC:** Use generic "data source" terminology. Configure via `<SOURCE>_` prefix env vars.

## Build / Lint / Run

```bash
# Build all services
docker-compose build

# Start API and Web UI (name services explicitly to avoid starting selenium)
docker-compose up -d api web
# Web UI: http://localhost:8080 | API: http://localhost:5000

# Rebuild after code changes
docker-compose build api web && docker-compose up -d --force-recreate api web

# Run scraper (scraper profile required for `up`; `run` works directly)
docker-compose run --rm scraper

# Run Selenium-based LinkedIn scraper
docker-compose build scraper-selenium
docker-compose up -d firefox          # start browser, wait for healthy
docker-compose run --rm scraper-selenium
# Inspect browser live at http://localhost:7900 (noVNC, no password)
```

### Linting

```bash
# Python syntax check
python3 -m py_compile app/main.py api/app.py

# Python style (CI uses: E9,F63,F7,F82 + W503 warning)
flake8 app/main.py api/app.py

# React (validates build + JS errors)
cd web && npm run build
```

### Manual Validation (no automated test suite)

```bash
sqlite3 out/jobhubmine.db "SELECT COUNT(*) FROM jobs_all;"
curl http://localhost:5000/api/health
curl http://localhost:5000/api/filters
curl "http://localhost:5000/api/jobs?limit=10&offset=0"
```

## Architecture

Three Docker services share a single SQLite file at `./out/jobhubmine.db`:

```
Scraper (Python) ──▶ SQLite ◀── API (Flask/Gunicorn) ◀── Web (React/Nginx)
```

- **Scraper** (`app/main.py`) — runs on-demand via `docker-compose run`. `GupyScraper`, `InhireScraper`, and `LinkedInScraper` subclass `Scraper`, which defines `fetch_companies()` and `fetch_jobs(company)`. A `ThreadPoolExecutor` per scraper parallelises `fetch_jobs` across companies.
- **Selenium scraper** (`scraper-selenium/`) — Firefox-based LinkedIn scraper running under the `selenium` compose profile. Does not write to SQLite; outputs JSON to `/app/out/`. Controlled entirely via env vars in `.env` (git-ignored) overriding `.env_sample`.
- **API** (`api/app.py`) — five read-only Flask endpoints served by 2 Gunicorn workers. Filter logic is built dynamically in `build_filters()`.
- **Web** (`web/src/`) — React SPA, state in `App.js`. Nginx proxies `/api/*` to Flask, eliminating CORS. `entrypoint.sh` injects `API_URL` at container start.

### API Endpoints

| Route | Key query params |
|---|---|
| `GET /api/health` | — |
| `GET /api/jobs` | `search`, `company_id`, `city`, `state`, `department`, `workplace_type`, `jobType`, `source`, `sort`, `order`, `limit` (max 1000), `offset` |
| `GET /api/jobs/<job_id>` | — |
| `GET /api/companies` | — |
| `GET /api/filters` | — |

### Database Pattern

Each scraper run creates `jobs_{ts}` and `companies_{ts}` timestamped tables. `run_scrap.sh` merges them into permanent `jobs_all` / `companies_all` tables via `INSERT OR IGNORE`. The API queries through the `job_details` view (denormalised join with URL construction). Schema lives in `sqlite-init.sql`.

### Selenium Scraper Internals

`scraper-selenium/app/linkedin.py` — `LinkedInSeleniumScraper.scrape_by_scrolling()` is the core loop: queries the card list, scrolls each card into center view (triggering LinkedIn's lazy loader), parses it immediately, then waits up to `SCROLL_WAIT_RETRIES × SCROLL_WAIT_SECONDS` for new cards before stopping. No detail page navigation — card-level data only.

## Code Style

### Python

- Type hints **required** on all function signatures (`typing` module).
- Catch specific exceptions; log with `logger.error(..., exc_info=True)`.
- Always set `timeout=` on network requests.
- New data sources: subclass `Scraper`, implement `fetch_companies()` and `fetch_jobs()`.

### React

- Functional components with Hooks only — no class components.
- `prop-types` validation on all components.
- `fetch` inside `useEffect` with `AbortController` for cleanup.
- Handle loading / error / success states explicitly.

## Key Files

| File | Purpose |
|------|---------|
| `app/main.py` | Scraper entry point and all scraper classes |
| `api/app.py` | Flask endpoints and `build_filters()` helper |
| `sqlite-init.sql` | Full DB schema — changes need migration planning |
| `run_scrap.sh` | Validates timestamp, runs schema init, merges timestamped tables into `_all` |
| `docker-compose.yml` | All service definitions (`scraper`, `api`, `web`, `selenium` profile) |
| `.env_sample` | Unified env var defaults for all services |
| `scraper-selenium/app/linkedin.py` | Selenium scraper core logic |
| `scraper-selenium/app/config.py` | All Selenium scraper config with defaults |
