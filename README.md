# JobHubMine Job Scraping System

A Dockerized pipeline to scrape, store, and browse job opportunities from Gupy and Inhire.

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

Customize behavior using environment variables in `docker-compose.yml` or a `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `GUPY_COMPANY_LIMIT` | `3` | Number of companies to scrape |
| `GUPY_THREADS` | `16` | Parallel worker threads |
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
