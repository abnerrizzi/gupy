import logging
import random
import time

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

logger = logging.getLogger(__name__)

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.4; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
]


class BrowserSession:
    def __init__(self, selenium_url: str, timeout: int):
        self.selenium_url = selenium_url
        self.timeout = timeout
        self.driver: webdriver.Remote | None = None

    def create_driver(self) -> webdriver.Remote:
        options = Options()

        # Anti-detection: hide webdriver flag
        options.set_preference("dom.webdriver.enabled", False)
        options.set_preference("useAutomationExtension", False)
        options.set_preference("privacy.resistFingerprinting", False)

        # Realistic UA
        ua = random.choice(_USER_AGENTS)
        options.set_preference("general.useragent.override", ua)
        logger.debug("Using user-agent: %s", ua)

        # Stable window size
        options.add_argument("--width=1920")
        options.add_argument("--height=1080")

        self.driver = webdriver.Remote(
            command_executor=self.selenium_url,
            options=options,
        )
        self.driver.set_page_load_timeout(self.timeout)
        self.driver.set_window_size(1920, 1080)
        logger.debug("WebDriver session created: %s", self.driver.session_id)
        return self.driver

    def random_delay(self, min_s: float, max_s: float) -> None:
        delay = random.uniform(min_s, max_s)
        logger.debug("Waiting %.1fs", delay)
        time.sleep(delay)

    def scroll_incremental(self, step: int = 400, pause: float = 0.4) -> None:
        total_height = self.driver.execute_script("return document.body.scrollHeight")
        current = 0
        while current < total_height:
            current = min(current + step, total_height)
            self.driver.execute_script(f"window.scrollTo(0, {current});")
            time.sleep(pause)
            total_height = self.driver.execute_script("return document.body.scrollHeight")

    def wait_for_element(self, by: By, value: str, timeout: int | None = None) -> WebElement:
        t = timeout or self.timeout
        return WebDriverWait(self.driver, t).until(
            EC.presence_of_element_located((by, value))
        )

    def safe_get_text(self, element: WebElement, css_selector: str) -> str:
        try:
            return element.find_element(By.CSS_SELECTOR, css_selector).text.strip()
        except NoSuchElementException:
            return ""

    def safe_get_attr(self, element: WebElement, css_selector: str, attr: str) -> str:
        try:
            return element.find_element(By.CSS_SELECTOR, css_selector).get_attribute(attr) or ""
        except NoSuchElementException:
            return ""

    def quit(self) -> None:
        if self.driver:
            try:
                self.driver.quit()
                logger.debug("WebDriver session closed")
            except Exception:
                pass
            self.driver = None
