import bs4
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper
from datetime import datetime
from loguru import logger
from dataclasses import asdict

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class KoopScraper(BaseScraper):
    """A scraper for the Koop online shop."""
    def __init__(self, shop_name: str, base_url: str, driver_name: str, ignore_nonfood=False):
        """
        Initializes the KoopScraper.

        Args:
            shop_name (str): The name of the shop (should be 'Koop').
            base_url (str): The base URL for the Koop website.
            driver_name (str): The name of the driver to use.
            ignore_nonfood (bool): Whether to ignore non-food products.
        """
        super().__init__(shop_name=shop_name, base_url=base_url, driver_name=driver_name, ignore_nonfood=ignore_nonfood)
        # We put page=10 as Koop loads all available products --> no infinite scroll needed to load all products
        self.search_string = "/arama?ara=%s&page="
        self.search_url = f"{self.base_url}{self.search_string}"
        logger.info(f"Scraper for '{self.shop_name}' initialized.")


    def search(self, product: str, category_id: int):
        """
        Scrapes the Koop website for a given product.

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
        page_num = 1

        try:
            search_url = self.search_url + str(page_num)
            search_url = search_url % urllib.parse.quote(product)
            # Load the page
            self.driver.get(search_url)
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'ss_urun_area')))
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            no_products_found = soup.find("div", {"class": "ss_urun_yok"})

            if no_products_found is None:

                # At the end of the page, the number of max pages is available --> fetch it
                find_num_pages = soup.find_all("div", {"class": "ss_urun_area"})

                for content in find_num_pages[0].contents:
                    if "Toplam Sayfa" in content.text.strip():
                        page_num_max = int(content.contents[4].text)

                for page_num in range (1,page_num_max + 1):
                    articles = soup.find_all("div", {"class": "ss_urun"})
                    logger.info(f"Found {len(articles)} {product} articles on page {page_num}.")
                    for article in articles:
                        url = article.find("a").attrs["href"].strip()
                        # Fetching display name from url because long names are in html not written out and contain '...' at the end
                        display_name = url.split('/')[-1].replace('-', ' ').replace('_', ' ')
                        #display_name = article.find("div", {"class": "ss_urun3"}).text.strip()
                        product_info = self.ScrapedProductInfo(
                            Scrape_Timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            Display_Name=display_name,
                            Shop=self.shop_name,
                            category_id=category_id,
                            Search_Term=product,
                            Discount_Price=self.get_prices(article.find("div", {"class": "ss_urun52"}))[0],
                            Price=self.get_prices(article.find("div", {"class": "ss_urun52"}))[1],
                            URL=url,
                            product_id=url.split('/')[-1]
                        )
                        product_info = asdict(product_info)
                        scraped_data.append(product_info)
                        logger.info(f"Article {product_info['Display_Name']} scraped successfully.")

                return scraped_data

            else:
                logger.warning(f"No articles for {product} found.")

        except Exception as e:
            logger.error(f"An error occurred: {e}")
            return None

    @staticmethod
    def get_prices(price_tag: bs4.element.Tag) -> tuple[float, float]:
        """
        Extracts and returns the discount and original prices from an article's text.

        Args:
            price_tag (string): The price tag which has the original and discount prices.
                                         price_tag example:
                                         <div class="ss_urun52"><div>900,<span>00</span><div style="    width: 30px;
                                            float: right;
                                            font-size: 22px;
                                            padding-top: 0px;
                                            left: -10px;
                                            display: block;
                                            MARGIN-LEFT: 0PX;">TL</div></div></div>

        Returns:
            tuple[float, float]: A tuple containing the original price and the
                                 discount price. Returns (0.0, 0.0) if no
                                 prices are found.
        """
        regular_price = 0.0

        try:
            # In the HTML, the item-price span is always available independent of the regular price
            # If item-price span is available alone, then it is the regular price. Otherwise, it is the discount price
            discount_price = price_tag.text.strip()
            discount_price = discount_price.replace("TL", "")
            discount_price = discount_price.replace('.', '')
            discount_price = round(float(discount_price.replace(',', '.')), 2)
            regular_price = discount_price

            return discount_price, regular_price

        except Exception as e:
            logger.error(f"An error occurred while fetching the prices." + str(e))
            return 0.0, 0.0
