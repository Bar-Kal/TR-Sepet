from .base import BaseScraper
import time
from datetime import datetime
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from loguru import logger
from dataclasses import asdict

class OnurmarketScraper(BaseScraper):
    """A scrapers for the Onurmarket online shop."""
    def __init__(self, shop_name, base_url):
        """
        Initializes the CarrefourScraper.

        Args:
            shop_name (str): The name of the shop (should be 'Onurmarket').
            base_url (str): The base URL for the Onurmarket website.
        """
        super().__init__(shop_name=shop_name, base_url=base_url)
        logger.info(f"Scraper for '{self.shop_name}' initialized.")


    def search(self, product: str, category_id: int):
        """
        Scrapes the Onurmarket website for a given product.

        This method navigates to the search results page for the specified
        product, clicks through the pages, and then parses the page
        to extract product information.

        Args:
            product (str): The product to search for.
            category_id (int): The category id of the product (e.g. 21 for 'Meyve').

        Returns:
            list: A list of dictionaries, each containing information about a
                  scraped product. Returns None if an error occurs.
        """
        logger.info(f"Starting to scrape product {product} in {self.shop_name}.")

        search_url = f"{self.base_url}/Arama?1&kelime={product}"
        scraped_data = []
        page_num = 1
        print(search_url)
        # Load the page
        self.driver.get(search_url)
        try:
            WebDriverWait(self.driver, 15)#.until(EC.presence_of_element_located((By.ID, "ProductPageProductList")))
            while True:
                page_source = self.driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')
                articles = soup.find_all("div", {"class": "productItem"})
                logger.info(f"Found {len(articles)} {product} articles on page {page_num}.")

                for article in articles:
                    dummy = article.find(id='product-name')

                return scraped_data
        except Exception as e:
            logger.error(f"An error occurred: {e}")
            return None

    @staticmethod
    def get_prices(product_price_element: str) -> tuple[float, float]:
        """
        Extracts and returns the discount and original prices from an article's text.

        Args:
            product_price_element (str): The text of the product article.

        Returns:
            tuple[float, float]: A tuple containing the original price and the
                                 discount price. Returns (0.0, 0.0) if no
                                 prices are found.
        """

        return 0.0, 0.0
