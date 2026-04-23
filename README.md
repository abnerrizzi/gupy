# JobHubMine Job Scraping System

A Dockerized pipeline to scrape, store, and browse job opportunities from various data sources.

## 🏗️ Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Scraper    │────▶│   SQLite     │◀────│     API      │
│  (Python)    │     │   Database   │     │   (Flask)    │
└──────────────┘     └──────────────┘     └──────────────┘
                                                  │
                                                  ▼
                                         ┌──────────────┐
                                         │     Web      │
                                         │   (React)    │
                                         └──────────────┘
```

## 💾 Data Flow (tables & views)

```
┌──────────────────────────────────────────────────────────────┐
│  Scraper  (app/main.py, per-source Scraper subclasses)       │
└──────────────────────────────┬───────────────────────────────┘
                               │  INSERT OR IGNORE
                               ▼
┌──────────────────────────────────────────────────────────────┐
│  Per-run ephemeral tables  (fresh set each scrape)           │
│    jobs_{source}_<ts>        companies_{source}_<ts>         │
└──────────────────────────────┬───────────────────────────────┘
                               │  sqlite-init.sql merge:
                               │   • DELETE  _latest  (if <SOURCE>_WRITE_MODE=replace
                               │                       and the <ts> table has rows)
                               │   • INSERT OR REPLACE  from  _<ts>
                               ▼
┌──────────────────────────────────────────────────────────────┐
│  Per-source _latest tables  (persistent source of truth)     │
│    jobs_gupy_latest          companies_gupy_latest           │
│    jobs_inhire_latest        companies_inhire_latest         │
│    jobs_linkedin_latest      companies_linkedin_latest       │
└──────────────────────────────┬───────────────────────────────┘
                               │  UNION ALL  (per source)
                               ▼
┌──────────────────────────────────────────────────────────────┐
│  Views  (what the API reads)                                 │
│    jobs_all       companies_all                              │
│    job_details    ◀── JOIN jobs_all + companies_all          │
│                       + per-source URL synthesis             │
└──────────────────────────────────────────────────────────────┘
```

- Ephemeral `_<ts>` tables keep every run isolated until the merge step.
- `<SOURCE>_WRITE_MODE` (`replace` | `append`) governs whether stale IDs in `_latest` survive a run. An `EXISTS` guard in `sqlite-init.sql` blocks the wipe when the current run produced no rows, so a disabled or failed scrape never destroys good data.
- The API only reads the views (`jobs_all`, `companies_all`, `job_details`) — adding a new source means extending the `UNION ALL` arm, not touching the API.

## 🚀 Getting Started (Docker)

This system is designed to run in Docker. Ensure [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) are installed.

1. **Launch Services**:
   ```bash
   docker-compose up -d
   ```
   * **Web UI**: [http://localhost:8080](http://localhost:8080)
   * **API**: [http://localhost:5000](http://localhost:5000)

2. **Scrape Data**:
   ```bash
   docker-compose run --rm scraper
   ```

## ⚙️ Configuration

Customize behavior using environment variables in `docker-compose.yml` or a `.env` file. `<SOURCE>` can be `GUPY`, `INHIRE`, or `LINKEDIN`.

| Variable | Default | Description |
|----------|---------|-------------|
| `<SOURCE>_COMPANY_LIMIT` | Varies | Number of companies/jobs to scrape |
| `<SOURCE>_THREADS` | `16` | Parallel worker threads |
| `<SOURCE>_ENABLED` | `true` | Toggle a specific data source |
| `LINKEDIN_KEYWORDS` | `Software Engineer` | LinkedIn search keywords |
| `LINKEDIN_LOCATION` | `Brazil` | LinkedIn search location |
| `JOBHUBMINE_DATABASE` | `/app/out/jobhubmine.db` | Container path to the SQLite database |

## 🛠️ Development

To rebuild services after code changes:
```bash
docker-compose build
docker-compose up -d --force-recreate
```

## 📂 Project Structure
- `app/`: Python scraper service.
- `api/`: Flask REST API service.
- `web/`: React frontend service.
- `out/`: Persistent storage for the SQLite database and logs.
