from .simple_base import SimpleBaseScraper
import re
import time
from datetime import datetime
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dataclasses import asdict
from loguru import logger

class A101Scraper(SimpleBaseScraper):
    """A scrapers for the A101 online shop."""
    def __init__(self, shop_name: str, base_url: str):
        """
        Initializes the A101Scraper.

        Args:
            shop_name (str): The name of the shop (should be 'A101').
            base_url (str): The base URL for the A101 website.
        """
        super().__init__(shop_name=shop_name, base_url=base_url)
        self.search_string = "/arama?k=%s&kurumsal=1"
        self.search_url = f"{self.base_url}{self.search_string}"
        logger.info(f"Scraper for '{self.shop_name}' initialized.")


    def search(self, product: str, category_id: int):
        """
        Scrapes the A101 website for a given product.

        This method navigates to the search results page for the specified
        product, scrolls down to load all results, and then parses the page
        to extract product information.

        Args:
            product (str): The product to search for.
            category_id (int): The category id of the product (e.g. 21 for 'Meyve').

        Returns:
            list: A list of dictionaries, each containing information about a
                  scraped product. Returns None if an error occurs.
        """
        search_url = self.search_string % product
        scraped_data = []

        # Load the page
        self.driver.get(search_url)
        try:
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'article')))
            # This loop scrolls down the page until no new products are loaded.
            last_article_count = 0
            while True:
                # Get the current number of product articles on the page
                current_articles = self.driver.find_elements(By.TAG_NAME, 'article')
                article_count = len(current_articles)
                # If the count hasn't changed after a scroll and wait, we've reached the bottom
                if article_count == last_article_count:
                    logger.info(f"Reached the end of the page. Total products found: {article_count}")
                    break
                logger.info(f"Loaded {article_count} {product} products, scrolling for more...")
                last_article_count = article_count
                # Execute JavaScript to scroll to the bottom of the page
                # Large footer causing that auto-scrolling is not working. Solution was to set scrollHeight - 1000
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight - 1000);")
                # Wait for a moment to allow new products to load
                time.sleep(2)  # This pause is crucial for the dynamic content
            # Now that the page is fully loaded, get the complete page source
            # Get the page source and parse it with BeautifulSoup
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            articles = soup.find_all('article')
            if articles:
                for art in articles:
                    if self.base_url in art.contents[0].attrs['href']:
                        if self.predict(text=str(art.contents[0].attrs['title'])):
                            product_info = self.ScrapedProductInfo(
                                Scrape_Timestamp=datetime.now().isoformat(),
                                Display_Name=art.contents[0].attrs['title'],
                                Shop=self.shop_name,
                                category_id=category_id,
                                Search_Term=product,
                                Discount_Price=self.get_prices(art.text)[0],
                                Price=self.get_prices(art.text)[1],
                                URL=art.contents[0].attrs['href'],
                                product_id=art.contents[0].attrs['href'].split("p-")[-1]
                            )
                            product_info = asdict(product_info)
                            scraped_data.append(product_info)
                            logger.info(f"Article {product_info['Display_Name']} scraped successfully.")
                        else:
                            logger.warning(f"Non-Food product scraped but skipped: {str(art.contents[0].attrs['title'])}")

                return scraped_data
        except Exception as e:
            logger.error(f"An error occurred: {e}")
        return None

    @staticmethod
    def get_prices(article_text: str) -> tuple[float, float]:
        """
        Extracts and returns the discount and original prices from an article's text.

        This method uses a regular expression to find all prices (indicated by '₺')
        in the given text, converts them to floats, and returns the lowest and
        highest prices found.

        Args:
            article_text (str): The text of the product article.

        Returns:
            tuple[float, float]: A tuple containing the discount price and the
                                 original price. Returns (0.0, 0.0) if no
                                 prices are found.
        """
        # Find all occurrences of the price pattern (e.g., ₺12,34 or ₺1.234,56)
        prices = re.findall(r'₺\s*([\d.,]+)', article_text)
        if len(prices) > 0:
            prices = [price.replace('.', '') for price in prices]
            prices = [price.replace(',', '.') for price in prices]
            prices = [float(i) for i in prices]
            prices.sort()
            return prices[0], prices[-1] # Lowest is discount, highest is original

        return 0.0, 0.0



