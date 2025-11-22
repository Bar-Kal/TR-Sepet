from .base_scraper import BaseScraper
import time
from datetime import datetime
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from loguru import logger
from dataclasses import asdict

class MigrosScraper(BaseScraper):
    """A scraper for the Migros online shop."""
    def __init__(self, shop_name: str, base_url: str, driver_name: str, ignore_nonfood=False):
        """
        Initializes the MigrosScraper.

        Args:
            shop_name (str): The name of the shop (should be 'Migros').
            base_url (str): The base URL for the Migros website.
            driver_name (str): The name of the driver to use.
            ignore_nonfood (bool): Whether to ignore non-food products.
        """
        super().__init__(shop_name=shop_name, base_url=base_url, driver_name=driver_name, ignore_nonfood=ignore_nonfood)
        self.search_string = "/arama?q="
        self.search_url = f"{self.base_url}{self.search_string}%s"
        logger.info(f"Scraper for '{self.shop_name}' initialized.")


    def search(self, product: str, category_id: int):
        """
        Scrapes the Migros website for a given product.

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
        search_url = self.search_url % product
        scraped_data = []
        page_num = 1

        # Load the page
        self.driver.get(search_url)
        try:
            WebDriverWait(self.driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, 'fe-product-price')))
            while True:
                page_source = self.driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')
                articles = soup.find_all('sm-product-list-content')
                articles = articles[0].find_all('mat-card')

                logger.info(f"Found {len(articles)} {product} articles on page {page_num}.")

                for article in articles:
                    product_name_element = article.find(id='product-name')
                    product_price_element = article.find("div", {"class": "price-container"})

                    product_info = self.ScrapedProductInfo(
                        Scrape_Timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        Display_Name=product_name_element.text.strip(),
                        Shop=self.shop_name,
                        category_id=category_id,
                        Search_Term=product,
                        Discount_Price=self.get_prices(product_price_element.text)[0],
                        Price=self.get_prices(product_price_element.text)[1],
                        URL=self.base_url + str(product_name_element.attrs['href']),
                        product_id=product_name_element.attrs['href'].split("p-")[-1]
                    )
                    product_info = asdict(product_info)
                    scraped_data.append(product_info)
                    logger.info(f"Article {product_info['Display_Name']} scraped successfully.")

                try:
                    next_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.ID, 'pagination-button-next'))
                    )
                    self.driver.execute_script("arguments[0].click();", next_button)
                    logger.info(f"Loading next page for product {product}.")
                    page_num += 1
                    time.sleep(2)  # Wait for page to load
                except Exception as e:
                    logger.info(f"No more pages to load for product {product}.")
                    break

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
        try:
            product_price_element = product_price_element.replace("İyi Fiyat", "") # Sometimes text 'İyi Fiyat' appears
            product_price_element = product_price_element.replace('.', '') # Get rid of thousands separators

            if "Money ile" in product_price_element: # There is a discount price in text
                # Example from webpage article with discount price ' 294,95 TLMoney ile219,95 TL'
                dummy_prices = product_price_element.replace("Money ile", "")
                dummy_prices = dummy_prices.replace("TL", "").strip().replace(",", ".")
                dummy_prices = dummy_prices.split(' ')
                price = float(dummy_prices[0])
                discount = float(dummy_prices[1])
                return discount, price

            # No discount price available for article
            price = float(product_price_element.replace("TL", "").strip().replace(",", "."))
            return price, price

        except Exception as e:
            logger.error(f"An error occurred while fetching the prices." + str(e))
            return 0.0, 0.0
