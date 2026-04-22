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
    StaleElementReferenceException,
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
        logger.warning("Could not determine total jobs count from page")
        return 0

    def _save_page_source(self, label: str) -> None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(config.LOG_DIR, f"page_{label}_{ts}.html")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self.driver.page_source)
        logger.info("Page source saved → %s", path)

    def scroll_and_collect_cards(self, limit: int) -> List[Any]:
        cards: List[Any] = []
        stale_scrolls = 0
        max_stale = 3
        iteration = 0

        logger.info("Starting card collection (limit=%d)", limit)

        while len(cards) < limit and stale_scrolls < max_stale:
            iteration += 1
            logger.info("[iter %d] cards: %d / %d", iteration, len(cards), limit)

            try:
                elements = self.driver.find_elements(
                    By.CSS_SELECTOR, "ul.jobs-search__results-list li"
                )
            except WebDriverException:
                elements = []

            new_count = len(elements) - len(cards)
            if new_count <= 0:
                stale_scrolls += 1
                logger.info("[iter %d] no new cards — stale %d/%d", iteration, stale_scrolls, max_stale)
            else:
                stale_scrolls = 0
                cards = elements
                logger.info("[iter %d] +%d new cards → total %d", iteration, new_count, len(cards))

            if len(cards) >= limit:
                break

            # Scroll the last card into view first; fall back to the "show more"
            # button only if the scroll does not deliver new cards.
            if cards:
                logger.info("[iter %d] scrolling to card #%d", iteration, len(cards))
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'end', behavior: 'smooth'});",
                    cards[-1],
                )
                current_count = len(cards)
                logger.info("[iter %d] waiting for new cards (current: %d)...", iteration, current_count)
                try:
                    WebDriverWait(self.driver, 8).until(
                        lambda d: len(
                            d.find_elements(By.CSS_SELECTOR, "ul.jobs-search__results-list li")
                        ) > current_count
                    )
                    logger.info("[iter %d] new cards detected after scroll", iteration)
                except TimeoutException:
                    logger.info("[iter %d] scroll timed out — trying 'show more' button", iteration)
                    self._click_show_more()
            else:
                logger.info("[iter %d] no cards yet — full page scroll", iteration)
                self.session.scroll_incremental()
                self.session.random_delay(config.DELAY_MIN, config.DELAY_MAX)

            self.dismiss_ads()

            if detect_rate_limit(self.driver):
                logger.warning("Rate limit detected during card collection, stopping")
                break

        logger.info("Card collection done — %d cards in %d iterations", len(cards), iteration)
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

        card_elements = self.scroll_and_collect_cards(limit)
        logger.info("Collected %d card elements, parsing...", len(card_elements))

        jobs: List[Dict[str, Any]] = []
        for idx, card in enumerate(card_elements, 1):
            try:
                job = parse_job_card(card)
            except Exception as e:
                logger.warning("Card %d parse error: %s", idx, e)
                continue

            if not job.get("title"):
                logger.debug("Card %d — no title, skipping", idx)
                continue

            job["scraped_at"] = datetime.now(timezone.utc).isoformat()
            job["keywords"] = keywords
            job["search_location"] = location

            jobs.append(job)
            logger.info("[%d/%d] Scraped: %r @ %r", idx, len(card_elements), job["title"], job["company"])

        logger.info("Scrape session complete — %d jobs collected", len(jobs))
        return jobs
