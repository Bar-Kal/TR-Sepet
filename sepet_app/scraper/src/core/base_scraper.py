import shutil
from abc import ABC, abstractmethod
from typing import List
from loguru import logger
from .core import ScraperCore
from selenium import webdriver

def _create_driver(driver_name: str):
    if driver_name == "chrome":
        user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'
        options = webdriver.ChromeOptions()

        # --- Add this preference to disable images -- -
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
        options.add_argument("--disable-geolocation")
        options.add_argument("--disable-popup-blocking")
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
            return driver
        except Exception as e:
            logger.error("Could not instantiate chromedriver." + str(e))
            return None
    elif driver_name == "firefox":
        user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0'
        options = webdriver.FirefoxOptions()

        # --- Add this preference to disable images -- -
        # 1: Allow all images / 2: Block all images
        options.set_preference("permissions.default.image", 2)
        # --- Add this preference to disable JavaScript ---
        options.set_preference("javascript.enabled", False)

        options.add_argument(f'user-agent={user_agent}')
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument("-width=1920")
        options.add_argument("-height=1080")

        try:
            # instantiate geckodriver
            geckodriver_path = shutil.which("geckodriver")
            service = webdriver.FirefoxService(executable_path=geckodriver_path)
            driver = webdriver.Firefox(options=options, service=service)

            logger.info(
                f"Using geckodriver version {driver.capabilities['browserVersion']} located at {geckodriver_path}.")
            return driver
        except Exception as e:
            logger.error("Could not instantiate geckodriver." + str(e))
            return None
    else:
        raise ValueError(f"Unknown driver: {driver_name}")


class BaseScraper(ScraperCore, ABC):
    """
    Abstract Base Class for all shop scraper.
    It defines the common interface (the "contract") that every
    concrete scraper must implement.
    """

    def __init__(self, shop_id: int, shop_name: str, base_url: str, driver_name: str, ignore_nonfood: bool = False):
        super().__init__()
        self.driver = _create_driver(driver_name)
        if self.driver:
            self.shop_id = shop_id
            self.shop_name = shop_name
            self.base_url = base_url
            self.ignore_nonfood = ignore_nonfood
        else:
            logger.error(f"Failed to create webdriver for {shop_name} with shop_id: {shop_id}")

    def __del__(self):
        if self.driver:
            self.driver.quit()
            logger.warning(f"Destructor of base class called for {self.shop_name}")

    @abstractmethod
    def search(self, product: dict) -> List[dict]:
        """
        Searches for products based on a query string.

        This method MUST be implemented by any class that inherits from BaseScraper.

        Args:
            product (dict): The food product from food.json.

        Returns:
            A list of dictionaries, where each dictionary represents a found product.
            Example: [{'id': '123', 'name': 'Product A', 'price': 10.99}, ...]
        """
        pass
