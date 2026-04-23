import logging
import os
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List
from urllib.parse import urlencode

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchElementException,
    WebDriverException,
)
from selenium.webdriver.common.by import By

from app import config
from app.browser import BrowserSession
from app.parser import detect_rate_limit, parse_job_card, parse_job_detail

logger = logging.getLogger(__name__)

_SEARCH_BASE = "https://www.linkedin.com/jobs/search/"


class LinkedInSeleniumScraper:
    def __init__(self, session: BrowserSession):
        self.session = session
        self.driver = session.driver

    def build_search_url(self, keywords: str, location: str) -> str:
        params = urlencode({
            "keywords": keywords,
            "location": location,
            "position": 1,
            "pageNum": 0,
            "f_TPR": config.LINKEDIN_TIME_FILTER,
            "sortBy": config.LINKEDIN_SORT_BY,
        })
        return f"{_SEARCH_BASE}?{params}"

    def load_search_page(self, url: str) -> bool:
        logger.info("Navigating to search URL: %s", url)
        try:
            self.driver.get(url)
        except WebDriverException as e:
            logger.error("Page load failed: %s", e)
            return False

        self.session.random_delay(config.PAGE_LOAD_DELAY_MIN, config.PAGE_LOAD_DELAY_MAX)
        logger.debug("Page loaded — title: %r", self.driver.title)

        if detect_rate_limit(self.driver):
            return False

        self._save_page_source("search")
        self._get_total_jobs()
        self.dismiss_ads()
        return True

    def _get_total_jobs(self) -> int:
        selectors = [
            "span.results-context-header__job-count",
            "h1.results-context-header__query-search span",
            "div.results-context-header__job-count",
        ]
        for sel in selectors:
            try:
                raw = self.driver.find_element(By.CSS_SELECTOR, sel).text.strip()
                nums = re.findall(r"\d[\d,]*", raw)
                if nums:
                    total = int(nums[0].replace(",", ""))
                    logger.info("Total jobs available: %d (raw: %r)", total, raw)
                    return total
            except NoSuchElementException:
                continue
        try:
            card_count = len(self.driver.find_elements(
                By.CSS_SELECTOR, "ul.jobs-search__results-list li"
            ))
        except WebDriverException:
            card_count = 0
        if card_count > 0:
            logger.info(
                "Total jobs header not found — falling back to rendered card count: %d",
                card_count,
            )
            return card_count
        logger.warning("Could not determine total jobs count from page (no header, no cards)")
        return 0

    def _save_page_source(self, label: str) -> None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(config.LOG_DIR, f"page_{label}_{ts}.html")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self.driver.page_source)
        logger.info("Page source saved → %s", path)

    def scrape_by_scrolling(self, limit: int) -> List[Dict[str, Any]]:
        seen_ids: set = set()
        jobs: List[Dict[str, Any]] = []
        cursor = 0  # index of next unprocessed card in the DOM list

        while len(jobs) < limit:
            try:
                cards = self.driver.find_elements(
                    By.CSS_SELECTOR, "ul.jobs-search__results-list li"
                )
            except WebDriverException:
                cards = []

            if len(cards) <= cursor:
                logger.info("End of results — %d dom cards, %d jobs collected", len(cards), len(jobs))
                break

            logger.info("Batch: processing cards %d–%d", cursor + 1, len(cards))

            for i in range(cursor, len(cards)):
                card = cards[i]

                try:
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", card
                    )
                    self.session.random_delay(0.3, 0.6)
                    job = parse_job_card(card)
                except Exception as e:
                    logger.warning("Card %d error: %s", i + 1, e)
                    continue

                if not job.get("title"):
                    continue

                job_id = job.get("job_id", "")
                if job_id in seen_ids:
                    logger.debug("Card %d duplicate job_id=%s — skipping", i + 1, job_id)
                    continue
                seen_ids.add(job_id)

                job["scraped_at"] = datetime.now(timezone.utc).isoformat()
                jobs.append(job)
                logger.info("[%d] %r @ %r", len(jobs), job["title"], job["company"])

                if len(jobs) >= limit:
                    return jobs

            cursor = len(cards)

            self.dismiss_ads()
            if detect_rate_limit(self.driver):
                logger.warning("Rate limit detected — stopping")
                break

            page_total = self._get_total_jobs()
            live_count = len(self.driver.find_elements(By.CSS_SELECTOR, "ul.jobs-search__results-list li"))
            logger.info(
                "After batch: page_total=%d  dom_cards=%d  cursor=%d",
                page_total, live_count, cursor,
            )

            if live_count <= cursor:
                for attempt in range(1, config.SCROLL_WAIT_RETRIES + 1):
                    logger.info(
                        "No new cards yet — waiting %.1fs (attempt %d/%d)",
                        config.SCROLL_WAIT_SECONDS, attempt, config.SCROLL_WAIT_RETRIES,
                    )
                    time.sleep(config.SCROLL_WAIT_SECONDS)
                    live_count = len(self.driver.find_elements(
                        By.CSS_SELECTOR, "ul.jobs-search__results-list li"
                    ))
                    if live_count > cursor:
                        logger.info("+%d new cards appeared after wait", live_count - cursor)
                        break
                else:
                    logger.info("No new cards after %d retries — done", config.SCROLL_WAIT_RETRIES)
                    break

            logger.info("+%d new cards detected, continuing...", live_count - cursor)

        return jobs

    def dismiss_ads(self) -> None:
        selectors = [
            "button.artdeco-modal__dismiss",
            "button[aria-label='Dismiss']",
            "button[aria-label='Close']",
            "button[data-tracking-control-name='public_jobs_contextual-sign-in-modal_modal_dismiss']",
            "button[action-type='ACCEPT']",
        ]
        dismissed = 0
        for sel in selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, sel)
                if not elements or not elements[0].is_displayed():
                    continue
                self.driver.execute_script("arguments[0].click();", elements[0])
                logger.info("dismiss_ads: closed overlay — %s", sel)
                dismissed += 1
                self.session.random_delay(0.5, 1.0)
            except (ElementClickInterceptedException, WebDriverException):
                continue
        if not dismissed:
            logger.info("dismiss_ads: no overlays found")

    def scrape_detail_page(self, job_url: str) -> Dict[str, Any]:
        for attempt in range(1, config.RETRY_ATTEMPTS + 1):
            try:
                logger.debug("Visiting detail page (attempt %d): %s", attempt, job_url)
                self.driver.get(job_url)
                self.session.random_delay(config.PAGE_LOAD_DELAY_MIN, config.PAGE_LOAD_DELAY_MAX)

                if detect_rate_limit(self.driver):
                    logger.warning("Rate limit on detail page, backing off %.1fs", config.RETRY_DELAY)
                    time.sleep(config.RETRY_DELAY)
                    continue

                return parse_job_detail(self.driver)

            except WebDriverException as e:
                logger.warning("Detail page error (attempt %d/%d): %s", attempt, config.RETRY_ATTEMPTS, e)
                if attempt < config.RETRY_ATTEMPTS:
                    time.sleep(config.RETRY_DELAY)

        logger.error("Failed to scrape detail page after %d attempts: %s", config.RETRY_ATTEMPTS, job_url)
        return {}

    def scrape(self, keywords: str, location: str, limit: int) -> List[Dict[str, Any]]:
        logger.info("Scrape session start — keywords=%r location=%r limit=%d", keywords, location, limit)
        url = self.build_search_url(keywords, location)

        if not self.load_search_page(url):
            logger.error("Could not load search page, aborting")
            return []

        jobs = self.scrape_by_scrolling(limit)
        for job in jobs:
            job["keywords"] = keywords
            job["search_location"] = location

        logger.info("Scrape session complete — %d jobs collected", len(jobs))
        return jobs
