# AGENTS.md - Development Guidelines

This file contains guidelines for agentic coding agents working in this repository.

## Project Overview

This repository contains a job scraping system with three main components:
- `app/main.py` - Python scraper for various data sources
- `api/` - Flask REST API serving job data
- `web/` - React web UI for searching/filtering jobs
- `run_scrap.sh` - Shell script to run the full scraping pipeline (via Docker)

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

## Build/Lint/Test Commands

**CRITICAL: Do not run locally. Always use Docker to build and run the application.**

### Docker Compose (Recommended)
```bash
# Build all services
docker-compose build

# Start API and Web
docker-compose up -d

# Run scraper manually
docker-compose run --rm scraper
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `<SOURCE>_COMPANY_LIMIT` | Varies | Number of companies to fetch for a data source |
| `<SOURCE>_THREADS` | `16` | Parallel worker threads for a data source |
| `<SOURCE>_ENABLED` | `true` | Toggle a specific data source |
| `GUPY_OUTPUT_FOLDER` | CLI arg | Output directory |

### Linting
```bash
# Python (run via docker or locally if environment is setup)
python3 -m py_compile app/main.py api/app.py
flake8 app/main.py api/app.py

# React
cd web && npm run lint
```

### Testing
There are currently no automated test suites, so rely on manual validations. If `pytest` or `jest`/`react-scripts` testing are added, use the following commands:

```bash
# Run Python tests
pytest
pytest path/to/specific_test.py  # Run a single test

# Run React tests
cd web && npm test
cd web && npm test -- specific.test.js  # Run a single test

# Manual Testing Validations
ls -la out/
sqlite3 out/jobhubmine.db "SELECT COUNT(*) FROM jobs;"
curl http://localhost:5000/api/filters
curl http://localhost:8080/api/filters
```

## Code Style Guidelines

### Python (Scraper & API)
- **Formatting:** 4 spaces for indentation.
- **Naming Conventions:** `snake_case` for functions/variables, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants.
- **Types:** Provide type hints for all function signatures.
- **Strings:** Use f-strings for string interpolation.
- **Imports Order:** 1. Standard library, 2. Third-party packages, 3. Local modules.
- **Error Handling:** Use specific exception catches with clear logging. Avoid empty `except:` blocks.

```python
import os
import sys
import requests
from typing import Dict, List, Tuple
from concurrent.futures import ThreadPoolExecutor

def fetch_and_process_job_data(company: Dict) -> Tuple[Dict, List[Dict]]:
    """Fetches job data for a specific company."""
    try:
        company_id: str = company.get('companyId', '')
        # logic here
        return company_data, job_data_list
    except requests.RequestException as e:
        print(f"Error fetching data: {e}")
        raise
```

### React (Web UI)
- **Components:** Use functional components with React hooks.
- **Naming Conventions:** `PascalCase` for component names and files (`.jsx`), `camelCase` for props and variables.
- **Styles:** Use CSS modules or styled-components.

```jsx
function JobSearch({ value, onChange }) {
  return <input value={value} onChange={onChange} />;
}
```

### Shell Scripts
- Use `#!/bin/sh` for portability.
- Check file existence (`[ ! -f ... ]`) and executability.
- Always use proper variable quoting (e.g., `"$folder"` instead of `$folder`).

## Git & Commit Conventions

The project follows the **Conventional Commits Format**.
- **Format:** `type(scope): description`
- **Types:** `feat` (new feature), `fix` (bug fix), `refactor` (code refactoring), `chore` (maintenance, tooling), `docs` (documentation).
- **Example:** `feat(search): add 200ms debounce`
- Use the `auto-commit` skill (`.skills/auto-commit.md`) for automatic commits.
- **Exclusions:** Never commit generated output files (`out/`, `*.db`, `*.csv`), logs, or node_modules.

## File Organization

```
/home/abner.smartdb/src/jobhubmine/
├── app/              # Python Scraper
├── api/              # Flask API
├── web/              # React UI
├── docker-compose.yml
├── run_scrap.sh
├── sqlite-init.sql
├── .skills/          # Agent skills
└── out/              # Output (ignored in git)
```

## CI/CD

GitHub Actions (`.github/workflows/ci.yml`):
1. Builds scraper, API, and web images
2. Pushes to GHCR
3. Runs scraper in CI
4. Uploads SQLite as artifact
