import shutil
from abc import ABC, abstractmethod
from typing import List, Dict
from loguru import logger
from selenium import webdriver

from selenium.webdriver import Remote, ChromeOptions as Options
from selenium.webdriver.chromium.remote_connection import ChromiumRemoteConnection as Connection

from .core import ScraperCore


class SimpleBaseScraper(ScraperCore, ABC):
    """
    Abstract Base Class for all shop scrapers.
    It defines the common interface (the "contract") that every
    concrete scraper must implement.
    """

    def __init__(self, shop_name: str, base_url: str):
        super().__init__()
        # Set up the WebDriver
        user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'
        options = webdriver.ChromeOptions()

        # --- Add this preference to disable images ---
        # 1: Allow all images / 2: Block all images
        prefs = {"profile.managed_default_content_settings.images": 2}
        options.add_experimental_option("prefs", prefs)

        options.add_argument(f'user-agent={user_agent}')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--headless')
        options.add_argument('--disable-plugins-discovery')
        options.add_argument('--disable-web-security')
        options.add_argument('--allow-running-insecure-content')
        options.add_argument('--start-maximized')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-browser-side-navigation')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('enable-automation')
        # Tell ChromeDriver to only log fatal errors.
        # Log level 3 is the most severe, effectively silencing most messages.
        options.add_argument('--log-level=3')

        try:
            # instantiate chromedriver
            # For ARM. Found at: https://stackoverflow.com/questions/76857893/is-there-a-known-working-configuration-for-using-selenium-on-linux-arm64
            chromedriver_path = shutil.which("chromedriver")
            service = webdriver.ChromeService(executable_path=chromedriver_path)
            driver = webdriver.Chrome(options=options, service=service)

            logger.info(
                f"Using chromedriver version {driver.capabilities['browserVersion']} located at {chromedriver_path}.")

            self.options = options
            self.shop_name = shop_name
            self.base_url = base_url
            self.driver = driver
        except Exception as e:
            logger.error("Could not instantiate chromedriver." + str(e))

    def __del__(self):
        self.driver.quit()
        logger.warning(f"Destructor of base class called for {self.shop_name}")

    @abstractmethod
    def search(self, product: str, category_id: int) -> List[Dict]:
        """
        Searches for products based on a query string.

        This method MUST be implemented by any class that inherits from SimpleBaseScraper.

        Args:
            product (str): The search term (e.g., 'Sucuk', 'Pirinc').
            category_id (int): The category id of a product (e.g. 21 for 'Meyve').

        Returns:
            A list of dictionaries, where each dictionary represents a found product.
            Example: [{'id': '123', 'name': 'Product A', 'price': 10.99}, ...]
        """
        pass
