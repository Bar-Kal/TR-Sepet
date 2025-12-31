import bs4
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper
from datetime import datetime
from typing import Any
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from loguru import logger
from dataclasses import asdict

class CagriScraper(BaseScraper):
    """A scraper for the Cagri online shop."""
    def __init__(self, shop_id: int, shop_name: str, base_url: str, driver_name: str, ignore_nonfood=False):
        """
        Initializes the CarrefourScraper.

        Args:
            shop_id (int): The ID of the shop.
            shop_name (str): The name of the shop (should be 'Cagri').
            base_url (str): The base URL for the Cagri website.
            driver_name (str): The name of the driver to use.
            ignore_nonfood (bool):
        """
        super().__init__(shop_id=shop_id, shop_name=shop_name, base_url=base_url, driver_name=driver_name, ignore_nonfood=ignore_nonfood)
        self.search_string = "/arama?isim="
        self.search_url = f"{self.base_url}{self.search_string}%s"
        logger.info(f"Scraper for '{self.shop_name}' initialized.")


    def search(self, product: dict):
        """
        Scrapes the Cagri website for a given product.

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
            WebDriverWait(self.driver, 15).until(EC.presence_of_element_located((By.CLASS_NAME, "product-card")))
            while True:
                page_source = self.driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')
                articles = soup.find_all("div", {"class": "product-card"})
                logger.info(f"Found {len(articles)} {product_name} articles.")

                for article in articles:
                    display_name = article.find("a",{"class": "text-slate-700"}).text
                    product_info = self.ScrapedProductInfo(
                        Scrape_Timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        Display_Name=display_name,
                        Shop_ID=self.shop_id,
                        Category_ID=product['category_id'],
                        Product_ID=product['product_id'],
                        Discount_Price=self.get_prices(article.find("div",{"class": "flex items-center gap-1"}))[0],
                        Price=self.get_prices(article.find("div",{"class": "flex items-center gap-1"}))[1],
                        URL=article.find("a",{"class": "mt-2 md:mt-4"}).attrs['href'].split('?')[0],
                        Scraped_Product_ID=article.find("a",{"class": "mt-2 md:mt-4"}).attrs['href'].replace('/', '').split('?')[0] # product id not found -> take url instead
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
            price_tag (bs4.element.Tag): The price tag which has the original and discount prices.
                                         price_tag example:
                                         <div class="flex items-center gap-1">
                                         <p class="text-slate-700 dark:text-slate-300 font-sans text-xl sm:text-lg lg:text-xl max-xxs:text-base font-semibold p-0 m-0 text-left whitespace-nowrap">110,96 TL</p>
                                         <p class="dark:text-slate-300 font-sans text-sm sm:text-base lg:text-sm max-xxs:text-xs font-medium p-0 m-0 text-left text-zinc-500 line-through">147,95TL</p>
                                         </div>

        Returns:
            tuple[float, float]: A tuple containing the original price and the
                                 discount price. Returns (0.0, 0.0) if no
                                 prices are found.
        """
        regular_price = 0.0

        try:
            # If there is a discount, the discounted price is in place of the regular price tag
            # If a single price is available, then it is the regular price
            discount_price = str(price_tag.next.contents[0])
            discount_price = discount_price.replace("TL", "").strip()
            discount_price = discount_price.replace('.', '')
            discount_price = round(float(discount_price.replace(',', '.')), 2)
            regular_price = discount_price

            # Regular price is only available if there is really a discount on the article
            if price_tag.next.nextSibling is not None:
                regular_price = price_tag.next.nextSibling.next
                regular_price = regular_price.replace("TL", "").strip()
                regular_price = regular_price.replace('.', '')
                regular_price = round(float(regular_price.replace(',', '.')), 2)

            return discount_price, regular_price

        except Exception as e:
            logger.error(f"An error occurred while fetching the prices." + str(e))
            return 0.0, 0.0
