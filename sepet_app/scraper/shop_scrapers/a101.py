import time
import bs4
from .base_scraper import BaseScraper
from datetime import datetime
from typing import Any
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dataclasses import asdict
from loguru import logger

class A101Scraper(BaseScraper):
    """A scraper for the A101 online shop."""
    def __init__(self, shop_id: int, shop_name: str, base_url: str, driver_name: str, ignore_nonfood=False):
        """
        Initializes the A101Scraper.

        Args:
            shop_id (int): The ID of the shop.
            shop_name (str): The name of the shop (should be 'A101').
            base_url (str): The base URL for the A101 website.
            driver_name (str): The name of the driver to use.
            ignore_nonfood (bool): Whether to ignore non-food products.
        """
        super().__init__(shop_id=shop_id, shop_name=shop_name, base_url=base_url, driver_name=driver_name, ignore_nonfood=ignore_nonfood)
        self.search_string = "/arama?k=%s&kurumsal=1"
        self.search_url = f"{self.base_url}{self.search_string}"
        logger.info(f"Scraper for '{self.shop_name}' initialized.")


    def search(self, product: dict):
        """
        Scrapes the A101 website for a given product.

        This method navigates to the search results page for the specified
        product, scrolls down to load all results, and then parses the page
        to extract product information.

        Args:
            product (Any): The food product from food.json.

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
                logger.info(f"Loaded {article_count} {product_name} products, scrolling for more...")
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
                for article in articles:
                    if self.base_url in article.contents[0].attrs['href']:
                        display_name = article.contents[0].attrs['title']
                        url = article.contents[0].attrs['href']
                        product_info = self.ScrapedProductInfo(
                            Scrape_Timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            Display_Name=display_name,
                            Shop_ID=self.shop_id,
                            Category_ID=product['category_id'],
                            Product_ID=product['product_id'],
                            Discount_Price=self.get_prices(article.find_all("section", {"class": "mt-2.5 h-full flex flex-col justify-end mb-3"})[0])[0],
                            Price=self.get_prices(article.find_all("section", {"class": "mt-2.5 h-full flex flex-col justify-end mb-3"})[0])[1],
                            URL=url.replace(self.base_url, ''),
                            Scraped_Product_ID=article.contents[0].attrs['href'].split("p-")[-1]
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

        This method uses a regular expression to find all prices (indicated by '₺')
        in the given text, converts them to floats, and returns the lowest and
        highest prices found.

        Args:
            price_tag (bs4.element.Tag): The price tag which has the original and discount prices.
                                         price_tag example:
                                         <section class="mt-2.5 h-full flex flex-col justify-end mb-3">
                                         <span class="text-xs text-[#333] h-[17px] line-through cursor-pointer" style="line-height: initial;"></span>
                                         <span class="text-base text-[#333]  not-italic font-medium leading-normal cursor-pointer">₺33,00</span>
                                         </section>

        Returns:
            tuple[float, float]: A tuple containing the discount price and the
                                 original price. Returns (0.0, 0.0) if no
                                 prices are found.

        """

        regular_price = 0.0

        try:
            # In the HTML, the section with class "mt-2.5 h-full flex flex-col justify-end mb-3" is always available for the prices.
            # The text of this class has the regular price IF the next element is empty. Otherwise, it is the discount price
            discount_price = price_tag.contents[1].text.strip().replace('₺', '')
            discount_price = discount_price.replace('.', '')
            discount_price = round(float(discount_price.replace(',', '.')), 2)
            regular_price = discount_price

            # A discount is available if the text of the next element is not empty.
            # Which means that the next element would be the regular price in such cases.
            if len(price_tag.next.contents) > 0:
                regular_price = price_tag.next.text.strip().replace('₺', '')
                regular_price = regular_price.replace('.', '')
                regular_price = round(float(regular_price.replace(',', '.')), 2)

            return discount_price, regular_price

        except Exception as e:
            logger.error(f"An error occurred while fetching the prices." + str(e))
            return 0.0, 0.0



