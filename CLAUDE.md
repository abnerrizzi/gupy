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

# Auth round-trip (cookie-session)
COOKIE=$(mktemp)
curl -s -c "$COOKIE" -X POST -H 'Content-Type: application/json' \
  -d '{"username":"demo","password":"hunter22pw"}' \
  http://localhost:8080/api/auth/register
curl -s -b "$COOKIE" http://localhost:8080/api/auth/me
curl -s -b "$COOKIE" -X POST -H 'Content-Type: application/json' \
  -d '{"job_id":"<id>","source":"gupy","title":"…"}' \
  http://localhost:8080/api/me/tracked
curl -s -b "$COOKIE" -X POST http://localhost:8080/api/auth/logout

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
- **Selenium scraper** (`scrapers/linkedin-ff-selenium/`) — Firefox-based LinkedIn *listings* scraper (detail is now fetched directly by the API — see below). The `selenium` and `scraper-linkedin` compose services sit behind the `linkedin` profile so they don't autostart on bare `up`. `docker compose run --rm scraper-linkedin` auto-activates the profile; selenium comes up via `depends_on` health check. Writes `out/linkedin_<ts>.json` AND loads rows into `jobs_linkedin_{ts}` / `companies_linkedin_{ts}` → merged into `_latest` via `sqlite-init.sql` (mounted read-only into the container). Configured entirely via env vars in `.env` (git-ignored) overriding `.env_sample`.
- **API** (`api/app.py` + `api/auth.py` + `api/fetchers/`) — Flask endpoints served by 2 Gunicorn workers (**`--timeout 120`** because the LinkedIn detail round-trip can take 30–60 s). Read endpoints use `build_filters()` over `jobs_all`/`job_details` views. Cookie-session auth + a per-user `tracked_jobs` table back the SPA's Saved/Pipeline pages. Each connection enables WAL once (`_enable_wal`) so API writes don't block a concurrent scraper run.
- **linkedin-detail sidecar** (`scrapers/linkedin-ff-selenium/app/detail_server.py`) — **legacy path**, still builds under the `linkedin` compose profile. The API no longer proxies to it (the LinkedIn fetcher now hits the public `jobs-guest/jobs/api/jobPosting/<id>` endpoint directly via `requests` + BeautifulSoup, see `api/fetchers/linkedin.py`).
- **Web** (`web/src/`) — React SPA, all top-level state in `App.js`. Sidebar shell at 240px with five pages: Dashboard / Buscar vagas (the API search) / Salvas / Pipeline (kanban) / collapsible user menu in the foot. Login gate uses real auth. Tracker (Saved/Pipeline) is API-backed (`useTrackedJobs`). Theme is a binary light/dark switch (`useTheme` + `data-theme` attribute), toggled in the user menu. Nginx proxies `/api/*` to Flask (**`proxy_read_timeout 120s`** to match the gunicorn timeout), eliminating CORS. `entrypoint.sh` injects `API_URL` at container start. `JobDetails.jsx` has two states driven by `has_detail`: **Sync** button vs. rendered payload (DOMPurify-sanitized HTML for all three sources; LinkedIn falls back to plain-text rendering for legacy Selenium-era rows via a `<`-prefix sniff). `utils/detailFields.js::extractCommonFacts` normalises source-specific details. A collapsible `<details>` at the bottom renders the raw source JSON (`next_data`/`raw_payload`) via `JsonTree.jsx`.

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
| `POST /api/auth/register` | Body `{username, password, name?, surname?}`. 201 + sets cookie session. 409 on duplicate username. 400 on invalid password (≥8 chars) or `name`/`surname` >64 chars. |
| `POST /api/auth/login` | Body `{username, password}`. 200 + cookie. 401 generic on bad credentials (no user enumeration). |
| `POST /api/auth/logout` | 204; clears the session cookie. |
| `GET /api/auth/me` | 200 with `{user: {id, username, name, surname}}` if logged in, 401 otherwise. |
| `GET /api/me/tracked` | `@login_required` — returns the caller's saved jobs. |
| `POST /api/me/tracked` | `@login_required` — body is the snapshot from `web/src/App.js::jobRowToTracked`. Idempotent on `(user_id, job_id)`. |
| `PATCH /api/me/tracked/<job_id>` | `@login_required` — body `{stage?, notes?}`. Validates `stage` against `STAGE_ORDER`; appends a timeline event when `stage` changes. |
| `DELETE /api/me/tracked/<job_id>` | `@login_required` — 204 / 404. |

### Auth model

Cookie-session auth via `flask.session` (signed by `SECRET_KEY`, `HttpOnly`, `SameSite=Lax`, `Secure` when `SESSION_COOKIE_SECURE=true`). 30-day permanent lifetime. Password hashing via `werkzeug.security.generate_password_hash` / `check_password_hash` — no extra dep. Helpers and the `@login_required` decorator live in `api/auth.py`. The SPA reaches the API via the nginx proxy on the same origin, so cookies cross naturally; `web/src/utils/api.js::fetchJSON` always sets `credentials: 'include'`. Set `SECRET_KEY` in `.env` (sample in `.env_sample`); the API raises at boot if `FLASK_ENV=production` and `SECRET_KEY` is missing.

### Database Pattern

Per-source tables with unioned views, plus app-state tables (`users`, `tracked_jobs`):

- Each scraper run creates `jobs_{source}_{ts}` and `companies_{source}_{ts}` timestamped tables (ts is digits-only; cross-checked against `KNOWN_SOURCES` to keep SQL-safe).
- `sqlite-init.sql` (applied pre- and post-scrape by `run_scrap.sh`) folds rows into per-source `_latest` tables via `INSERT OR REPLACE ... WHERE '${ts}' != '0'`, then recreates `jobs_all` / `companies_all` as `UNION ALL` VIEWs over every `_latest` table. `job_details` is a second view joining `jobs_all` + `companies_all` with URL synthesis per source.
- Per-source `<SOURCE>_WRITE_MODE` env var controls merge semantics: `replace` (default for gupy/inhire) wipes `_latest` before merging this run so dropped IDs disappear; `append` (default for linkedin) keeps prior rows. An `EXISTS` guard in `sqlite-init.sql` ensures an empty/failed run never wipes good data.
- Pre-split DBs (where `jobs_all` was a TABLE) are migrated once on first run by `migrate-to-per-source.sql`, guarded in `run_scrap.sh` via a `sqlite_master` type check.
- `users` and `tracked_jobs` are also defined in `sqlite-init.sql` (final block before `COMMIT`). They live alongside the scrape data so the same SQLite file is the single store.
- Adding a new scrape source means adding `CREATE TABLE` + `INSERT OR REPLACE` blocks + another `UNION ALL` arm in `sqlite-init.sql`, mirror entries in `migrate-to-per-source.sql`, a scraper class under `app/scrapers/`, and appending the source name to `KNOWN_SOURCES`.

### Schema migration hooks (idempotent, run at API boot)

`api/app.py` runs two migration helpers at module import — both safe to re-run:

- `_ensure_detail_schema()` walks `_DETAIL_MIGRATIONS` and `ALTER TABLE … ADD COLUMN` for any column missing from the existing `jobs_{source}_detail` tables (also retypes when affinity differs). `CREATE TABLE IF NOT EXISTS` cannot add columns to existing tables, so this hook is the only path to add new detail columns.
- `_ensure_app_schema()` `CREATE TABLE IF NOT EXISTS users (…)` and `tracked_jobs (…)` plus their indexes, and ALTERs `users` to add `name`/`surname` if missing. When you add a new column on either table: update the `CREATE TABLE` in `sqlite-init.sql` AND add the matching `PRAGMA table_info` + `ALTER TABLE` block here.

### On-demand detail tables (separate from bulk scrape)

Per-source `jobs_{source}_detail` tables are populated by the POST `/detail/fetch` endpoint, not by the bulk scraper:

- Schema is source-specific:
  - **gupy**: `description_html`, `responsibilities_html`, `prerequisites_html`, `workplace_type`, `job_type`, `country`, `published_at`, `next_data` (raw `__NEXT_DATA__` JSON).
  - **inhire**: `description_html`, `about_html`, `contract_type`, `workplace_type`, `location`, `location_complement`, `published_at`, `raw_payload` (raw API JSON).
  - **linkedin**: `description` (HTML from guest endpoint), `seniority`, `employment_type`, `job_function`, `industries`, `posted_at` (ISO datetime parsed from "N hours ago"), `num_applicants` (INTEGER), `detail_html` (full guest HTML body).
- The `job_details` view LEFT JOINs all three detail tables and exposes `has_detail` + `detail_fetched_at` so the SPA can decide whether to show the Sync button.
- **Schema migration hook**: `api/app.py::_ensure_detail_schema` runs at module import and ALTERs each table to add or re-type columns declared in `_DETAIL_MIGRATIONS`.
- Fetchers live in `api/fetchers/<source>.py`, registered in `api/fetchers/__init__.py::FETCHERS`. They return a dict whose keys match the detail-table columns (minus `id` and `fetched_at`); `upsert_detail` builds the `INSERT OR REPLACE` dynamically from the dict.
- The LinkedIn fetcher parses the guest-endpoint HTML with BeautifulSoup: description from `[class*=description] > section > div` (strips the `show-more-less-html__markup` wrapper), criteria list from `ul.description__job-criteria-list` (maps "Seniority level", "Employment type", "Job function", "Industries"), posted time from `[class*=posted-time-ago__text]` (converted to ISO via `_parse_posted_time_ago`), applicants from `[class*=num-applicants__*]` (integer via `_parse_applicants`). Document the endpoint shape at <https://gist.github.com/Diegiwg/51c22fa7ec9d92ed9b5d1f537b9e1107> if selectors change.

### Selenium Scraper Internals

`scrapers/linkedin-ff-selenium/app/linkedin.py` — `LinkedInSeleniumScraper.scrape_by_scrolling()` is the core loop: queries the card list, scrolls each card into center view (triggering LinkedIn's lazy loader), parses it immediately, then waits up to `SCROLL_WAIT_RETRIES × SCROLL_WAIT_SECONDS` for new cards before stopping. No detail page navigation — card-level data only. `_get_total_jobs()` falls back to counting rendered DOM cards when LinkedIn's results-header selectors don't match.

`scrapers/linkedin-ff-selenium/app/db.py` — `load_jobs_to_db()` re-reads the shared `sqlite-init.sql`, substitutes `${ts}` / `${*_mode}` placeholders in Python (same keys `run_scrap.sh:95-99` uses), and runs a three-phase merge: (A) apply schema with real `ts` + `linkedin_mode='append'` so staging tables get created and the merge DELETE/INSERT are no-ops via the `EXISTS` guard; (B) `INSERT OR IGNORE` the scraped rows into `jobs_linkedin_{ts}` / `companies_linkedin_{ts}`; (C) re-apply schema with the real `LINKEDIN_WRITE_MODE` so the merge into `_latest` actually fires. LinkedIn cards lack a stable company ID, so `_slugify(company_name)` derives one; the per-job URL is synthesised in the `job_details` view CASE (`https://www.linkedin.com/jobs/view/{id}`), not stored.

### Web SPA conventions

- **API URL convention**: `web/Dockerfile` builds with `ARG REACT_APP_API_URL=/api`. All `fetchJSON` calls in `web/src/utils/api.js` consumers (and the older `${API_URL}/…` calls in `App.js`) pass paths **without** the `/api/` prefix. Concatenation produces `/api/auth/me` etc. The fallback default in `api.js` is also `/api`. **Never bake `/api/` into a fetch path** — that produces `/api/api/…` 404s.
- **Tracker tokens (`STAGE_ORDER`)** are defined twice — once in `api/app.py` for server validation and once in `web/src/constants/stages.js` for UI rendering. Keep them in sync manually.
- **Tracker hook shape**: `useTrackedJobs(authStatus, onError)` returns `{trackedJobs, addJob, updateStage, updateNotes, removeJob, isTracked, loaded}` with optimistic updates and rollback on error. Same shape as the (now-replaced) localStorage version, so the kit pages (Dashboard / Saved / Pipeline / TrackedJobModal) didn't change.
- **Theme**: binary light/dark via `data-theme` attribute on `<html>`. `useTheme` writes to `localStorage.jh_theme` and falls back to `prefers-color-scheme` on first run. Only first-run respects the OS preference — explicit toggles stick. Tokens override block in `web/src/styles/tokens.css` (`:root[data-theme="dark"] { ... }`); colours flow through `--jh-surface` / `--jh-surface-2` / `--jh-fg` etc., aliased onto the legacy `--primary` / `--bg-color` names so existing `App.css` keeps working.
- **Two-modal pattern**: `JobDetails` (API-backed: Sync, JsonTree, DOMPurify) is the *primary* modal everywhere — clicking a tracked job from Dashboard / Saved / Pipeline opens it. The `TrackedJobModal` (notes + timeline + advance-stage) is reached via an "Anotações e linha do tempo" button inside `JobDetails` when the job is saved. Both wired through the shared `useModalA11y` hook (ESC-to-close + focus-on-open + focus-restore + `role="dialog" aria-modal="true"`).
- **`web/templates/jobhub_app/`** is the source design kit (Babel-standalone HTML/JSX/CSS). Reference only — not bundled. The web Dockerfile copies just `src/` and `public/`.

## Code Style

### Python

- Type hints **required** on all function signatures (`typing` module).
- Catch specific exceptions; log with `logger.error(..., exc_info=True)`.
- Always set `timeout=` on network requests.
- New HTTP data sources: add `app/scrapers/<source>.py` subclassing `Scraper` (from `app/scrapers/base.py`), implement `fetch_companies()` and `fetch_jobs(company)`, re-export from `app/scrapers/__init__.py`, append name to `KNOWN_SOURCES` in `app/main.py`, and extend `sqlite-init.sql` + `migrate-to-per-source.sql` per the Database Pattern notes.
- Protect new `/api/me/*` routes with `@login_required` from `api/auth.py`. Always scope queries by `current_user_id()` — never trust a user_id from request bodies.

### React

- Functional components with Hooks only — no class components.
- `prop-types` validation on all components.
- `fetch` inside `useEffect` with `AbortController` for cleanup, OR via `web/src/utils/api.js::fetchJSON` (which sets `credentials: 'include'` so the auth cookie crosses).
- Handle loading / error / success states explicitly.
- Any externally-sourced HTML rendered via `dangerouslySetInnerHTML` must be piped through `DOMPurify.sanitize` first (see `JobDetails.jsx`).
- Surface tracker-mutation errors through `useToasts()::push` (red toasts auto-dismiss in 4s).
- Prefer `setX(prev => …)` functional updates inside `useCallback` to avoid re-creating callbacks on every state change.

## Key Files

| File | Purpose |
|------|---------|
| `app/main.py` | HTTP scraper entry point — orchestrates the per-source scrapers, writes `jobs_{source}_{ts}` tables |
| `app/scrapers/base.py` | `Scraper` base class + `get_http_session()` (retry/backoff) |
| `app/scrapers/__init__.py` | Re-exports each source scraper; must register new sources here |
| `api/app.py` | Flask endpoints, `build_filters()`, schema-migration hooks (`_ensure_detail_schema`, `_ensure_app_schema`), WAL enable, auth + tracker routes |
| `api/auth.py` | Password hashing helpers, `@login_required`, `current_user_id()` |
| `api/fetchers/` | On-demand detail fetchers (gupy, inhire, linkedin). `__init__.py::FETCHERS` dispatches by `source`. |
| `scrapers/linkedin-ff-selenium/app/detail_server.py` | Sidecar: Flask app wrapping a warm Selenium driver for per-job detail fetches |
| `web/src/App.js` | Top-level state owner: auth gate, page switch, tracker, modal coordination |
| `web/src/utils/api.js` | `fetchJSON(path, opts)` — single source for cookies + JSON + error shape |
| `web/src/hooks/useAuth.js` | `{user, status, login, register, logout, refresh}` |
| `web/src/hooks/useTrackedJobs.js` | API-backed tracker with optimistic updates |
| `web/src/hooks/useTheme.js` | Binary light/dark, persisted in `localStorage.jh_theme`, applies `data-theme` to `<html>` |
| `web/src/hooks/useToasts.js` | Auto-dismissing transient errors, rendered by `ToastTray` |
| `web/src/hooks/useModalA11y.js` | Reusable ESC + focus management for both modals |
| `web/src/components/Sidebar.jsx` | 240px shell + collapsible user menu (Configurações / theme switch / Sair) |
| `web/src/components/JobDetails.jsx` | Two-state modal (Sync vs. rendered payload), source-specific rendering via `sourceBlocks()`, collapsible raw-JSON `<details>` |
| `web/src/components/TrackedJobModal.jsx` | Local notes + timeline + advance-stage modal for tracked jobs |
| `web/src/components/JsonTree.jsx` | Minimal recursive JSON explorer (expand/collapse, colour-coded primitives) |
| `web/src/utils/detailFields.js` | `extractCommonFacts()` normaliser + date/country/seniority formatters used by `JobDetails.jsx` |
| `web/src/utils/formatters.js` | Portuguese labels for `workplace_type` and `job_type`, shared between table and modal |
| `web/src/styles/tokens.css` | Design tokens incl. `data-theme="dark"` overrides; aliases legacy vars |
| `web/src/styles/shell.css` | Sidebar / kanban / saved-list / theme-switch / toast / login layout |
| `web/src/constants/stages.js` | `STAGE_META`, `STAGE_ORDER`, `STAGE_NEXT` (kept manually in sync with `api/app.py::STAGE_ORDER`) |
| `entrypoint.sh` + `api/entrypoint.sh` | Root-level chown of `/app/out` then `su-exec appuser` — keeps scraper + api writing as uid 1000 |
| `sqlite-init.sql` | Full DB schema: per-source tables, `_latest` tables, UNION views. Runs pre- and post-scrape; `${ts}` substituted by `run_scrap.sh` |
| `migrate-to-per-source.sql` | One-shot migration from the pre-split `jobs_all`/`companies_all` TABLE schema; invoked conditionally by `run_scrap.sh` |
| `run_scrap.sh` | Validates timestamp, runs schema init, conditionally applies migration, runs scraper, re-applies schema |
| `docker-compose.yml` | All service definitions (`scraper`, `api`, `web`, `selenium`, `scraper-linkedin`, `linkedin-detail`). `scraper` uses the `scraper` profile; `selenium` + `scraper-linkedin` + `linkedin-detail` use the `linkedin` profile |
| `.env_sample` | Unified env var defaults (incl. `SECRET_KEY`, `SESSION_COOKIE_SECURE`) for all services |
| `web/templates/jobhub_app/` | Source design kit (Babel-standalone), reference only — not bundled |
