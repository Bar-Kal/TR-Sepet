import json
import re
import time
from abc import ABC, abstractmethod
from datetime import datetime
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class Scraper(ABC):
    def __init__(self, base_url):
        self.base_url = base_url

    @abstractmethod
    def search(self, product):
        pass

class A101Scraper(Scraper):
    def __init__(self):
        super().__init__("https://www.a101.com.tr")

        # Set up the WebDriver
        user_agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.50 Safari/537.36'
        options = webdriver.ChromeOptions()
        options.add_argument(f'user-agent={user_agent}')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--headless')
        options.add_argument('--disable-plugins-discovery')
        options.add_argument('--disable-web-security')
        options.add_argument('--allow-running-insecure-content')
        options.add_argument('--start-maximized')

        self.shop_name = 'A101'
        self.options = options

    def search(self, product):
        search_url = f"{self.base_url}/arama?k={product}&kurumsal=1"
        scraped_data = []

        with webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=self.options) as driver:
            # Load the page
            driver.get(search_url)
            try:
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'article')))
                last_height = driver.execute_script("return document.body.scrollHeight")
                # --- START: New Scrolling Logic ---
                # This loop scrolls down the page until no new products are loaded.
                last_article_count = 0
                while True:
                    # Get the current number of product articles on the page
                    current_articles = driver.find_elements(By.TAG_NAME, 'article')
                    article_count = len(current_articles)

                    # If the count hasn't changed after a scroll and wait, we've reached the bottom
                    if article_count == last_article_count:
                        print(f"Reached the end of the page. Total products found: {article_count}")
                        break

                    print(f"Loaded {article_count} {product} products, scrolling for more...")
                    last_article_count = article_count

                    # Execute JavaScript to scroll to the bottom of the page
                    # Large footer causing that auto-scrolling is not working. Solution was to set scrollHeight - 1000
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight - 1000);")

                    # Wait for a moment to allow new products to load
                    time.sleep(2)  # This pause is crucial for the dynamic content
                # --- END: New Scrolling Logic ---

                # Now that the page is fully loaded, get the complete page source
                # Get the page source and parse it with BeautifulSoup
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                articles = soup.find_all('article')
                if articles:
                    for art in articles:
                        product_info = {}
                        product_info['Scrape_Timestamp'] = datetime.now().isoformat()
                        product_info['Display_Name'] = art.contents[0].attrs['title']
                        product_info['Shop'] = self.shop_name
                        product_info['Search_Term'] = product
                        product_info['Discount_Price'], product_info['Price'] = self.get_prices(art.text)
                        product_info['URL'] = art.contents[0].attrs['href']
                        product_info['id'] = product_info['URL'].split("p-")[-1]

                        scraped_data.append(product_info)

                    return scraped_data
            except Exception as e:
                print(f"An error occurred: {e}")
        return None

    def get_prices(self, article_text: str) -> tuple[float, float]:
        """
        Extracts all prices from a string, converts them to float, and sorts them.
        The price is indicated by '₺'. It can appear anywhere in the string.
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
