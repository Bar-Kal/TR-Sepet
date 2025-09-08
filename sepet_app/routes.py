import os
import random
import time
from datetime import datetime
import concurrent.futures
import multiprocessing
from flask import render_template, current_app, redirect
import pandas as pd
import numpy as np
from pathlib import Path
from .scraper import A101Scraper
CHUNK_SIZE = 1

# By using current_app, we access the application instance created by the factory.
# This is a clean way to access the app without circular imports.
@current_app.route('/')
@current_app.route('/index')
def index():
    """Renders the home page."""
    # The render_template function automatically looks in the 'templates' folder.
    #return render_template('index.html', title='Home')
    return redirect('/scrape/A101')
    #return redirect('/test')


@current_app.route('/about')
def about():
    """Renders a simple about page."""
    return "<h1>About This Application</h1>"

def scrape_category(category_slice: pd.DataFrame, shop_name: str, filepath: str, today_str: str, worker_id: int):
    try:
        print(f'Got {len(category_slice)} rows for worker {worker_id}')
        for category in category_slice:

            if shop_name == "A101":
                scraper = A101Scraper()
            else:
                raise ValueError(f'Unknown shop name {shop_name}.')

            wait = random.randint(5, 20)
            print(f"Waiting {wait} seconds before scraping {category} for shop {scraper.shop_name} in worker {worker_id}")
            time.sleep(wait)  # Wait, to not create too much traffic to the server.
            retrieved_products = scraper.search(category)
            df = pd.DataFrame(retrieved_products)
            save_to_csv(shop_name=scraper.shop_name, df=df, filepath=filepath, filename=category + '.csv',
                        today_str=today_str)
            print(f'File for category {category} created successfully for shop {scraper.shop_name}.')

    except:
        raise Exception(f'Exception in worker {worker_id} while working on {category}')


@current_app.route('/scrape/<shop_name>')
def scrape(shop_name):
    """Scrapes A101 for products from the CSV and displays the links."""
    worker_id = 0
    jobs = []  # list of jobs
    df = pd.read_csv('sepet_app/static/food.csv', sep=';')
    products_categories_to_search = df['Turkish_names']#.tolist()  # e.g. Sucuk, Pirinc, etc.

    filepath = os.path.join('sepet_app', 'downloads')
    today_str = datetime.now().strftime('%Y-%m-%d')  # Get today's date in YYYY-MM-DD format

    sliced_products_categories_to_search = np.array_split(products_categories_to_search, CHUNK_SIZE)

    for category_slice in sliced_products_categories_to_search:
        # Declare a new process and pass arguments to it
        p = multiprocessing.Process(
            target=scrape_category,
            args=(
                category_slice,
                shop_name,
                filepath,
                today_str,
                worker_id,
            ),
        )
        jobs.append(p)
        worker_id = worker_id + 1

    for job in jobs:
        job.start()

    for job in jobs:
        print("Job: " + str(job) + " finished")
        job.join()

    #with concurrent.futures.ThreadPoolExecutor() as executor:
        #futures = [executor.submit(scrape_category, category, shop_name, filepath, today_str) for category in products_categories_to_search]
        #concurrent.futures.wait(futures)

    print("Starting data combination process...")
    combine_and_deduplicate_csvs(base_downloads_path=Path(os.path.join(filepath, shop_name, today_str)))

    product_urls = {}
    return render_template('scrape_results.html', product_urls=product_urls)


@current_app.route('/test')
def test():
    """Renders a simple about page."""
    combine_and_deduplicate_csvs(base_downloads_path=Path(os.path.join('sepet_app', 'downloads', '2025-test', 'A101')))
    return "<h1>You reached the Test endpoint</h1>"

def save_to_csv(shop_name: str, df: pd.DataFrame, filepath: str, filename: str, today_str: str):
    """
    Saves a list of dictionaries to a CSV file inside a date-stamped folder.
    """
    if len(df) < 1:
        print(f"No data to save for '{filename}' and '{shop_name}'.")
        return

    # 1. Create the full directory path (e.g., downloads/2023-10-27/shop_name)
    #    Pathlib is used for robust, cross-platform path handling.
    output_dir = Path(filepath) / shop_name / today_str
    output_dir.mkdir(parents=True, exist_ok=True)

    # 2. Write the data to the CSV file
    try:
        df.to_csv(os.path.join(output_dir,filename), sep=';', encoding='utf-8', index=False, header=True)
    except IOError as e:
        print(f"Error writing to file '{filepath}' for {shop_name}: {e}")


def combine_and_deduplicate_csvs(base_downloads_path: Path):
    """
    Loads all CSVs from subdirectories, combines them, removes duplicates by 'id',
    and saves the result as 'combined.csv' in the base path.
    """
    # Use .rglob to recursively find all .csv files, excluding 'combined.csv' itself.
    csv_files = [f for f in base_downloads_path.rglob('*.csv') if f.name != 'combined.csv']

    if not csv_files:
        print("No CSV files found to combine.")
        return

    print(f"Found {len(csv_files)} CSV files to process.")

    # Read all found CSVs into a list of DataFrames
    df_list = []
    for file in csv_files:
        try:
            df = pd.read_csv(file, sep=';')
            df_list.append(df)
        except pd.errors.EmptyDataError:
            print(f"Skipping empty file: {file}")
        except Exception as e:
            print(f"Error reading {file}: {e}")

    if not df_list:
        print("No data could be loaded from the found CSV files.")
        return

    # Concatenate all DataFrames into one
    combined_df = pd.concat(df_list, ignore_index=True)
    print(f"Combined {len(combined_df)} total rows from all files.")

    # Drop duplicates based on the 'id' column, keeping the first entry
    if 'id' in combined_df.columns:
        initial_rows = len(combined_df)
        # Ensure 'id' column is of a consistent type to avoid issues with mixed types
        combined_df['id'] = combined_df['id'].astype(str)
        combined_df.drop_duplicates(subset=['id'], keep='first', inplace=True)
        final_rows = len(combined_df)
        print(f"Removed {initial_rows - final_rows} duplicate rows based on unique 'id'.")
    else:
        print("Warning: 'id' column not found. Cannot remove duplicates.")

    # Save the final, clean DataFrame
    output_file = base_downloads_path / 'combined.csv'
    try:
        combined_df.to_csv(output_file, sep=';', index=False, encoding='utf-8')
        print(f"Successfully saved combined data with {len(combined_df)} unique rows to '{output_file}'")
    except IOError as e:
        print(f"Error writing to final file '{output_file}': {e}")