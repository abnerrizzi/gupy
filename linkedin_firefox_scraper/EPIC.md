# Epic: LinkedIn Firefox Selenium Scraper

## Overview
Create an isolated Docker container to scrape LinkedIn jobs using Firefox (Selenium). This scraper runs entirely in Docker without affecting the local machine.

## Stories

- [ ] **Story 1: Set up Docker environment with Firefox**
  - [ ] Task 1.1: Create Dockerfile with Firefox + geckodriver
  - [ ] Task 1.2: Create app/requirements.txt with selenium deps
  - [ ] Task 1.3: Create docker-compose.yml for isolated scraper

- [ ] **Story 2: Implement LinkedIn scraper with Firefox**
  - [ ] Task 2.1: Create base Scraper class
  - [ ] Task 2.2: Create LinkedInScraper using Selenium/Firefox
  - [ ] Task 2.3: Implement job fetching logic
  - [ ] Task 2.4: Implement job detail fetching

- [ ] **Story 3: Add database output**
  - [ ] Task 3.1: Create SQLite output logic
  - [ ] Task 3.2: Create run_scrap.sh entrypoint

- [ ] **Story 4: Configure environment variables**
  - [ ] Task 4.1: Create .env_sample
  - [ ] Task 4.2: Update AGENTS.md with new structure

- [ ] **Story 5: Test and validate**
  - [ ] Task 5.1: Build Docker image
  - [ ] Task 5.2: Run scraper via docker-compose
  - [ ] Task 5.3: Validate output data

## Checklist for JR Developer

Follow this checklist step by step. Commit after completing each task.

### Prerequisites
- [ ] Docker installed
- [ ] Docker Compose installed
- [ ] Basic Python knowledge
- [ ] Understanding of Selenium WebDriver

### Step-by-Step Execution

1. [ ] Read existing code in `/home/abner.smartdb/src/jobhubmine/app/main.py`
2. [ ] Read existing `Dockerfile` for patterns
3. [ ] Read existing `docker-compose.yml`
4. [ ] Create new folder: `linkedin_firefox_scraper/`
5. [ ] Create `linkedin_firefox_scraper/Dockerfile`
6. [ ] Create `linkedin_firefox_scraper/app/requirements.txt`
7. [ ] Create `linkedin_firefox_scraper/app/main.py`
8. [ ] Create `linkedin_firefox_scraper/run_scrap.sh`
9. [ ] Create `linkedin_firefox_scraper/docker-compose.yml`
10. [ ] Create `linkedin_firefox_scraper/.env_sample`
11. [ ] Run `docker-compose build`
12. [ ] Run `docker-compose run --rm scraper`
13. [ ] Verify output in `linkedin_firefox_scraper/out/`

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LINKEDIN_EMAIL` | - | LinkedIn account email |
| `LINKEDIN_PASSWORD` | - | LinkedIn account password |
| `LINKEDIN_KEYWORDS` | `Software Engineer` | Job search keywords |
| `LINKEDIN_LOCATION` | `Brazil` | Job location filter |
| `LINKEDIN_LIMIT` | `50` | Max jobs to fetch |

## File Structure

```
linkedin_firefox_scraper/
├── Dockerfile
├── docker-compose.yml
├── .env_sample
├── run_scrap.sh
├── app/
│   ├── main.py
│   └── requirements.txt
└── out/
```

## Notes

- Never run Selenium locally, always inside Docker
- Use `headless` Firefox mode for no GUI
- Respect LinkedIn rate limits
- Store credentials in `.env` (gitignored)