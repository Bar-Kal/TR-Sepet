import os
import glob
import json
import pickle
import re
import sqlite3
import py7zr
import numpy as np
import pandas as pd
from datetime import datetime
from gensim.models import FastText
from loguru import logger

def sanitize_name(name, is_path=False):
    """Sanitizes a string to be a valid name."""
    if is_path:
        base_name = os.path.splitext(os.path.basename(name))[0]
        # Go up two levels to get the shop name from the path
        parent_dir = os.path.basename(os.path.dirname(os.path.dirname(name)))
        name = f"{parent_dir}_{base_name}"
    return re.sub(r'[^a-zA-Z0-9_]', '_', name)


def compress_db(db_file_path: str):
    """
    Compresses the given file using py7zr.
    """
    if not os.path.exists(db_file_path):
        logger.error(f"Error: Database file not found at '{db_file_path}'. Cannot compress.")
        return

    archive_name = db_file_path + ".7z"
    try:
        logger.info(f"Attempting to compress '{db_file_path}' to '{archive_name}' using py7zr.")
        with py7zr.SevenZipFile(archive_name, 'w') as archive:
            archive.write(db_file_path, arcname=os.path.basename(db_file_path))
        logger.info(f"Successfully compressed '{db_file_path}' to '{archive_name}'.")
    except Exception as e:
        logger.error(f"An unexpected error occurred during py7zr compression: {e}")


def create_sqlite_from_csvs(db_folder: str, scraped_files_folder: str) -> str | None:
    """
    Finds all combined.csv files, loads them into pandas DataFrames,
    and saves them into a sqlite database. Each shop gets its own table.
    """
    today_str = datetime.now().strftime('%Y-%m-%d')
    db_file = os.path.join(db_folder, 'sepet_data_' + today_str + '.db')

    if not os.path.isdir(scraped_files_folder):
        logger.error(f"Error: Scraped files not found at '{scraped_files_folder}'")
        return None

    csv_files = [f for f in glob.glob(os.path.join(scraped_files_folder, '**', 'combined.csv'), recursive=True) if 'imported' not in f]

    if not csv_files:
        logger.info("No CSV files found in the downloads directory.")
        # If no new CSVs, check if a db file already exists. If so, do nothing.
        if os.path.exists(db_file):
            logger.info("Database file already exists. No new data to process.")
            return None
        # If no db file and no CSVs, create an empty db file.
        else:
            con = sqlite3.connect(db_file)
            con.close()
            logger.info("No CSVs found and no existing database file. Created an empty database file.")
            return None

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
            
            logger.info(f"Loaded {file_path} for shop '{shop_name}' into memory")

        except Exception as e:
            logger.error(f"Failed to process {file_path}. Reason: {e}")

    if data:
        con = sqlite3.connect(db_file)
        cursor = con.cursor()
        try:
            for shop_name, df in data.items():
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (shop_name,))
                if cursor.fetchone() is not None:
                    logger.info(f"Table '{shop_name}' exists. Merging new data.")
                    existing_df = pd.read_sql_query(f'SELECT * FROM "{shop_name}"', con)
                    combined_df = pd.concat([existing_df, df], ignore_index=True)
                    deduplicated_df = combined_df.drop_duplicates().reset_index(drop=True)
                    deduplicated_df.to_sql(shop_name, con, if_exists='replace', index=False)
                    logger.info(f"Merged and deduped data for '{shop_name}'. New shape: {deduplicated_df.shape}")
                else:
                    logger.info(f"Table '{shop_name}' does not exist. Creating it.")
                    df.to_sql(shop_name, con, if_exists='replace', index=False)
                    logger.info(f"Created table '{shop_name}' with new data. Shape: {df.shape}")

            logger.info(f"Successfully created/updated database file: {db_file}")
            return db_file

        except Exception as e:
            logger.error(f"An error occurred during database operation: {e}")
        finally:
            # Add shop metadata to the database
            try:
                logger.info("Adding shop metadata to the database.")
                with open(os.path.join('sepet_app', 'scraper', 'configs', 'shops.json'), 'r', encoding='utf-8') as f:
                    shops_data = json.load(f)
                
                shops_df = pd.DataFrame(shops_data)
                shops_df = shops_df[['shop_id', 'shop_name', 'base_url', 'logo']]
                
                shops_df.to_sql('shops_metadata', con, if_exists='replace', index=False)
                logger.info("Successfully added/updated 'shops_metadata' table.")

                # Add food category metadata to the database
                logger.info("Adding food category metadata to the database.")
                with open(os.path.join('sepet_app', 'scraper', 'configs', 'food.json'), 'r', encoding='utf-8') as f:
                    food_data = json.load(f)

                food_df = pd.DataFrame(food_data)
                food_df = food_df[['product_id', 'TurkishName', 'category_id', 'TurkishCategory']]

                food_df.to_sql('food_categories_metadata', con, if_exists='replace', index=False)
                logger.info("Successfully added/updated 'food_categories_metadata' table.")

            except Exception as e:
                logger.error(f"Failed to add metadata to the database. Reason: {e}")
            
            con.close()

    return None

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
