import bs4
import urllib.request
import urllib.parse
import ssl
from bs4 import BeautifulSoup
from sepet_app.scraper.src.core.advanced_base import AdvancedBaseScraper
from datetime import datetime
from loguru import logger
from dataclasses import asdict

class OnurmarketScraper(AdvancedBaseScraper):
    """A scraper for the Onurmarket online shop."""
    def __init__(self, shop_id: int, shop_name: str, base_url: str, ignore_nonfood=False):
        """
        Initializes the OnurmarketScraper.

        Args:
            shop_id (int): The ID of the shop.
            shop_name (str): The name of the shop (should be 'Onurmarket').
            base_url (str): The base URL for the Onurmarket website.
            ignore_nonfood (bool): Whether to ignore non-food products.
        """
        super().__init__(shop_id=shop_id, shop_name=shop_name, base_url=base_url, ignore_nonfood=ignore_nonfood)
        self.search_string = "/Arama?1&kelime="
        self.search_url = f"{self.base_url}{self.search_string}%s"
        logger.info(f"Scraper for '{self.shop_name}' initialized.")


    def search(self, product: dict):
        """
        Scrapes the Onurmarket website for a given product.

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

        search_url = self.search_url % urllib.parse.quote(product_name)
        scraped_data = []

        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({'https': self.proxy, 'http': self.proxy}),
            urllib.request.HTTPSHandler(context=ssl._create_unverified_context())
        )

        try:
            page_source = opener.open(search_url).read().decode()
            soup = BeautifulSoup(page_source, 'html.parser')
            articles = soup.find_all("div", {"class": "productItem"})
            logger.info(f"Found {len(articles)} {product_name} articles.")

            for article in articles:
                display_name = article.find_all("div",{"class": "productName"})[0].text.strip()
                product_info = self.ScrapedProductInfo(
                    Scrape_Timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    Display_Name=display_name,
                    Shop_ID=self.shop_id,
                    Category_ID=product['category_id'],
                    Product_ID=product['product_id'],
                    Discount_Price=self.get_prices(article.find_all("div",{"class": "productPrice"})[0])[0],
                    Price=self.get_prices(article.find_all("div",{"class": "productPrice"})[0])[1],
                    URL=article.find_all("a",{"class": "detailUrl"})[0].attrs['href'],
                    Scraped_Product_ID=article.find_all("a",{"class": "detailUrl"})[0].attrs['data-id']
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

        try:
            # In the HTML, the discountPriceSpan is always available independent of the regular price
            # If discountPriceSpan is available alone, then it is the regular price
            discount_price = price_tag.find_all("span", {"class": "discountPriceSpan"})[0]
            discount_price = discount_price.text.strip().replace('₺', '')
            discount_price = discount_price.replace('.', '')
            discount_price = round(float(discount_price.replace(',', '.')), 2)

            regular_price = discount_price

            # Regular price is only available if there is really a discount on the article
            if price_tag.find_all("span",{"class": "regularPriceSpan"}):
                regular_price = price_tag.find_all("span",{"class": "regularPriceSpan"})[0]
                regular_price = regular_price.text.strip().replace('₺', '')
                regular_price = regular_price.replace('.', '')
                regular_price = round(float(regular_price.replace(',', '.')), 2)

            return discount_price, regular_price

        except Exception as e:
            logger.error(f"An error occurred while fetching the prices." + str(e))
            return 0.0, 0.0