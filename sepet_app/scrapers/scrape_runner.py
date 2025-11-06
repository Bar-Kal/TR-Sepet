import os
import json
import random
import time
import json
import pandas as pd
from datetime import datetime
from pathlib import Path
from loguru import logger
from typing import Union
from .advanced_base import AdvancedBaseScraper
from .base_scraper import BaseScraper
from .factory import get_scraper

def scrape_categories(scraper: Union[BaseScraper, AdvancedBaseScraper], products_categories: json, shop_name: str, filepath: str, today_str: str):
    """
    Scrapes product categories for a given shop and saves the results to CSV files.

    Args:
        scraper (SimpleBaseScraper): The scrapers object for the shop.
        products_categories (json): JSON containing the products and categories to scrape. (food.json)
        shop_name (str): The name of the shop.
        filepath (str): The base filepath to save the CSV files.
        today_str (str): The current date as a string in 'YYYY-MM-DD' format.
    """
    logger.info(f'Got {len(products_categories)} product categories to scrape for shop {shop_name}.')

    for product in products_categories: # List of products, Sucuk, Pirinc, etc.
        product_name = product['TurkishName']
        try:
            wait = random.randint(2, 10)
            logger.info(f"Waiting {wait} seconds before scraping {product_name} in shop {scraper.shop_name}")
            time.sleep(wait)  # Wait, to not create too much traffic to the server.
            retrieved_products = scraper.search(product=product['TurkishName'], category_id=product['category_id'])
            df = pd.DataFrame(retrieved_products)
            save_to_csv(shop_name=scraper.shop_name, df=df, filepath=filepath, filename=product_name + '.csv',today_str=today_str)
            logger.info(f'File for product {product_name} created successfully for shop {scraper.shop_name}.')
        except Exception as e:
            logger.error(f'Exception occurred while working on {product_name}: {e}')


def save_to_csv(shop_name: str, df: pd.DataFrame, filepath: str, filename: str, today_str: str):
    """
    Saves a pandas DataFrame to a CSV file in a structured directory.

    The directory structure is `filepath/shop_name/today_str/filename`.

    Args:
        shop_name (str): The name of the shop, used to create a subdirectory.
        df (pd.DataFrame): The DataFrame to be saved.
        filepath (str): The base directory for saving the file.
        filename (str): The name of the CSV file.
        today_str (str): The current date in 'YYYY-MM-DD' format, used for a subdirectory.
    """
    if len(df) < 1:
        logger.info(f"No data to save for '{filename}' and '{shop_name}'.")
        return

    # Create the full directory path (e.g., downloads/2023-10-27/shop_name)
    # Pathlib is used for robust, cross-platform path handling.
    output_dir = Path(filepath) / shop_name / today_str
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        df.to_csv(os.path.join(output_dir,filename), sep=';', encoding='utf-8', index=False, header=True)
    except IOError as e:
        logger.error(f"Error writing to file '{filepath}' for {shop_name}: {e}")


def combine_and_deduplicate_csvs(base_downloads_path: Path):
    """
    Combines all CSV files in a directory, removes duplicates, and saves the result.

    This function recursively finds all '.csv' files in the given base path,
    combines them into a single pandas DataFrame, removes duplicate rows based
    on the 'id' column, and saves the cleaned DataFrame as 'combined.csv' in the
    same directory.

    Args:
        base_downloads_path (Path): The path to the directory containing the CSV files.
    """
    # Use .rglob to recursively find all .csv files, excluding 'combined.csv' itself.
    csv_files = [f for f in base_downloads_path.rglob('*.csv') if f.name != 'combined.csv']

    if not csv_files:
        logger.info("No CSV files found to combine.")
        return

    logger.info(f"Found {len(csv_files)} CSV files to process.")

    # Read all found CSVs into a list of DataFrames
    df_list = []
    for file in csv_files:
        try:
            df = pd.read_csv(file, sep=';')
            df_list.append(df)
        except pd.errors.EmptyDataError:
            logger.info(f"Skipping empty file: {file}")
        except Exception as e:
            logger.error(f"Error reading {file}: {e}")

    if not df_list:
        logger.info("No data could be loaded from the found CSV files.")
        return

    # Concatenate all DataFrames into one
    combined_df = pd.concat(df_list, ignore_index=True)
    logger.info(f"Combined {len(combined_df)} total rows from all files.")

    # Drop duplicates based on the 'product_id' column, keeping the first entry
    if 'product_id' in combined_df.columns:
        initial_rows = len(combined_df)
        # Ensure 'product_id' column is of a consistent type to avoid issues with mixed types
        combined_df['product_id'] = combined_df['product_id'].astype(str)
        combined_df.drop_duplicates(subset=['product_id'], keep='first', inplace=True)
        final_rows = len(combined_df)
        logger.info(f"Removed {initial_rows - final_rows} duplicate rows based on unique 'product_id'.")
    else:
        logger.warning("Warning: 'id' column not found. Cannot remove duplicates.")

    # Save the final, clean DataFrame
    output_file = base_downloads_path / 'combined.csv'
    try:
        combined_df.to_csv(output_file, sep=';', index=False, encoding='utf-8')
        logger.info(f"Successfully saved combined data with {len(combined_df)} unique rows to '{output_file}'")
    except IOError as e:
        logger.error(f"Error writing to final file '{output_file}': {e}")


def main():
    """
    Main function to orchestrate the scraping process for all shops.

    This function reads the shop configurations from a JSON file, then iterates
    through each shop, initializing the corresponding scraper and running the scraping process.
    After scraping, it combines and deduplicates the generated CSV files.
    """
    IGNORE_NONFOOD = False

    with open(os.path.join('sepet_app', 'configs', 'shops.json')) as f:
        shops = json.load(f)

    with open(os.path.join('sepet_app', 'configs', 'food.json'), 'r', encoding='utf-8') as f:
        products_and_categories = json.load(f)

    today_str = datetime.now().strftime('%Y-%m-%d')  # Get today's date in YYYY-MM-DD format
    filepath = os.path.join('sepet_app', 'downloads')

    for shop in shops:
        shop_name = shop['shop_name']
        log_sink_id = logger.add(f"sepet_app/logs/{datetime.now().strftime("%Y%m%d-%H%M%S")}_{shop_name}.log", rotation="10 MB")
        logger.info(f"--- Starting process for {shop_name} ---")
        logger.info(f"Ignoring non-food products: {IGNORE_NONFOOD}")
        logger.info(f"Found {len(shops)} shops to scrape.")

        # Use the factory to get the correct scraper
        scraper = get_scraper(shop_config=shop, ignore_nonfood=IGNORE_NONFOOD)
        scrape_categories(
            scraper=scraper,
            products_categories=products_and_categories,
            shop_name=scraper.shop_name,
            filepath=filepath,
            today_str=today_str
        )
        logger.info("Starting data combination process...")
        combine_and_deduplicate_csvs(base_downloads_path=Path(os.path.join(filepath, scraper.shop_name, today_str)))
        logger.info(f"--- Finished process for {shop_name} ---")
        del scraper
        logger.remove(log_sink_id)
