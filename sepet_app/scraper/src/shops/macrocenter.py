import time
import bs4
from bs4 import BeautifulSoup
from sepet_app.scraper.src.core.base_scraper import BaseScraper
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from loguru import logger
from dataclasses import asdict

class MacrocenterScraper(BaseScraper):
    """A scraper for the Macrocenter online shop."""
    def __init__(self, shop_id: int, shop_name: str, base_url: str, driver_name: str, ignore_nonfood=False):
        """
        Initializes the MacrocenterScraper.

        Args:
            shop_id (int): The ID of the shop.
            shop_name (str): The name of the shop (should be 'Macrocenter').
            base_url (str): The base URL for the Macrocenter website.
            driver_name (str): The name of the driver to use.
            ignore_nonfood (bool):
        """
        super().__init__(shop_id=shop_id, shop_name=shop_name, base_url=base_url, driver_name=driver_name, ignore_nonfood=ignore_nonfood)
        self.search_string = "/arama?q="
        self.search_url = f"{self.base_url}{self.search_string}%s"
        logger.info(f"Scraper for '{self.shop_name}' initialized.")


    def search(self, product: dict):
        """
        Scrapes the Macrocenter website for a given product.

        This method navigates to the search results page for the specified
        product, clicks through the pages, and then parses the page
        to extract product information.

        Args:
            product (dict): The food product from food.json.

        Returns:
            list: A list of dictionaries, each containing information about a
                  scraped product. Returns None if an error occurs.
        """
        product_name = product['TurkishName']
        logger.info(f"Starting to scrape product {product_name} in {self.shop_name}.")
        search_url = self.search_url % product_name
        scraped_data = []

        # Load the page
        self.driver.get(search_url)

        try:
            WebDriverWait(self.driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "fe-product-list")))
            # This loop scrolls down the page until no new products are loaded.
            last_article_count = 0
            while True:
                # Get the current number of product articles on the page
                current_articles = self.driver.find_elements(By.TAG_NAME, 'fe-product-card')
                article_count = len(current_articles)
                # If the count hasn't changed after a scroll and wait, we've reached the bottom
                if article_count == last_article_count:
                    logger.info(f"Reached the end of the page. Total products found: {article_count}")
                    break
                logger.info(f"Loaded {article_count} {product_name} products, scrolling for more...")
                last_article_count = article_count
                # Execute JavaScript to scroll to the bottom of the page
                # Large footer causing that auto-scrolling is not working. Solution was to set scrollHeight - 1000
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight - 1000);")
                # Wait for a moment to allow new products to load
                time.sleep(2)  # This pause is crucial for the dynamic content

            # Now that the page is fully loaded, get the complete page source
            # Get the page source and parse it with BeautifulSoup
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            articles = soup.find_all("fe-product-card")
            logger.info(f"Found {len(articles)} {product_name} articles.")
            for article in articles:
                display_name = str(article.find("a",{"class": "text-decoration-ellipsis"}).text).strip()
                url = article.find("a",{"class": "text-decoration-ellipsis"}).attrs['href']
                product_info = self.ScrapedProductInfo(
                    Scrape_Timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    Display_Name=display_name,
                    Shop_ID=self.shop_id,
                    Category_ID=product['category_id'],
                    Product_ID=product['product_id'],
                    Discount_Price=self.get_prices(article)[0],
                    Price=self.get_prices(article)[1],
                    URL=url,
                    Scraped_Product_ID=url.split('-')[-1]
                )
                product_info = asdict(product_info)
                scraped_data.append(product_info)
                logger.info(f"Article {product_info['Display_Name']} scraped successfully.")
            return scraped_data
        except Exception as e:
            logger.error(f"An error occurred: {e}")
            return None

    @staticmethod
    def get_prices(price_tag: bs4.element.Tag) -> tuple[float, float]:
        """
        Extracts and returns the discount and original prices from an article's text.

        Args:
            price_tag (bs4.element.Tag): The price tag which is the complete product card: fe-product-card

        Returns:
            tuple[float, float]: A tuple containing the original price and the
                                 discount price. Returns (0.0, 0.0) if no
                                 prices are found.
        """
        regular_price = 0.0
        discount_price = 0.0

        try:
            # If there is a discount, the discounted price is in fe-money-discount-label tag
            # The regular price is always available in fe-product-price tag

            regular_price = price_tag.find("fe-product-price").text
            regular_price = regular_price.replace("TL", "").strip()
            regular_price = regular_price.replace('.', '')
            regular_price = round(float(regular_price.replace(',', '.')), 2)

            discount_price = regular_price

            # Discount price (Money ile) is only available if fe-money-discount-label is not None
            discount_tag = price_tag.find("fe-money-discount-label")
            if discount_tag is not None:
                discount_price = discount_tag.find("div", {"class": "price-content"}).text
                discount_price = discount_price.replace("TL", "").strip()
                discount_price = discount_price.replace('.', '')
                discount_price = round(float(discount_price.replace(',', '.')), 2)

            return discount_price, regular_price

        except Exception as e:
            logger.error(f"An error occurred while fetching the prices." + str(e))
            return 0.0, 0.0
