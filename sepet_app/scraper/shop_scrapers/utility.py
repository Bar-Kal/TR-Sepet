import pickle
from gensim.models import FastText
from loguru import logger
import numpy as np
import os
import glob
import pandas as pd
import re
from datetime import datetime

def sanitize_name(name, is_path=False):
    """Sanitizes a string to be a valid name."""
    if is_path:
        base_name = os.path.splitext(os.path.basename(name))[0]
        # Go up two levels to get the shop name from the path
        parent_dir = os.path.basename(os.path.dirname(os.path.dirname(name)))
        name = f"{parent_dir}_{base_name}"
    return re.sub(r'[^a-zA-Z0-9_]', '_', name)

def create_pickle_from_csvs():
    """
    Finds all combined.csv files, loads them into pandas DataFrames,
    and saves them as a pickled dictionary.
    """
    today_str = datetime.now().strftime('%Y-%m-%d')  # Get today's date in YYYY-MM-DD format
    downloads_folder = os.path.join('sepet_app', 'scraper', 'downloads')
    pickle_file = os.path.join(downloads_folder, 'sepet_data_' + today_str + '.pkl')

    if not os.path.isdir(downloads_folder):
        logger.error(f"Error: Downloads folder not found at '{downloads_folder}'")
        return

    csv_files = [f for f in glob.glob(os.path.join(downloads_folder, '**', 'combined.csv'), recursive=True) if 'imported' not in f]

    if not csv_files:
        logger.info("No CSV files found in the downloads directory.")
        # If no new CSVs, check if a pickle file already exists. If so, do nothing.
        if os.path.exists(pickle_file):
            logger.info("Pickle file already exists. No new data to process.")
            return
        # If no pickle file and no CSVs, create an empty pickle file.
        else:
            with open(pickle_file, 'wb') as f:
                pickle.dump({}, f)
            logger.info("No CSVs found and no existing pickle file. Created an empty pickle file.")
            return

    logger.info(f"Found {len(csv_files)} CSV files to process.")
    
    data = {}
    for file_path in csv_files:
        try:
            shop_name_raw = os.path.basename(os.path.dirname(os.path.dirname(file_path)))
            shop_name = sanitize_name(shop_name_raw)
            
            df = pd.read_csv(file_path, delimiter=';', encoding='utf-8', on_bad_lines='skip')
            
            # Sanitize column names
            df.columns = [sanitize_name(col) for col in df.columns]

            if shop_name in data:
                data[shop_name] = pd.concat([data[shop_name], df], ignore_index=True)
            else:
                data[shop_name] = df
            
            logger.info(f"  - Processed {file_path} for shop '{shop_name}'")

        except Exception as e:
            logger.error(f"  - ERROR: Failed to process {file_path}. Reason: {e}")

    if data:
        # If a pickle file already exists, load it and merge the new data.
        if os.path.exists(pickle_file):
            logger.info("Existing pickle file found. Merging new data.")
            with open(pickle_file, 'rb') as f:
                existing_data = pickle.load(f)
            
            for shop, df in data.items():
                if shop in existing_data:
                    existing_data[shop] = pd.concat([existing_data[shop], df], ignore_index=True).drop_duplicates().reset_index(drop=True)
                else:
                    existing_data[shop] = df
            data_to_save = existing_data
        else:
            data_to_save = data

        with open(pickle_file, 'wb') as f:
            pickle.dump(data_to_save, f)
        
        logger.info(f"Successfully created/updated pickle file: {pickle_file}")

def _get_document_vector(doc_tokens, model):
    valid_tokens = [word for word in doc_tokens if word in model.wv]
    if not valid_tokens:
        return np.zeros(model.vector_size)
    vectors = [model.wv[word] for word in valid_tokens]
    return np.mean(vectors, axis=0)

class ProductClassifier:
    """
    A utility class providing common functionalities for scraper,
    such as product classification.
    """

    def __init__(self):
        """
        Initializes the ScraperCore by loading the machine learning models.
        """
        try:
            # Load the models
            self.ft_model = FastText.load("sepet_app/models/trained_model/fasttext_model.bin")
            with open("sepet_app/models/trained_model/classifier_model.pkl", "rb") as f:
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
            vector = _get_document_vector(text, self.ft_model).reshape(1, -1)

            # Predict the category
            prediction = self.classifier.predict_proba(vector)
            logger.info(f"Prediction: {prediction}")
            return True if prediction[0][1] > 0.7 else False

        except Exception as e:
            logger.error(f"An error occurred during prediction: {e}")
            return False
