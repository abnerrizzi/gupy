# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Core Mandates

1. **DOCKER ONLY:** Never run the application locally. Always use Docker Compose.
2. **CONVENTIONAL COMMITS:** `type(scope): description` — max 70 chars, one line. Types: `feat`, `fix`, `refactor`, `chore`, `docs`.
3. **SOURCE AGNOSTIC:** Use generic "data source" terminology. Configure via `<SOURCE>_` prefix env vars.

## Build / Lint / Run

```bash
# Build all services
docker compose build

# Start API and Web UI (scraper, selenium, scraper-linkedin are profile-gated)
docker compose up -d
# Web UI: http://localhost:8080 | API: http://localhost:5000 (internal only; access via web proxy)

# Rebuild after code changes
docker compose build && docker compose up -d --force-recreate

# Run HTTP scraper — scraper profile auto-activates on `run`
docker compose run --rm scraper

# Run Selenium-based LinkedIn scraper — selenium starts via depends_on healthcheck
docker compose run --rm --build scraper-linkedin
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

- **HTTP Scraper** (`app/main.py` + `app/scrapers/` package) — runs on-demand via `docker compose run`. Each source is a `Scraper` subclass in `app/scrapers/<source>.py` (currently `GupyScraper`, `InhireScraper`), re-exported from `app/scrapers/__init__.py`. `KNOWN_SOURCES` in `app/main.py` gates which source names can become table-name suffixes (SQL-injection defence). A `ThreadPoolExecutor` per scraper parallelises `fetch_jobs` across companies.
- **Selenium scraper** (`scrapers/linkedin-ff-selenium/`) — Firefox-based LinkedIn scraper. The `selenium` and `scraper-linkedin` compose services sit behind the `linkedin` profile so they don't autostart on bare `up`. `docker compose run --rm scraper-linkedin` auto-activates the profile; selenium comes up via `depends_on` health check. Does not write to SQLite; outputs JSON to `/app/out/selenium/`. Configured entirely via env vars in `.env` (git-ignored) overriding `.env_sample`.
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

Per-source tables with unioned views:

- Each scraper run creates `jobs_{source}_{ts}` and `companies_{source}_{ts}` timestamped tables (ts is digits-only; cross-checked against `KNOWN_SOURCES` to keep SQL-safe).
- `sqlite-init.sql` (applied pre- and post-scrape by `run_scrap.sh`) folds rows into per-source `_latest` tables via `INSERT OR REPLACE ... WHERE '${ts}' != '0'`, then recreates `jobs_all` / `companies_all` as `UNION ALL` VIEWS over every `_latest` table. `job_details` is a second view joining `jobs_all` + `companies_all` with URL synthesis per source.
- Pre-split DBs (where `jobs_all` was a TABLE) are migrated once on first run by `migrate-to-per-source.sql`, guarded in `run_scrap.sh` via a `sqlite_master` type check. The migration redistributes rows by `source` column and drops the legacy tables so `sqlite-init.sql` can recreate the UNION views.
- Adding a new source means adding `CREATE TABLE` + `INSERT OR REPLACE` blocks + another `UNION ALL` arm in `sqlite-init.sql`, mirror entries in `migrate-to-per-source.sql`, a scraper class under `app/scrapers/`, and appending the source name to `KNOWN_SOURCES`.

### Selenium Scraper Internals

`scrapers/linkedin-ff-selenium/app/linkedin.py` — `LinkedInSeleniumScraper.scrape_by_scrolling()` is the core loop: queries the card list, scrolls each card into center view (triggering LinkedIn's lazy loader), parses it immediately, then waits up to `SCROLL_WAIT_RETRIES × SCROLL_WAIT_SECONDS` for new cards before stopping. No detail page navigation — card-level data only.

## Code Style

### Python

- Type hints **required** on all function signatures (`typing` module).
- Catch specific exceptions; log with `logger.error(..., exc_info=True)`.
- Always set `timeout=` on network requests.
- New HTTP data sources: add `app/scrapers/<source>.py` subclassing `Scraper` (from `app/scrapers/base.py`), implement `fetch_companies()` and `fetch_jobs(company)`, re-export from `app/scrapers/__init__.py`, append name to `KNOWN_SOURCES` in `app/main.py`, and extend `sqlite-init.sql` + `migrate-to-per-source.sql` per the Database Pattern notes.

### React

- Functional components with Hooks only — no class components.
- `prop-types` validation on all components.
- `fetch` inside `useEffect` with `AbortController` for cleanup.
- Handle loading / error / success states explicitly.

## Key Files

| File | Purpose |
|------|---------|
| `app/main.py` | HTTP scraper entry point — orchestrates the per-source scrapers, writes `jobs_{source}_{ts}` tables |
| `app/scrapers/base.py` | `Scraper` base class + `get_http_session()` (retry/backoff) |
| `app/scrapers/__init__.py` | Re-exports each source scraper; must register new sources here |
| `api/app.py` | Flask endpoints and `build_filters()` helper |
| `sqlite-init.sql` | Full DB schema: per-source tables, `_latest` tables, UNION views. Runs pre- and post-scrape; `${ts}` substituted by `run_scrap.sh` |
| `migrate-to-per-source.sql` | One-shot migration from the pre-split `jobs_all`/`companies_all` TABLE schema; invoked conditionally by `run_scrap.sh` |
| `run_scrap.sh` | Validates timestamp, runs schema init, conditionally applies migration, runs scraper, re-applies schema |
| `docker-compose.yml` | All service definitions (`scraper`, `api`, `web`, `selenium`, `scraper-linkedin`). `scraper` uses the `scraper` profile; `selenium` + `scraper-linkedin` use the `linkedin` profile |
| `.env_sample` | Unified env var defaults for all services |
| `scrapers/linkedin-ff-selenium/app/linkedin.py` | Selenium scraper core logic |
| `scrapers/linkedin-ff-selenium/app/config.py` | All Selenium scraper config with defaults |
