import time
import bs4
from bs4 import BeautifulSoup
from .base import BaseScraper
from datetime import datetime
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
            WebDriverWait(self.driver, 15).until(EC.presence_of_element_located((By.ID, "ProductPageProductList")))
            while True:
                page_source = self.driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')
                articles = soup.find_all("div", {"class": "productItem"})
                logger.info(f"Found {len(articles)} {product} articles on page {page_num}.")

                if articles:
                    for article in articles:
                        product_info = self.ScrapedProductInfo(
                            Scrape_Timestamp=datetime.now().isoformat(),
                            Display_Name=article.find_all("div",{"class": "productName"})[0].text,
                            Shop=self.shop_name,
                            category_id=category_id,
                            Search_Term=product,
                            Discount_Price=self.get_prices(article.find_all("div",{"class": "productPrice"})[0])[0],
                            Price=self.get_prices(article.find_all("div",{"class": "productPrice"})[0])[1],
                            URL=self.base_url + article.find_all("a",{"class": "detailUrl"})[0].attrs['href'],
                            product_id=article.find_all("a",{"class": "detailUrl"})[0].attrs['data-id']
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
                                         <div class="discountPrice">
                                        <span class="discountPriceSpan">₺108,00</span>
                                        <span class="discountKdv">KDV Dahil</span>
                                        </div>
                                        <div class="regularPrice">
                                        <span class="regularPriceSpan">₺180,00</span>

        Returns:
            tuple[float, float]: A tuple containing the original price and the
                                 discount price. Returns (0.0, 0.0) if no
                                 prices are found.
        """
        regular_price = 0.0

        # In the HTML, the discountPriceSpan is always available independent of the regular price
        # If discountPriceSpan is available alon, then it is the regular price
        discount_price = price_tag.find_all("span", {"class": "discountPriceSpan"})[0]
        discount_price = discount_price.text.strip().replace('₺', '')
        discount_price = discount_price.replace('.', '')
        discount_price = float(discount_price.replace(',', '.'))

        regular_price = discount_price

        # Regular price is only available if there is really a discount on the article
        if price_tag.find_all("span",{"class": "regularPriceSpan"}):
            regular_price = price_tag.find_all("span",{"class": "regularPriceSpan"})[0]
            regular_price = regular_price.text.strip().replace('₺', '')
            regular_price = regular_price.replace('.', '')
            regular_price = float(regular_price.replace(',', '.'))

        return discount_price, regular_price
