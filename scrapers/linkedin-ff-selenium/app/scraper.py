import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from app import config


def setup_logging() -> logging.Logger:
    os.makedirs(config.LOG_DIR, exist_ok=True)
    log_file = os.path.join(config.LOG_DIR, "linkedin_selenium.log")

    fmt_simple = "%(asctime)s - %(levelname)s - %(message)s"
    fmt_detailed = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(config.LOG_LEVEL_STDOUT)
    stdout_handler.setFormatter(logging.Formatter(fmt_simple))

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=config.LOG_MAX_BYTES,
        backupCount=config.LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(config.LOG_LEVEL_FILE)
    file_handler.setFormatter(logging.Formatter(fmt_detailed))

    root.addHandler(stdout_handler)
    root.addHandler(file_handler)

    return logging.getLogger(__name__)


def main() -> None:
    logger = setup_logging()
    logger.info("LinkedIn Selenium Scraper starting — Python %s", sys.version.split()[0])
    logger.info(
        "Config: keywords=%r location=%r limit=%d detail_pages=%s selenium=%s",
        config.LINKEDIN_KEYWORDS,
        config.LINKEDIN_LOCATION,
        config.LINKEDIN_JOB_LIMIT,
        config.SCRAPE_DETAIL_PAGES,
        config.SELENIUM_URL,
    )

    from app.browser import BrowserSession
    from app.linkedin import LinkedInSeleniumScraper
    from app.output import write_json_output

    session = BrowserSession(config.SELENIUM_URL, config.BROWSER_TIMEOUT)

    try:
        session.create_driver()
        scraper = LinkedInSeleniumScraper(session)
        jobs = scraper.scrape(
            keywords=config.LINKEDIN_KEYWORDS,
            location=config.LINKEDIN_LOCATION,
            limit=config.LINKEDIN_JOB_LIMIT,
        )
        write_json_output(jobs, config.LINKEDIN_KEYWORDS, config.LINKEDIN_LOCATION, config.OUTPUT_DIR)
        logger.info("Done.")
    except Exception as e:
        logger.exception("Unhandled exception: %s", e)
        sys.exit(1)
    finally:
        session.quit()


if __name__ == "__main__":
    main()
