import logging
import re
from typing import Any, Dict, Tuple

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

logger = logging.getLogger(__name__)


def parse_job_card(card: WebElement) -> Dict[str, Any]:
    def text(selector: str) -> str:
        try:
            return card.find_element(By.CSS_SELECTOR, selector).text.strip()
        except NoSuchElementException:
            return ""

    def attr(selector: str, attribute: str) -> str:
        try:
            return card.find_element(By.CSS_SELECTOR, selector).get_attribute(attribute) or ""
        except NoSuchElementException:
            return ""

    title = text("h3.base-search-card__title")
    company = text("h4.base-search-card__subtitle")
    location_raw = text("span.job-search-card__location")
    posted_date = text("time.job-search-card__listdate")
    job_url = attr("a.base-card__full-link", "href").split("?")[0]
    workplace_badge = text("span.job-posting-benefits__text")

    # Job ID: prefer href, fall back to data-entity-urn on the base-card div
    job_id = ""
    id_match = re.search(r"/view/(\d+)", job_url)
    if id_match:
        job_id = id_match.group(1)
    else:
        urn = attr("div.base-card", "data-entity-urn")
        job_id = re.sub(r"[^0-9]", "", urn)

    city, state = split_location(location_raw)

    logger.debug("Card parsed: job_id=%s title=%r company=%r", job_id, title, company)

    return {
        "job_id": job_id,
        "title": title,
        "company": company,
        "location": location_raw,
        "city": city,
        "state": state,
        "workplace_type": workplace_badge,
        "job_url": job_url,
        "posted_date": posted_date,
    }


def parse_job_detail(driver) -> Dict[str, Any]:
    def text(css: str) -> str:
        try:
            return driver.find_element(By.CSS_SELECTOR, css).text.strip()
        except NoSuchElementException:
            return ""

    # Wait for the description section to load
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.show-more-less-html"))
        )
    except TimeoutException:
        logger.debug("Description section not found within timeout")

    description = text("div.show-more-less-html__markup")
    if not description:
        description = text("div.description__text")

    # Criteria items (seniority, employment type, etc.)
    seniority = ""
    employment_type = ""
    try:
        criteria_items = driver.find_elements(
            By.CSS_SELECTOR, "li.description__job-criteria-item"
        )
        for item in criteria_items:
            label = item.find_element(By.CSS_SELECTOR, "h3").text.strip().lower()
            value = item.find_element(By.CSS_SELECTOR, "span").text.strip()
            if "seniority" in label:
                seniority = value
            elif "employment" in label:
                employment_type = value
    except NoSuchElementException:
        pass

    logger.debug("Detail parsed: seniority=%r employment_type=%r desc_len=%d",
                 seniority, employment_type, len(description))

    return {
        "description": description,
        "seniority": seniority,
        "employment_type": employment_type,
    }


def split_location(raw: str) -> Tuple[str, str]:
    parts = [p.strip() for p in raw.split(",")]
    city = parts[0] if len(parts) > 0 else ""
    state = parts[1] if len(parts) > 1 else ""
    return city, state


def detect_rate_limit(driver) -> bool:
    title = driver.title.lower()
    url = driver.current_url.lower()

    # Real auth wall redirect
    if "authwall" in url:
        logger.warning("Auth wall redirect detected: %s", driver.current_url)
        return True

    # Cloudflare / bot challenges in the page title
    if any(s in title for s in ("just a moment", "attention required", "access denied")):
        logger.warning("Bot challenge page detected (title: %r)", driver.title)
        return True

    # LinkedIn sign-in wall: page has no job content and title says "sign in"
    if "sign in" in title and "jobs" not in title:
        logger.warning("Sign-in wall detected (title: %r)", driver.title)
        return True

    return False
