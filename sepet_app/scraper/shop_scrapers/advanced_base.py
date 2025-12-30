import os
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from loguru import logger
from .core import ScraperCore

class AdvancedBaseScraper(ScraperCore, ABC):
    """
    Abstract Base Class for advanced shop scraper that require more
    sophisticated techniques to bypass anti-scraping mechanisms.
    """

    def __init__(self, shop_id: int, shop_name: str, base_url: str, ignore_nonfood: bool = False):
        """
        Initializes the AdvancedBaseScraper for pages which need an unlocker API.
        """
        super().__init__()
        self.proxy = os.getenv('CUSTOM_PROXY')
        if self.proxy is not None:
            self.shop_id = shop_id
            self.shop_name = shop_name
            self.base_url = base_url
            self.ignore_nonfood = ignore_nonfood
            logger.info(f"Initialized AdvancedBaseScraper for {self.shop_name} with shop_id: {self.shop_id}")
        else:
            logger.error(f"Could not initialized AdvancedBaseScraper for {self.shop_name} because environment variable CUSTOM_PROXY is None")

    def __del__(self):
        """
        Destructor to clean up resources, like closing a browser instance.
        """
        logger.warning(f"Destructor of advanced base class called for {self.shop_name}")

    @abstractmethod
    def search(self, product: dict) -> List[dict]:
        """
        Searches for products based on a query string.

        This method MUST be implemented by any class that inherits from AdvancedBaseScraper.

        Args:
            product (dict): The food product from food.json.

        Returns:
            A list of dictionaries, where each dictionary represents a found product.
            Example: [{'id': '123', 'name': 'Product A', 'price': 10.99}, ...]
        """
        pass
