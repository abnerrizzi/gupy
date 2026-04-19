# Gupy Job Scraping System

A complete pipeline for scraping job data from the Gupy API, storing it in SQLite, and serving it via a Flask API to a React web interface.

## Architecture

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

## Components

- **Scraper (`app/`)**: Python script that fetches job data and exports to CSV/SQLite.
- **API (`api/`)**: Flask REST API serving job filters and data.
- **Web (`web/`)**: React-based dashboard for searching and filtering jobs.

## Getting Started

### Using Docker Compose (Recommended)

1. **Build and start services**:
   ```bash
   docker-compose build
   docker-compose up -d
   ```
   *The API will be available at `http://localhost:5000` and the Web UI at `http://localhost:8080`.*

2. **Run Scraper manually**:
   ```bash
   docker-compose run --rm scraper
   ```

### Running Locally

1. **Run full pipeline**:
   ```bash
   ./run_scrap.sh out/
   ```

2. **Run components separately**:
   ```bash
   # Scraper only
   python3 app/main.py "<timestamp>" "<folder>"
   
   # Initialize SQLite from CSV
   ./create_sqlite_from_csv.sh "<timestamp>" "<folder>"
   ```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `GUPY_COMPANY_LIMIT` | `3` | Number of companies to fetch |
| `GUPY_THREADS` | `16` | Parallel worker threads |
| `GUPY_OUTPUT_FOLDER` | CLI arg | Output directory for CSV/DB files |

## Development

### Linting
```bash
python3 -m py_compile app/main.py api/app.py
# or
flake8 app/main.py api/app.py
```

### Verification
```bash
# Verify SQLite data
sqlite3 out/*.db "SELECT COUNT(*) FROM jobs;"

# Test API
curl http://localhost:5000/api/filters
```

## Project Structure

```
├── app/              # Scraper (Python)
├── api/              # Flask API
├── web/              # React UI
├── run_scrap.sh      # Pipeline script
├── sqlite-init.sql   # Database schema
└── out/              # Generated data (CSV/SQLite)
```
