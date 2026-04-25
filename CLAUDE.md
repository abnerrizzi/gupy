# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Core Mandates

1. **DOCKER ONLY:** Every project binary runs in a container — scraper, API, web, *and* ad-hoc validation (`sqlite3`, `flake8`, `npm`, `python3`). Never invoke them on the host, even for throwaway checks. Host tools reachable over the wire (e.g. `curl` against a published port) are fine.
2. **CONVENTIONAL COMMITS:** `type(scope): description` — max 70 chars, one line. Types: `feat`, `fix`, `refactor`, `chore`, `docs`.
3. **SOURCE AGNOSTIC:** Use generic "data source" terminology. Configure via `<SOURCE>_` prefix env vars.

## Build / Lint / Run

```bash
# Build all services
docker compose build

# Start API and Web UI (scraper, selenium, scraper-linkedin, linkedin-detail are profile-gated)
docker compose up -d
# Web UI: http://localhost:8080 | API: http://localhost:5000 (internal only; access via web proxy)

# Rebuild after code changes
docker compose build && docker compose up -d --force-recreate

# Run HTTP scraper — scraper profile auto-activates on `run`
docker compose run --rm scraper

# Run Selenium-based LinkedIn scraper — selenium starts via depends_on healthcheck
docker compose run --rm --build scraper-linkedin
# Inspect browser live at http://localhost:7900 (noVNC, no password)

# Bring up the on-demand LinkedIn detail sidecar (keeps a Selenium driver warm)
docker compose --profile linkedin up -d selenium linkedin-detail
```

### Linting

CI runs flake8 across the whole repo in two passes (`.github/workflows/ci.yml`):
1. Strict: `flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics` — fails build on syntax errors / undefined names.
2. Non-fatal: `flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics`.

Locally (no project image ships flake8 / node, so use ephemeral containers):

```bash
# Python lint (matches CI pass 1)
docker run --rm -v "$PWD:/src" -w /src python:3.12-slim sh -c 'pip install -q flake8 && flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics'

# React build validation
docker compose build web
```

### Manual Validation (no automated test suite)

The API is `expose: 5000` (internal to the compose network), reachable only via the web proxy at `localhost:8080/api/*`.

```bash
# SQLite via the scraper image (it already has sqlite3)
docker compose run --rm --no-deps --entrypoint sqlite3 scraper /app/out/jobhubmine.db "SELECT COUNT(*) FROM jobs_all;"

# API (through web proxy)
curl http://localhost:8080/api/health
curl http://localhost:8080/api/filters
curl "http://localhost:8080/api/jobs?limit=10&offset=0"

# On-demand job-detail fetch (writes the source-specific jobs_{source}_detail row).
# All three sources now resolve inside the API container — no sidecar required.
curl -X POST "http://localhost:8080/api/jobs/<job_id>/detail/fetch"
curl "http://localhost:8080/api/jobs/<job_id>/detail"

# Follow step-level fetch logs (all three sources log from the api container)
docker compose logs -f api
```

## Architecture

All services share a single SQLite file at `./out/jobhubmine.db`:

```
Scraper (Python) ──▶ SQLite ◀── API (Flask/Gunicorn) ◀── Web (React/Nginx)
                                    │
                                    └─▶ on-demand detail fetch
                                        (gupy, inhire, linkedin — all in-process)
```

- **HTTP Scraper** (`app/main.py` + `app/scrapers/` package) — runs on-demand via `docker compose run`. Each source is a `Scraper` subclass in `app/scrapers/<source>.py` (currently `GupyScraper`, `InhireScraper`), re-exported from `app/scrapers/__init__.py`. `KNOWN_SOURCES` in `app/main.py` gates which source names can become table-name suffixes (SQL-injection defence). A `ThreadPoolExecutor` per scraper parallelises `fetch_jobs` across companies.
- **Selenium scraper** (`scrapers/linkedin-ff-selenium/`) — Firefox-based LinkedIn *listings* scraper (detail is now fetched directly by the API — see below). The `selenium` and `scraper-linkedin` compose services sit behind the `linkedin` profile so they don't autostart on bare `up`. `docker compose run --rm scraper-linkedin` auto-activates the profile; selenium comes up via `depends_on` health check. Writes `out/linkedin_<ts>.json` AND loads rows into `jobs_linkedin_{ts}` / `companies_linkedin_{ts}` → merged into `_latest` via `sqlite-init.sql` (mounted read-only into the container). Unlike the HTTP scraper, it orchestrates its own schema init + merge in-process (see `app/db.py`) — it does not go through `run_scrap.sh`. Configured entirely via env vars in `.env` (git-ignored) overriding `.env_sample`.
- **API** (`api/app.py` + `api/fetchers/`) — Flask endpoints served by 2 Gunicorn workers (`--timeout 120` left over from the Selenium-sidecar era; LinkedIn fetches now take ~1 s). Read endpoints use `build_filters()` over `jobs_all`/`job_details` views; the write endpoint (`POST /api/jobs/<id>/detail/fetch`) dispatches per-source to fetchers in `api/fetchers/`. Each connection enables WAL once (`_enable_wal`) so API writes don't block a concurrent scraper run.
- **linkedin-detail sidecar** (`scrapers/linkedin-ff-selenium/app/detail_server.py`) — **legacy path**, still builds under the `linkedin` compose profile. The API no longer proxies to it (the LinkedIn fetcher now hits the public `jobs-guest/jobs/api/jobPosting/<id>` endpoint directly via `requests` + BeautifulSoup, see `api/fetchers/linkedin.py`). The sidecar is retained for situations where the guest endpoint is blocked or needs a logged-in session; re-wire it by pointing `LINKEDIN_DETAIL_URL` at it from the api service.
- **Web** (`web/src/`) — React SPA, state in `App.js`. Nginx proxies `/api/*` to Flask (**`proxy_read_timeout 120s`** to match the gunicorn timeout), eliminating CORS. `entrypoint.sh` injects `API_URL` at container start. `JobDetails.jsx` has two states driven by `has_detail`: **Sync** button vs. rendered payload (DOMPurify-sanitized HTML for all three sources; LinkedIn falls back to plain-text rendering for legacy Selenium-era rows via a `<`-prefix sniff). `utils/detailFields.js::extractCommonFacts` normalises the source-specific detail columns into one `{label,value}[]` list that both grids render. A collapsible `<details>` at the bottom renders the raw source JSON (`next_data`/`raw_payload`) via `JsonTree.jsx`.

### Container user model

All Python containers (`scraper`, `api`, `scraper-linkedin`, `linkedin-detail`) run as **uid 1000 appuser**. Each one's `entrypoint.sh` starts as root, `chown -R appuser:appuser /app/out`, then `exec su-exec appuser "$@"` (gosu equivalent on alpine). This keeps DB + output files writable across services regardless of which container created them first. If you add a new service that writes to `./out`, copy this pattern — otherwise a root-created file will lock out the api.

### API Endpoints

| Route | Purpose / key query params |
|---|---|
| `GET /api/health` | — |
| `GET /api/jobs` | `search`, `company_id`, `city`, `state`, `department`, `workplace_type`, `jobType`, `source`, `sort`, `order`, `limit` (max 1000), `offset`. Response includes `total` (filtered count) and `grand_total` (unfiltered count) so the SPA header can render "X jobs found in Y". |
| `GET /api/jobs/<job_id>` | Single job row (reads from `jobs_all` + `companies_all`). |
| `GET /api/jobs/<job_id>/detail` | 404 unless the detail has been synced; returns the source-specific `jobs_{source}_detail` row. |
| `POST /api/jobs/<job_id>/detail/fetch` | On-demand fetch. Dispatches to `api/fetchers/{source}.py`; LinkedIn hits `https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/<id>` directly (no sidecar). Upserts the row and returns it. 501 if the source isn't wired, 502 on upstream failure. |
| `GET /api/companies` | — |
| `GET /api/filters` | — |
| `POST /api/auth/register` | Body `{username, password}`. 201 + sets cookie session. 409 if username exists. 400 on invalid password. |
| `POST /api/auth/login` | Body `{username, password}`. 200 + cookie. 401 generic on bad credentials (no user enumeration). |
| `POST /api/auth/logout` | 204; clears the session cookie. |
| `GET /api/auth/me` | 200 with `{user: {id, username}}` if logged in, 401 otherwise. |
| `GET /api/me/tracked` | `@login_required` — returns the caller's saved jobs (joined `tracked_jobs`). |
| `POST /api/me/tracked` | `@login_required` — body is the snapshot from `web/src/App.js::jobRowToTracked`. Idempotent on `(user_id, job_id)`. |
| `PATCH /api/me/tracked/<job_id>` | `@login_required` — body `{stage?, notes?}`. Validates `stage` against `STAGE_ORDER`; appends a timeline event when `stage` changes. |
| `DELETE /api/me/tracked/<job_id>` | `@login_required` — 204 / 404. |

### Auth model

Cookie-session auth via `flask.session` (signed by `SECRET_KEY`, `HttpOnly`, `SameSite=Lax`, `Secure` when `SESSION_COOKIE_SECURE=true`). Password hashing via `werkzeug.security.generate_password_hash` / `check_password_hash` — no extra dep. Helpers and the `@login_required` decorator live in `api/auth.py`. The SPA reaches the API via the nginx proxy on the same origin, so cookies cross naturally; `web/src/utils/api.js::fetchJSON` always sets `credentials: 'include'`. Set `SECRET_KEY` in `.env` (sample in `.env_sample`).

### Database Pattern

Per-source tables with unioned views:

- Each scraper run creates `jobs_{source}_{ts}` and `companies_{source}_{ts}` timestamped tables (ts is digits-only; cross-checked against `KNOWN_SOURCES` to keep SQL-safe).
- `sqlite-init.sql` (applied pre- and post-scrape by `run_scrap.sh`) folds rows into per-source `_latest` tables via `INSERT OR REPLACE ... WHERE '${ts}' != '0'`, then recreates `jobs_all` / `companies_all` as `UNION ALL` VIEWS over every `_latest` table. `job_details` is a second view joining `jobs_all` + `companies_all` with URL synthesis per source.
- Per-source `<SOURCE>_WRITE_MODE` env var controls merge semantics: `replace` (default for gupy/inhire) wipes `_latest` before merging this run so dropped IDs disappear; `append` (default for linkedin) keeps prior rows. An `EXISTS` guard in `sqlite-init.sql` ensures an empty/failed run never wipes good data.
- Pre-split DBs (where `jobs_all` was a TABLE) are migrated once on first run by `migrate-to-per-source.sql`, guarded in `run_scrap.sh` via a `sqlite_master` type check. The migration redistributes rows by `source` column and drops the legacy tables so `sqlite-init.sql` can recreate the UNION views.
- Adding a new source means adding `CREATE TABLE` + `INSERT OR REPLACE` blocks + another `UNION ALL` arm in `sqlite-init.sql`, mirror entries in `migrate-to-per-source.sql`, a scraper class under `app/scrapers/`, and appending the source name to `KNOWN_SOURCES`.

### On-demand detail tables (separate from bulk scrape)

Per-source `jobs_{source}_detail` tables are populated by the POST `/detail/fetch` endpoint, not by the bulk scraper:

- Schema is source-specific:
  - **gupy**: `description_html`, `responsibilities_html`, `prerequisites_html`, `workplace_type`, `job_type`, `country`, `published_at`, `next_data` (raw `__NEXT_DATA__` JSON).
  - **inhire**: `description_html`, `about_html`, `contract_type`, `workplace_type`, `location`, `location_complement`, `published_at`, `raw_payload` (raw API JSON).
  - **linkedin**: `description` (HTML from guest endpoint), `seniority`, `employment_type`, `job_function`, `industries`, `posted_at` (ISO datetime parsed from "N hours ago"), `num_applicants` (INTEGER), `detail_html` (full guest HTML body).
- The `job_details` view LEFT JOINs all three detail tables and exposes `has_detail` + `detail_fetched_at` so the SPA can decide whether to show the Sync button.
- **Schema migration hook**: `api/app.py::_ensure_detail_schema` runs at module import and ALTERs each table to add or re-type columns declared in `_DETAIL_MIGRATIONS` (a map of `table → [(col, type), …]`). It also drops + re-adds a column whose current affinity differs from the declared type — needed because an earlier version of the hook always added `TEXT`, which broke `INTEGER` fields like `num_applicants`. When you add a new detail column, update the `CREATE TABLE` in `sqlite-init.sql` **and** the corresponding `_DETAIL_MIGRATIONS` entry; existing DBs pick it up on the next API start.
- Fetchers live in `api/fetchers/<source>.py`, registered in `api/fetchers/__init__.py::FETCHERS`. They return a dict whose keys match the detail-table columns (minus `id` and `fetched_at`); `upsert_detail` builds the `INSERT OR REPLACE` dynamically from the dict.
- The LinkedIn fetcher parses the guest-endpoint HTML with BeautifulSoup: description from `[class*=description] > section > div` (strips the `show-more-less-html__markup` wrapper), criteria list from `ul.description__job-criteria-list` (maps "Seniority level", "Employment type", "Job function", "Industries"), posted time from `[class*=posted-time-ago__text]` (converted to ISO via `_parse_posted_time_ago`), applicants from `[class*=num-applicants__*]` (integer via `_parse_applicants`). Document the endpoint shape at <https://gist.github.com/Diegiwg/51c22fa7ec9d92ed9b5d1f537b9e1107> if selectors change.

### Selenium Scraper Internals

`scrapers/linkedin-ff-selenium/app/linkedin.py` — `LinkedInSeleniumScraper.scrape_by_scrolling()` is the core loop: queries the card list, scrolls each card into center view (triggering LinkedIn's lazy loader), parses it immediately, then waits up to `SCROLL_WAIT_RETRIES × SCROLL_WAIT_SECONDS` for new cards before stopping. No detail page navigation — card-level data only. `_get_total_jobs()` falls back to counting rendered DOM cards when LinkedIn's results-header selectors don't match.

`scrapers/linkedin-ff-selenium/app/db.py` — `load_jobs_to_db()` re-reads the shared `sqlite-init.sql`, substitutes `${ts}` / `${*_mode}` placeholders in Python (same keys `run_scrap.sh:95-99` uses), and runs a three-phase merge: (A) apply schema with real `ts` + `linkedin_mode='append'` so staging tables get created and the merge DELETE/INSERT are no-ops via the `EXISTS` guard; (B) `INSERT OR IGNORE` the scraped rows into `jobs_linkedin_{ts}` / `companies_linkedin_{ts}`; (C) re-apply schema with the real `LINKEDIN_WRITE_MODE` so the merge into `_latest` actually fires. LinkedIn cards lack a stable company ID, so `_slugify(company_name)` derives one; the per-job URL is synthesised in the `job_details` view CASE (`https://www.linkedin.com/jobs/view/{id}`), not stored.

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
- Any externally-sourced HTML rendered via `dangerouslySetInnerHTML` must be piped through `DOMPurify.sanitize` first (see `JobDetails.jsx`).

## Key Files

| File | Purpose |
|------|---------|
| `app/main.py` | HTTP scraper entry point — orchestrates the per-source scrapers, writes `jobs_{source}_{ts}` tables |
| `app/scrapers/base.py` | `Scraper` base class + `get_http_session()` (retry/backoff) |
| `app/scrapers/__init__.py` | Re-exports each source scraper; must register new sources here |
| `api/app.py` | Flask endpoints, `build_filters()`, `_ensure_detail_schema` migration hook, WAL enable |
| `api/fetchers/` | On-demand detail fetchers (gupy, inhire, linkedin). `__init__.py::FETCHERS` dispatches by `source`. |
| `scrapers/linkedin-ff-selenium/app/detail_server.py` | Sidecar: Flask app wrapping a warm Selenium driver for per-job detail fetches |
| `web/src/components/JobDetails.jsx` | Two-state modal (Sync vs. rendered payload), source-specific rendering via `sourceBlocks()`, collapsible raw-JSON `<details>` |
| `web/src/components/JsonTree.jsx` | Minimal recursive JSON explorer (expand/collapse, colour-coded primitives) |
| `web/src/utils/detailFields.js` | `extractCommonFacts()` normaliser + date/country/seniority formatters used by `JobDetails.jsx` |
| `web/src/utils/formatters.js` | Portuguese labels for `workplace_type` and `job_type`, shared between table and modal |
| `entrypoint.sh` + `api/entrypoint.sh` | Root-level chown of `/app/out` then `su-exec appuser` — keeps scraper + api writing as uid 1000 |
| `sqlite-init.sql` | Full DB schema: per-source tables, `_latest` tables, UNION views. Runs pre- and post-scrape; `${ts}` substituted by `run_scrap.sh` |
| `migrate-to-per-source.sql` | One-shot migration from the pre-split `jobs_all`/`companies_all` TABLE schema; invoked conditionally by `run_scrap.sh` |
| `run_scrap.sh` | Validates timestamp, runs schema init, conditionally applies migration, runs scraper, re-applies schema |
| `docker-compose.yml` | All service definitions (`scraper`, `api`, `web`, `selenium`, `scraper-linkedin`). `scraper` uses the `scraper` profile; `selenium` + `scraper-linkedin` use the `linkedin` profile |
| `.env_sample` | Unified env var defaults for all services |
| `scrapers/linkedin-ff-selenium/app/linkedin.py` | Selenium scraper core logic |
| `scrapers/linkedin-ff-selenium/app/db.py` | In-process SQLite loader — renders `sqlite-init.sql` in Python and merges scraped cards into `_latest` |
| `scrapers/linkedin-ff-selenium/app/config.py` | All Selenium scraper config with defaults |
