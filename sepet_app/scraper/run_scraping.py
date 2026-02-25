import os
import argparse
import random
import time
import json
import pandas as pd
from datetime import datetime
from pathlib import Path
from loguru import logger
from typing import Union
from .src.core.advanced_base import AdvancedBaseScraper
from .src.core.base_scraper import BaseScraper
from .src.core.factory import get_scraper
from .src.utilities.create_database import  create_sqlite_from_csvs, compress_db
from .src.utilities.classifier import ProductClassifier

RUN_PRODUCT_CLASSIFIER = True

def scrape_categories(scraper: Union[BaseScraper, AdvancedBaseScraper], products_categories: json, filepath: str, today_str: str):
    """
    Scrapes product categories for a given shop and saves the results to CSV files.

    Args:
        scraper (SimpleBaseScraper): The scraper object for the shop.
        products_categories (json): JSON containing the products and categories to scrape. (food.json)
        filepath (str): The base filepath to save the CSV files.
        today_str (str): The current date as a string in 'YYYY-MM-DD' format.
    """
    logger.info(f'Got {len(products_categories)} product categories to scrape for shop {scraper.shop_name}.')

    for product in products_categories: # List of products, Sucuk, Pirinc, etc.
        product_name = product['TurkishName']
        try:
            wait = random.randint(2, 10)
            logger.info(f"Waiting {wait} seconds before scraping {product_name} in shop {scraper.shop_name}")
            time.sleep(wait)  # Wait, to not create too much traffic to the server.
            retrieved_products = scraper.search(product=product)
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

    # Create the full directory path (e.g., downloads/scraped_files/shop_name/2023-10-27/)
    # Pathlib is used for robust, cross-platform path handling.
    output_dir = Path(filepath) / shop_name / today_str
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        df.to_csv(os.path.join(output_dir,filename), sep=';', encoding='utf-8', index=False, header=True)
    except IOError as e:
        logger.error(f"Error writing to file '{filepath}' for {shop_name}: {e}")

def filter_nonfood(list_of_products: list, product_classifier):
    food_labels = []
    for product in list_of_products:
        model_result = product_classifier.predict(text=product)

        if model_result.get('label') == 1:
            food_labels.append(1)  # --> Food
        else:
            confidence = float(str(model_result.get('confidence'))[:3])
            if 0.2 <= confidence <= 0.7:
                logger.warning(f"Product {product} with confidence {confidence} filtered out.")
            food_labels.append(0)  # --> Non-Food

    return pd.DataFrame(food_labels, columns = ['food'])


def combine_and_filter_csvs(base_downloads_path: Path):
    """
    Combines all CSV files in a directory, removes duplicates, and saves the result.

    This function recursively finds all '.csv' files in the given base path,
    combines them into a single pandas DataFrame, and filters out products with fasttext models.
    It then saves the cleaned DataFrame as 'combined.csv' in the same directory.

    Args:
        base_downloads_path (Path): The path to the directory containing the CSV files.
    """
    # Use .rglob to recursively find all .csv files, excluding 'combined.csv' itself.
    csv_files = [f for f in base_downloads_path.rglob('*.csv') if f.name != 'combined.csv']

    if not csv_files:
        logger.info("No CSV files found to combine.")
        return

    logger.info(f"Found {len(csv_files)} CSV files to process.")

    csvfiles_dtypes = {'Category_ID': int, 'Shop_ID': int, 'Product_ID': int}

    # Read all found CSVs into a list of DataFrames
    df_list = []
    for file in csv_files:
        try:
            df = pd.read_csv(file, sep=';', dtype=csvfiles_dtypes)
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
    combined_df.reset_index(inplace=True, drop=True)
    logger.info(f"Combined {len(combined_df)} total rows from all files.")

    # Save the final, clean DataFrame
    output_filepath = os.path.join(base_downloads_path, 'combined.csv')

    try:
        combined_df.to_csv(output_filepath, sep=';', index=False, encoding='utf-8')
        logger.info(f"Successfully saved combined data with {len(combined_df)} unique rows to '{output_filepath}'")
    except IOError as e:
        logger.error(f"Error writing to final file '{output_filepath}': {e}")

def filtering_all_combined_files(base_download_path_of_shop: Path):
    """
    Run on all generated combined.csv files for all shops filtering like Bert-Classification.

    This function recursively finds all 'combined.csv' for the entire download history and applies filtering.
    The combined.csv files gets overwritten.

    Args:
        base_download_path_of_shop (Path): The path to the directory containing the scraped CSV files.
    """

    if RUN_PRODUCT_CLASSIFIER:
        product_classifier = ProductClassifier()
        csvfiles_dtypes = {'Category_ID': int, 'Shop_ID': int, 'Product_ID': int}

        # Use .rglob to recursively find all .csv files, excluding 'combined.csv' itself.
        combined_file_paths = [f for f in base_download_path_of_shop.rglob('combined.csv')]
        logger.info(f"Found {len(combined_file_paths)} combined CSV files to process.")

        if not combined_file_paths:
            logger.info("No combined.csv files found to combine.")
            return

        for filepath in combined_file_paths:
            try:
                logger.info(f"--- Processing file {filepath} ---")
                combined_df = pd.read_csv(filepath, sep=';', dtype=csvfiles_dtypes, encoding='utf-8')
                food_labels = filter_nonfood(list_of_products=combined_df['Display_Name'].tolist(),
                                             product_classifier=product_classifier)
                combined_df = combined_df.join(food_labels)
                combined_df = combined_df[combined_df['food'] == 1]
                combined_df.drop('food', axis=1, inplace=True)
                combined_df.to_csv(filepath, sep=';', index=False, encoding='utf-8', header=True)

            except pd.errors.EmptyDataError:
                logger.info(f"Skipping empty file: {filepath}")
            except Exception as e:
                logger.error(f"Error reading {filepath}: {e}")


def main(arg_shop_name: str = None):
    """
    Main function to orchestrate the scraping process for all shops.


    This function reads the shop configurations from a JSON file, then iterates
    through each shop, initializing the corresponding scraper and running the scraping process.
    After scraping, it combines and deduplicates the generated CSV files.
    """
    shop_num = 1

    with open(os.path.join('sepet_app', 'scraper', 'configs', 'shops.json'), 'r', encoding='utf-8') as f:
        shops = json.load(f)

    with open(os.path.join('sepet_app', 'scraper', 'configs', 'food.json'), 'r', encoding='utf-8') as f:
        products_and_categories = json.load(f)

    today_str = datetime.now().strftime('%Y-%m-%d')  # Get today's date in YYYY-MM-DD format
    download_folder = os.path.join('sepet_app', 'scraper', 'downloads', 'scraped_files')

    for shop in shops:
        shop_name = shop['shop_name']
        logfile_name = datetime.now().strftime("%Y%m%d-%H%M%S") + '_' + shop_name + '.log'
        log_sink_id = logger.add(os.path.join('sepet_app', 'scraper', 'logs', logfile_name), rotation="10 MB")

        if shop['scrape']:
            if arg_shop_name is not None and arg_shop_name != shop_name:
                continue

            logger.info(f"--- Starting process for {shop_name}: {shop_num}/{len(shops)} shops ---")
            logger.info(f"Distilbert classifier will be executed: {RUN_PRODUCT_CLASSIFIER}")

            # Use the factory to get the correct scraper
            scraper = get_scraper(shop_config=shop, ignore_nonfood=RUN_PRODUCT_CLASSIFIER)
            scrape_categories(
                scraper=scraper,
                products_categories=products_and_categories,
                filepath=download_folder,
                today_str=today_str
            )
            logger.info("Starting data combination process...")
            combine_and_filter_csvs(base_downloads_path=Path(os.path.join(download_folder, scraper.shop_name, today_str)))
            logger.info(f"--- Finished process for {shop_name} ---")
            del scraper
            logger.remove(log_sink_id)
            shop_num = shop_num + 1
        else:
            logger.info(f"--- Skipping shop {shop_name} because scrape parameter in shops.json is set to {shop['scrape']}. ---")

    logfile_name = datetime.now().strftime("%Y%m%d-%H%M%S") + '_sqlite_creation.log'
    log_sink_id = logger.add(os.path.join('sepet_app', 'scraper', 'logs', logfile_name), rotation="10 MB")

    logger.info(f"--- Starting to filter all combined.csv files ---")
    filtering_all_combined_files(base_download_path_of_shop=Path(download_folder))

    logger.info(f"--- Starting to create database file ---")
    db_file_path = create_sqlite_from_csvs(db_folder=os.path.join('sepet_app', 'scraper', 'downloads', 'db_files'),
                                           scraped_files_folder=os.path.join('sepet_app', 'scraper', 'downloads', 'scraped_files'))

    if db_file_path:
        compress_db(db_file_path)

    logger.remove(log_sink_id)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pass shop name to scrape a single shop.")
    parser.add_argument(
        '--shop',
        type = str,
        default=None,
        help="Shop name (e.g. Migros)"
    )
    args = parser.parse_args()
    shop_name = args.shop

    main(shop_name)
