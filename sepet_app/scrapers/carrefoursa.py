import bs4
import urllib.request
import urllib.parse
import ssl
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper
from datetime import datetime
from loguru import logger
from dataclasses import asdict

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class CarrefoursaScraper(BaseScraper):
    """A scrapers for the Carrefoursa online shop."""
    def __init__(self, shop_name: str, base_url: str, driver_name: str, ignore_nonfood=False):
        """
        Initializes the CarrefoursaScraper.

        Args:
            shop_name (str): The name of the shop (should be 'Carrefoursa').
            base_url (str): The base URL for the Carrefoursa website.
            driver_name (str): The name of the driver to use.
            ignore_nonfood (bool): Whether to ignore non-food products.
        """
        super().__init__(shop_name=shop_name, base_url=base_url, driver_name=driver_name, ignore_nonfood=ignore_nonfood)
        # We put page=10 as Carrefoursa loads all available products --> no infinite scroll needed to load all products
        self.search_string = "/search?q=%s:relevance&page=1"
        self.search_url = f"{self.base_url}{self.search_string}"
        logger.info(f"Scraper for '{self.shop_name}' initialized.")


    def search(self, product: str, category_id: int):
        """
        Scrapes the Carrefoursa website for a given product.

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
        scraped_data = []

        # For Carrefoursa blank spaces in product names must be replaced by plus symbol (+)
        search_url = self.search_url % urllib.parse.quote(product.replace(' ', '+'))

        # Load the page
        self.driver.get(search_url)

        try:
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'product-listing-item')))
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            articles = soup.find_all("div", {"class": "product-card"})
            logger.info(f"Found {len(articles)} {product} articles.")

            for article in articles:
                if article.find_all("div",{"class": "advice"}):
                    logger.info(f"Skipping advice element")
                else:
                    display_name = article.find_all("h3", {"class": "item-name"})[0].text.strip()
                    if not self.ignore_nonfood or self.predict(text=display_name):
                        product_info = self.ScrapedProductInfo(
                            Scrape_Timestamp=datetime.now().isoformat(),
                            Display_Name=display_name,
                            Shop=self.shop_name,
                            category_id=category_id,
                            Search_Term=product,
                            Discount_Price=self.get_prices(article.find_all("div",{"class": "item-price-contain"})[0])[0],
                            Price=self.get_prices(article.find_all("div",{"class": "item-price-contain"})[0])[1],
                            URL=self.base_url + article.find_all("a",{"class": "product-return"})[0].attrs['href'],
                            product_id=article.find_all("h3",{"class": "item-name"})[0].attrs['content']
                        )
                        product_info = asdict(product_info)
                        scraped_data.append(product_info)
                        logger.info(f"Article {product_info['Display_Name']} scraped successfully.")
                    else:
                        logger.warning(f"Non-Food product scraped but skipped: {display_name}")
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
                                         <span class="price-cont" content="TRY" itemprop="priceCurrency">
                                            <div class="item-price-contain">
                                               <span class="hidden" content="InStock" itemprop="availability">InStock</span>
                                               <span class="priceLineThrough js-variant-price">899,<span class="formatted-price">90 TL</span>
                                            </span>
                                                <span class="item-price js-variant-discounted-price  " content="849.9" itemprop="price">849,<span class="formatted-price">90 TL</span>
                                            </span>
                                            </div>
                                            <p class="item-price-unit"></p>
                                        </span>

        Returns:
            tuple[float, float]: A tuple containing the original price and the
                                 discount price. Returns (0.0, 0.0) if no
                                 prices are found.
        """
        regular_price = 0.0

        # In the HTML, the item-price span is always available independent of the regular price
        # If item-price span is available alone, then it is the regular price. Otherwise, it is the discount price
        discount_price = price_tag.find_all("span", {"class": "item-price"})[0].attrs['content']
        discount_price = float(discount_price)
        regular_price = discount_price

        # Regular price is only available if there is really a discount on the article
        if price_tag.find_all("span", {"class": "priceLineThrough"}):
            regular_price = price_tag.find_all("span", {"class": "priceLineThrough"})[0].text
            regular_price = regular_price.replace("TL", "").strip()
            regular_price = regular_price.replace('.', '')
            regular_price = float(regular_price.replace(',', '.'))

        return discount_price, regular_price
