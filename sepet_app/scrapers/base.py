import datetime
import re
import pickle
import shutil
from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import List, Dict
import numpy as np
from gensim.models import FastText
from loguru import logger
from selenium import webdriver

from selenium.webdriver import Remote, ChromeOptions as Options
from selenium.webdriver.chromium.remote_connection import ChromiumRemoteConnection as Connection


def get_document_vector(doc_tokens, model):
    valid_tokens = [word for word in doc_tokens if word in model.wv]
    if not valid_tokens:
        return np.zeros(model.vector_size)
    vectors = [model.wv[word] for word in valid_tokens]
    return np.mean(vectors, axis=0)

class BaseScraper(ABC):
    """
    Abstract Base Class for all shop scrapers.
    It defines the common interface (the "contract") that every
    concrete scraper must implement.
    """

    def __init__(self, shop_name: str, base_url: str):
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
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-browser-side-navigation')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('enable-automation')
        # Tell ChromeDriver to only log fatal errors.
        # Log level 3 is the most severe, effectively silencing most messages.
        options.add_argument('--log-level=3')

        try:
            # instantiate chromedriver
            # For ARM. Found at: https://stackoverflow.com/questions/76857893/is-there-a-known-working-configuration-for-using-selenium-on-linux-arm64
            chromedriver_path = shutil.which("chromedriver")
            service = webdriver.ChromeService(executable_path=chromedriver_path)
            driver = webdriver.Chrome(options=options, service=service)
            logger.info(
                f"Using chromedriver version {driver.capabilities['browserVersion']} located at {chromedriver_path}.")

            self.options = options
            self.shop_name = shop_name
            self.base_url = base_url
            self.driver = driver
        except Exception as e:
            logger.error("Could not instantiate chromedriver." + str(e))

        try:
            # Load the models
            self.ft_model = FastText.load("sepet_app/fasttext/trained_model/fasttext_model.bin")
            with open("sepet_app/fasttext/trained_model/classifier_model.pkl", "rb") as f:
                self.classifier = pickle.load(f)
        except Exception as e:
            logger.error(f"An error occurred during prediction: {e}")

    def __del__(self):
        self.driver.quit()
        logger.warning(f"Destructor of base class called for {self.shop_name}")

    @dataclass
    class ScrapedProductInfo:
        """A class for holding scraped product information"""

        Scrape_Timestamp: datetime
        Display_Name: str
        Shop: str
        category_id: int
        Search_Term: str
        Price: float
        Discount_Price: float
        URL: str
        product_id: str

    def predict(self, text: str) -> bool:
        """
        Predicts if an article is food or non-food product . This is used to filter out unneeded products.

        Args:
            text (str): The text to classify.

        Returns:
            bool: Is article food or non-food.
        """
        try:
            # Create a document vector for the input text
            text = text.lower()
            processed_text = re.sub(r'[^a-z\s]', '', text)
            vector = get_document_vector(processed_text, self.ft_model).reshape(1, -1)

            # Predict the category
            prediction = self.classifier.predict_proba(vector)
            #logger.info(f"Predicted category for {text}: {prediction[0]}")
            return True if prediction[0][1] > 0.8 else False

        except Exception as e:
            logger.error(f"An error occurred during prediction: {e}")
            return False

    @abstractmethod
    def search(self, product: str, category_id: int) -> List[Dict]:
        """
        Searches for products based on a query string.

        This method MUST be implemented by any class that inherits from BaseScraper.

        Args:
            product (str): The search term (e.g., 'Sucuk', 'Pirinc').
            category_id (int): The category id of a product (e.g. 21 for 'Meyve').

        Returns:
            A list of dictionaries, where each dictionary represents a found product.
            Example: [{'id': '123', 'name': 'Product A', 'price': 10.99}, ...]
        """
        pass
