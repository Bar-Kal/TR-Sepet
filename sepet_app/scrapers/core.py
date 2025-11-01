import datetime
import re
import pickle
import numpy as np
from dataclasses import dataclass
from gensim.models import FastText
from loguru import logger

def get_document_vector(doc_tokens, model):
    valid_tokens = [word for word in doc_tokens if word in model.wv]
    if not valid_tokens:
        return np.zeros(model.vector_size)
    vectors = [model.wv[word] for word in valid_tokens]
    return np.mean(vectors, axis=0)

class ScraperCore:
    """
    A core class providing common functionalities for scrapers,
    such as product classification.
    """

    def __init__(self):
        """
        Initializes the ScraperCore by loading the machine learning models.
        """
        try:
            # Load the models
            self.ft_model = FastText.load("sepet_app/fasttext/trained_model/fasttext_model.bin")
            with open("sepet_app/fasttext/trained_model/classifier_model.pkl", "rb") as f:
                self.classifier = pickle.load(f)
            logger.info("Successfully loaded FastText and classifier models.")
        except Exception as e:
            logger.error(f"An error occurred while loading the ML models: {e}")

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
        Predicts if an article is a food or non-food product.

        Args:
            text (str): The text to classify.

        Returns:
            bool: True if the article is predicted to be food, False otherwise.
        """
        try:
            # Create a document vector for the input text
            text = text.lower()
            processed_text = re.sub(r'[^a-z\s]', '', text)
            vector = get_document_vector(processed_text, self.ft_model).reshape(1, -1)

            # Predict the category
            prediction = self.classifier.predict_proba(vector)
            return True if prediction[0][1] > 0.8 else False

        except Exception as e:
            logger.error(f"An error occurred during prediction: {e}")
            return False
