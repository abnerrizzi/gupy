import logging
import time
from typing import Any, Dict, List
from urllib.parse import urlencode

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

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

        self.dismiss_ads()
        return True

    def scroll_and_collect_cards(self, limit: int) -> List[Any]:
        cards: List[Any] = []
        stale_scrolls = 0
        max_stale = 3

        logger.info("Collecting job cards (limit=%d)...", limit)

        while len(cards) < limit and stale_scrolls < max_stale:
            try:
                elements = self.driver.find_elements(
                    By.CSS_SELECTOR, "ul.jobs-search__results-list li"
                )
            except WebDriverException:
                elements = []

            new_count = len(elements) - len(cards)
            if new_count <= 0:
                stale_scrolls += 1
                logger.debug("No new cards after scroll (stale=%d/%d)", stale_scrolls, max_stale)
            else:
                stale_scrolls = 0
                cards = elements
                logger.info("%d job cards found so far", len(cards))

            if len(cards) >= limit:
                break

            # Try to load more via button, then scroll the last card into view
            # to trigger LinkedIn's lazy loader; fall back to full-page scroll
            if not self._click_show_more():
                if cards:
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({block: 'end', behavior: 'smooth'});",
                        cards[-1],
                    )
                else:
                    self.session.scroll_incremental()

            self.session.random_delay(config.DELAY_MIN, config.DELAY_MAX)
            self.dismiss_ads()

            if detect_rate_limit(self.driver):
                logger.warning("Rate limit detected during card collection, stopping")
                break

        return cards[:limit]

    def _click_show_more(self) -> bool:
        selectors = [
            "button.infinite-scroller__show-more-button",
            "button[aria-label='Load more results']",
            "button.see-more-jobs",
        ]
        for sel in selectors:
            try:
                btn = self.driver.find_element(By.CSS_SELECTOR, sel)
                self.driver.execute_script("arguments[0].click();", btn)
                logger.debug("Clicked 'show more' button (%s)", sel)
                self.session.random_delay(1.5, 3.0)
                return True
            except (NoSuchElementException, ElementClickInterceptedException):
                continue
        return False

    def dismiss_ads(self) -> None:
        selectors = [
            "button.artdeco-modal__dismiss",
            "button[aria-label='Dismiss']",
            "button[aria-label='Close']",
            "button[data-tracking-control-name='public_jobs_contextual-sign-in-modal_modal_dismiss']",
            "button[action-type='ACCEPT']",
        ]
        for sel in selectors:
            try:
                btn = WebDriverWait(self.driver, 2).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, sel))
                )
                self.driver.execute_script("arguments[0].click();", btn)
                logger.debug("Dismissed overlay (%s)", sel)
                self.session.random_delay(0.5, 1.0)
            except (NoSuchElementException, TimeoutException, ElementClickInterceptedException):
                continue

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
        from datetime import datetime, timezone

        logger.info("Scrape session start — keywords=%r location=%r limit=%d", keywords, location, limit)
        url = self.build_search_url(keywords, location)

        if not self.load_search_page(url):
            logger.error("Could not load search page, aborting")
            return []

        card_elements = self.scroll_and_collect_cards(limit)
        logger.info("Collected %d card elements, parsing...", len(card_elements))

        jobs: List[Dict[str, Any]] = []
        search_url = self.driver.current_url  # save for navigation back

        for i, card in enumerate(card_elements, 1):
            try:
                job = parse_job_card(card)
            except Exception as e:
                logger.error("Error parsing card %d: %s", i, e)
                continue

            if not job.get("title"):
                logger.debug("Skipping card %d — no title extracted", i)
                continue

            if config.SCRAPE_DETAIL_PAGES and job.get("job_url"):
                detail = self.scrape_detail_page(job["job_url"])
                job.update(detail)
                # Return to search results
                try:
                    self.driver.get(search_url)
                    self.session.random_delay(config.PAGE_LOAD_DELAY_MIN, config.PAGE_LOAD_DELAY_MAX)
                except WebDriverException:
                    pass

            job["scraped_at"] = datetime.now(timezone.utc).isoformat()
            job["keywords"] = keywords
            job["search_location"] = location

            # Ensure all schema fields exist
            for field in ("seniority", "employment_type", "description"):
                job.setdefault(field, "")

            jobs.append(job)
            logger.info("[%d/%d] Scraped: %r @ %r", i, len(card_elements), job["title"], job["company"])

            self.session.random_delay(config.DELAY_MIN, config.DELAY_MAX)

        logger.info("Scrape session complete — %d jobs collected", len(jobs))
        return jobs
