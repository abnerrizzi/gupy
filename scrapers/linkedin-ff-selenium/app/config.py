import os

# Selenium / WebDriver
SELENIUM_URL: str = os.environ.get("SELENIUM_URL", "http://localhost:4444/wd/hub")
BROWSER_TIMEOUT: int = int(os.environ.get("BROWSER_TIMEOUT", "30"))
IMPLICIT_WAIT: int = int(os.environ.get("IMPLICIT_WAIT", "10"))

# LinkedIn search
LINKEDIN_KEYWORDS: str = os.environ.get("LINKEDIN_KEYWORDS", "Software Engineer")
LINKEDIN_LOCATION: str = os.environ.get("LINKEDIN_LOCATION", "Brazil")
LINKEDIN_JOB_LIMIT: int = int(os.environ.get("LINKEDIN_JOB_LIMIT", "50"))
LINKEDIN_TIME_FILTER: str = os.environ.get("LINKEDIN_TIME_FILTER", "r86400")  # 24h = 86400s
LINKEDIN_SORT_BY: str = os.environ.get("LINKEDIN_SORT_BY", "DD")  # DD=latest, R=relevance
SCRAPE_DETAIL_PAGES: bool = os.environ.get("SCRAPE_DETAIL_PAGES", "true").lower() == "true"

# Anti-detection delays (seconds)
DELAY_MIN: float = float(os.environ.get("DELAY_MIN", "2.0"))
DELAY_MAX: float = float(os.environ.get("DELAY_MAX", "5.0"))
PAGE_LOAD_DELAY_MIN: float = float(os.environ.get("PAGE_LOAD_DELAY_MIN", "3.0"))
PAGE_LOAD_DELAY_MAX: float = float(os.environ.get("PAGE_LOAD_DELAY_MAX", "7.0"))
RETRY_ATTEMPTS: int = int(os.environ.get("RETRY_ATTEMPTS", "3"))
RETRY_DELAY: float = float(os.environ.get("RETRY_DELAY", "10.0"))
SCROLL_WAIT_SECONDS: float = float(os.environ.get("SCROLL_WAIT_SECONDS", "3.0"))
SCROLL_WAIT_RETRIES: int = int(os.environ.get("SCROLL_WAIT_RETRIES", "3"))

# Logging
LOG_LEVEL_STDOUT: str = os.environ.get("LOG_LEVEL_STDOUT", "INFO")
LOG_LEVEL_FILE: str = os.environ.get("LOG_LEVEL_FILE", "DEBUG")
LOG_DIR: str = os.environ.get("LOG_DIR", "/app/logs")
LOG_MAX_BYTES: int = int(os.environ.get("LOG_MAX_BYTES", str(10 * 1024 * 1024)))
LOG_BACKUP_COUNT: int = int(os.environ.get("LOG_BACKUP_COUNT", "5"))

# Output
OUTPUT_DIR: str = os.environ.get("OUTPUT_DIR", "/app/out")

# SQLite persistence
DB_PATH: str = os.environ.get("DB_PATH", "/app/out/jobhubmine.db")
SQLITE_INIT_SQL: str = os.environ.get("SQLITE_INIT_SQL", "/app/sqlite-init.sql")
LINKEDIN_WRITE_MODE: str = os.environ.get("LINKEDIN_WRITE_MODE", "append").strip().split("#")[0].strip() or "append"
