# Epic: LinkedIn Firefox Selenium Scraper

## Overview
Create an isolated Docker container to scrape LinkedIn jobs using Firefox (Selenium). This scraper runs entirely in Docker without affecting the local machine.

## Stories

- [ ] **Story 1: Set up Docker environment with Firefox**
  - [x] Task 1.1: Create Dockerfile with Firefox + geckodriver
  - [x] Task 1.2: Create app/requirements.txt with selenium deps
  - [x] Task 1.3: Create docker-compose.yml for isolated scraper

- [ ] **Story 2: Implement LinkedIn scraper with Firefox**
  - [x] Task 2.1: Create base Scraper class
  - [x] Task 2.2: Create LinkedInFirefoxScraper using Selenium/Firefox
  - [x] Task 2.3: Implement job fetching logic
  - [x] Task 2.4: Implement job detail fetching

- [ ] **Story 3: Add database output**
  - [x] Task 3.1: Create SQLite output logic
  - [x] Task 3.2: Create run_scrap.sh entrypoint

- [ ] **Story 4: Configure environment variables**
  - [x] Task 4.1: Create .env_sample
  - [x] Task 4.2: Create sqlite-init.sql

- [ ] **Story 5: API service**
  - [x] Task 5.1: Create api/app.py
  - [x] Task 5.2: Create api/requirements.txt
  - [x] Task 5.3: Create api/Dockerfile

- [ ] **Story 6: Web UI**
  - [x] Task 6.1: Create React components
  - [x] Task 6.2: Create nginx + entrypoint
  - [x] Task 6.3: Create web/Dockerfile

- [ ] **Story 7: Test and validate**
  - [ ] Task 7.1: Copy .env_sample to .env and add credentials
  - [ ] Task 7.2: Run `docker-compose build`
  - [ ] Task 7.3: Run `docker-compose run --rm scraper`
  - [ ] Task 7.4: Verify output in `out/`
  - [ ] Task 7.5: Run `docker-compose up -d api web`
  - [ ] Task 7.6: Test web UI at http://localhost:8080

## Checklist for JR Developer

### Step-by-Step Execution

1. [ ] Read existing code in `/home/abner.smartdb/src/jobhubmine/app/main.py`
2. [ ] Read existing `Dockerfile` for patterns
3. [ ] Read existing `docker-compose.yml`
4. [ ] Review the new `linkedin_firefox_scraper/` structure
5. [ ] Copy `.env_sample` to `.env` and add LinkedIn credentials
6. [ ] Run `docker-compose build`
7. [ ] Run `docker-compose run --rm scraper`
8. [ ] Verify output in `linkedin_firefox_scraper/out/`
9. [ ] Run `docker-compose up -d api`
10. [ ] Run `docker-compose up -d web`
11. [ ] Test at http://localhost:8080

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LINKEDIN_EMAIL` | - | LinkedIn account email |
| `LINKEDIN_PASSWORD` | - | LinkedIn account password |
| `LINKEDIN_KEYWORDS` | `Software Engineer` | Job search keywords |
| `LINKEDIN_LOCATION` | `Brazil` | Job location filter |
| `LINKEDIN_LIMIT` | `50` | Max jobs to fetch |
| `LINKEDIN_THREADS` | `2` | Parallel workers |

## File Structure

```
linkedin_firefox_scraper/
├── Dockerfile
├── docker-compose.yml
├── .env_sample
├── run_scrap.sh
├── sqlite-init.sql
├── app/
│   ├── main.py
│   └── requirements.txt
├── api/
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile
├── web/
│   ├── Dockerfile
│   ├── package.json
│   ├── nginx.conf
│   ├── entrypoint.sh
│   ├── public/
│   │   └── index.html
│   └── src/
│       ├── index.js
│       ├── App.js
│       ├── App.css
│       ├── components/
│       │   ├── JobSearch.jsx
│       │   ├── FilterBar.jsx
│       │   ├── JobTable.jsx
│       │   └── JobDetails.jsx
│       └── utils/
│           └── formatters.js
└── out/
```

## Notes

- Never run Selenium locally, always inside Docker
- Use `headless` Firefox mode for no GUI
- Respect LinkedIn rate limits
- Store credentials in `.env` (gitignored)