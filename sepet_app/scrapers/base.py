import shutil
from abc import ABC, abstractmethod
from typing import List, Dict
from selenium import webdriver
from loguru import logger

class BaseScraper(ABC):
    """
    Abstract Base Class for all shop scrapers.
    It defines the common interface (the "contract") that every
    concrete scraper must implement.
    """
    def __init__(self, shop_name: str, base_url: str):
        # Set up the WebDriver
        user_agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.50 Safari/537.36'
        options = webdriver.ChromeOptions()
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


    @abstractmethod
    def search(self, query: str) -> List[Dict]:
        """
        Searches for products based on a query string.

        This method MUST be implemented by any class that inherits from BaseScraper.

        Args:
            query (str): The search term (e.g., 'Sucuk', 'Pirinc').

        Returns:
            A list of dictionaries, where each dictionary represents a found product.
            Example: [{'id': '123', 'name': 'Product A', 'price': 10.99}, ...]
        """
        pass