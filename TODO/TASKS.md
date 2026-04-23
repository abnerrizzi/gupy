# Job Detail — Per-Source On-Demand Fetch

A board for a junior dev to pick up story-by-story. Each story = one commit (Conventional Commits, ≤70 chars). Tick the box when the acceptance criteria are met and commit.

## Context

Jobs are scraped as card-level rows today (title/company/location/type/link). There is no job description stored anywhere. This feature adds an on-demand **Sync** button: clicking it fetches the full posting from the source, persists the result in a per-source `jobs_{source}_detail` table, and renders it in the existing job modal.

Per-source tables (not one unified table) because each source ships a different payload shape — trying to flatten all three into one row would either be stringly-typed or extremely sparse.

Architecture sketch:

```
Web SPA ──POST /api/jobs/:id/detail/fetch──▶ api (Flask)
                                                ├── gupy    → HTTP inline (same container)
                                                ├── inhire  → HTTP inline
                                                └── linkedin → proxy to linkedin-detail sidecar (Selenium)
                                                                │
                                        all three write into ./out/jobhubmine.db
```

---

## EPIC 1 — Per-source detail tables in SQLite

- [x] **1.1 Lock the column list from real payloads**
  - [x] Scrape one gupy job's posting page and note which fields are present.
  - [x] Fetch one inhire `/vagas/{id}/description` and note its fields.
  - [x] Confirm LinkedIn's `parse_job_detail()` output keys (`scrapers/linkedin-ff-selenium/app/parser.py:60-103`).
  - [x] Record the decision (column names/types) below in the **Decisions** section.
  - Commit: `docs(tasks): lock per-source detail column list`

- [x] **1.2 Add detail tables + extend `job_details` view**
  - [x] `CREATE TABLE IF NOT EXISTS jobs_gupy_detail` in `sqlite-init.sql`.
  - [x] Same for `jobs_inhire_detail` and `jobs_linkedin_detail`.
  - [x] Extend the `job_details` view with LEFT JOINs → adds `has_detail` and `detail_fetched_at` columns.
  - Commit: `feat(db): add per-source job detail tables and view fields`
  - Acceptance:
    ```bash
    docker compose run --rm scraper
    docker compose run --rm --no-deps --entrypoint sqlite3 scraper /app/out/jobhubmine.db \
      ".schema jobs_gupy_detail"
    docker compose run --rm --no-deps --entrypoint sqlite3 scraper /app/out/jobhubmine.db \
      "SELECT has_detail FROM job_details LIMIT 3;"
    ```

## EPIC 2 — API: detail read + trigger

- [x] **2.1 `GET /api/jobs/<job_id>/detail`**
  - [x] SELECT from the right `jobs_{source}_detail` table based on the job's `source`.
  - [x] 404 when no row exists.
  - Commit: `feat(api): add GET job detail endpoint`
  - Acceptance: `curl http://localhost:8080/api/jobs/<id>/detail` returns 404 for an unfetched job.

- [x] **2.2 `POST /api/jobs/<job_id>/detail/fetch` skeleton**
  - [x] Source dispatch helper (look the job up in `jobs_all`, branch on `source`).
  - [x] Enable WAL once per connection so writes don't block scraper runs.
  - [x] Shared upsert helper (INSERT OR REPLACE).
  - [x] No per-source fetch code yet — each branch raises `NotImplementedError` (501).
  - Commit: `feat(api): add detail fetch skeleton and wal mode`

- [x] **2.3 Gupy fetcher**
  - [x] New package `api/fetchers/` (import `base.py` copied from `app/scrapers/`).
  - [x] `api/fetchers/gupy.py` — HTTP GET the job posting URL, parse `__NEXT_DATA__`, upsert.
  - [x] Wired into the POST endpoint via `FETCHERS` dict.
  - Commit: `feat(api): implement gupy job detail fetcher`
  - Verified: `jobs_gupy_detail` contains job 8106014 with 2961-char description after POST.

- [x] **2.4 Inhire fetcher**
  - [x] `api/fetchers/inhire.py` — HTTP GET `https://api.inhire.app/job-posts/public/pages/{id}` with `x-tenant` header, upsert. (The `vagas/` URL from the plan is a client-side React route; the JSON API is here.)
  - Commit: `feat(api): implement inhire job detail fetcher`
  - Verified: `jobs_inhire_detail` contains job d963cfa7-… with CLT contract + on-site + 2493-char description.

## EPIC 3 — LinkedIn detail sidecar

- [ ] **3.1 `detail_server.py` inside linkedin-ff-selenium**
  - [ ] Small Flask app exposing `POST /fetch/<job_id>`.
  - [ ] Boots a Selenium driver once, reuses it across requests.
  - [ ] Calls existing `LinkedInSeleniumScraper.scrape_detail_page()` and upserts into `jobs_linkedin_detail`.
  - Commit: `feat(linkedin): add on-demand detail fetch server`

- [ ] **3.2 `linkedin-detail` compose service**
  - [ ] Same image as `scraper-linkedin`, different entrypoint.
  - [ ] `linkedin` profile; `depends_on: selenium` with condition `service_healthy`.
  - [ ] Mount `./out:/app/out` for shared DB access.
  - Commit: `feat(compose): add linkedin-detail sidecar service`

- [ ] **3.3 API → sidecar proxy + nginx timeout**
  - [ ] `api/fetchers/linkedin.py` POSTs to `http://linkedin-detail:8000/fetch/<id>`, 90 s timeout.
  - [ ] `web/nginx.conf`: `proxy_read_timeout 120s;` on the `/api/` location.
  - Commit: `feat(api): proxy linkedin detail fetches to sidecar`
  - Acceptance:
    ```bash
    docker compose --profile linkedin up -d
    curl -X POST http://localhost:8080/api/jobs/<linkedin_id>/detail/fetch
    ```

## EPIC 4 — UI: Detail button + two-state modal

- [ ] **4.1 Detail column in `JobTable.jsx`**
  - [ ] Add an action column with a **Detail** button per row.
  - [ ] Clicking sets `selectedJob` (same flow as the existing row click).
  - Commit: `feat(web): add detail button column`

- [ ] **4.2 Sync action in `JobDetails.jsx`**
  - [ ] When `job.has_detail` is false, render a **Sync** button with a spinner while the POST is in-flight.
  - [ ] AbortController-based cleanup (match `App.js` style).
  - Commit: `feat(web): add sync action when detail missing`

- [ ] **4.3 Render fetched payload**
  - [ ] Header: title, company, workplace type, link, source badge.
  - [ ] Below: compact grid of source-specific fields (description HTML rendered via `DOMPurify.sanitize`).
  - [ ] Add `dompurify` to `web/package.json`; add `.detail-button` + `.detail-grid` to `App.css`.
  - Commit: `feat(web): render fetched job detail payload`

## EPIC 5 — E2E smoke test

- [ ] **5.1 Exercise Sync for one job per source**
  - [ ] Gupy: sync, confirm `jobs_gupy_detail` row, confirm modal renders.
  - [ ] Inhire: sync, confirm `jobs_inhire_detail` row, confirm modal renders.
  - [ ] LinkedIn: sync, confirm `jobs_linkedin_detail` row, confirm modal renders.
  - [ ] Record findings in **E2E results** section below.
  - Commit: `docs: record detail-fetch e2e smoke test results`

---

## Decisions (filled in during 1.1)

Investigated against three live jobs:

- **Gupy** → `https://{subdomain}.gupy.io/jobs/{id}` returns HTML with a `<script id="__NEXT_DATA__">` JSON block. The useful fields are `props.pageProps.job.{description, responsibilities, prerequisites}` (all HTML), plus `workplaceType`, `jobType`, `addressCountry`, `publishedAt`.
- **Inhire** → `https://api.inhire.app/job-posts/public/pages/{id}` returns JSON (requires the same `x-tenant` / `origin` / `referer` headers the listing scraper already uses). Useful fields: `description` (HTML), `about` (HTML, company blurb), `contractType` (list of strings — e.g. `["CLT"]`), `workplaceType`, `location`, `locationComplement`, `publishedAt`.
- **LinkedIn** → Already produced by `parse_job_detail()` in `scrapers/linkedin-ff-selenium/app/parser.py:60-103`: `description` (plain text — parser uses `.text`, not HTML), `seniority`, `employment_type`. No change needed to the parser.

Locked column list (all `_detail` tables also carry `id TEXT PRIMARY KEY` + `fetched_at TEXT NOT NULL`):

| Source   | Columns                                                                                                       |
| -------- | ------------------------------------------------------------------------------------------------------------- |
| gupy     | description_html, responsibilities_html, prerequisites_html, workplace_type, job_type, country, published_at  |
| inhire   | description_html, about_html, contract_type, workplace_type, location, location_complement, published_at      |
| linkedin | description, seniority, employment_type                                                                       |

Note: Gupy/Inhire `description*` fields are HTML and must be sanitized (`DOMPurify`) before rendering. LinkedIn's `description` is plain text and should render via `white-space: pre-wrap`.

## E2E results (filled in during 5.1)

_To be filled._
