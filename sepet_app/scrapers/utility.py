import re
import pickle
from gensim.models import FastText
from loguru import logger
import numpy as np

def _get_document_vector(doc_tokens, model):
    valid_tokens = [word for word in doc_tokens if word in model.wv]
    if not valid_tokens:
        return np.zeros(model.vector_size)
    vectors = [model.wv[word] for word in valid_tokens]
    return np.mean(vectors, axis=0)

class ProductClassifier:
    """
    A utility class providing common functionalities for scrapers,
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
            vector = _get_document_vector(processed_text, self.ft_model).reshape(1, -1)

            # Predict the category
            prediction = self.classifier.predict_proba(vector)
            logger.info(f"Prediction: {prediction}")
            return True if prediction[0][1] > 0.7 else False

        except Exception as e:
            logger.error(f"An error occurred during prediction: {e}")
            return False
