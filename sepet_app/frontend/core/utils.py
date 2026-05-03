import os
import sqlite3
import locale
import py7zr
import re
from django.conf import settings

# --- Locale and Formatting ---
try:
    locale.setlocale(locale.LC_TIME, 'tr_TR.UTF-8')
except locale.Error:
    print("Language setting for TR not found on system.")

def format_price(price):
    if price is None:
        return "N/A"
    return f'{f"{price:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")} TL'

# --- Database Helper Functions ---
def get_db_path():
    """Finds the path to the latest database file."""
    base_downloads_path = settings.DATABASE_FOLDER
    if not os.path.isdir(base_downloads_path):
        return None
    db_files = [os.path.join(base_downloads_path, f) for f in os.listdir(base_downloads_path) if f.endswith('.db')]
    if not db_files:
        return None
    latest_db_file = sorted(db_files)[-1]
    print(f"Using latest DB: {latest_db_file}")
    return latest_db_file

def get_shop_names():
    """Gets a list of all shop names and their logos from the database."""
    db_path = get_db_path()
    if not db_path:
        return [], {}
    try:
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cursor = con.cursor()
        cursor.execute("SELECT shop_id, shop_name, logo FROM shops_metadata ORDER BY shop_name;")
        rows = cursor.fetchall()
        con.close()

        shop_names = [row[1] for row in rows]
        shop_logo_mapping = {row[1]: row[2].replace('static/', '') for row in rows}
        
        return shop_names, shop_logo_mapping
    except sqlite3.Error as e:
        print(f"Database error while fetching shop names: {e}")
        return [], {}

def get_food_categories():
    """Gets food categories and their mappings from the database."""
    db_path = get_db_path()
    if not db_path:
        return []
    try:
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cursor = con.cursor()
        cursor.execute("SELECT product_id, TurkishName, category_id, TurkishCategory FROM food_categories_metadata;")
        rows = cursor.fetchall()
        con.close()
        
        productid_food_mapping = {row[0]: row[1] for row in rows}

        return list(productid_food_mapping.values())
    except sqlite3.Error as e:
        print(f"Database error while fetching food categories: {e}")
        return []

def regexp(expr, item):
    """Custom SQLite REGEXP function."""
    if item is None:
        return False
    try:
        reg = re.compile(expr, re.IGNORECASE)
        return reg.search(item) is not None
    except Exception as e:
        return False

def get_turkish_regex_pattern(text):
    """Converts a search string into a regex pattern matching Turkish characters."""
    mapping = {
        'c': '[cç]', 'ç': '[cç]',
        'g': '[gğ]', 'ğ': '[gğ]',
        'i': '[iıİ]', 'ı': '[iıİ]', 'İ': '[iıİ]',
        'o': '[oö]', 'ö': '[oö]',
        's': '[sş]', 'ş': '[sş]',
        'u': '[uü]', 'ü': '[uü]'
    }
    pattern = ""
    for char in text:
        if char.lower() in mapping:
            pattern += mapping[char.lower()]
        else:
            pattern += re.escape(char)
    return pattern

def unzip_new_db_file(base_downloads_path=None):
    """Finds all new zipped db files and unzips them"""
    if base_downloads_path is None:
        base_downloads_path = settings.DATABASE_FOLDER
    print(f"Unzip to: {base_downloads_path}")
    if not os.path.isdir(base_downloads_path):
        return None
    zipped_db_files = [os.path.join(base_downloads_path, f) for f in os.listdir(base_downloads_path) if f.endswith('.7z')]
    unzipped_db_files = [os.path.join(base_downloads_path, f) for f in os.listdir(base_downloads_path) if f.endswith('.db')]

    other_files = [os.path.join(base_downloads_path, f) for f in os.listdir(base_downloads_path) if not f.endswith(('.db', '.7z'))]

    if other_files:
        print(f'Found these other files on disk and removing them: {other_files}')
        for other_file in other_files:
            if os.path.isfile(other_file):
                os.remove(other_file)
                print(f"Deleted {other_file}")
            else:
                print(f"Skipping {other_file}")

    if (len(unzipped_db_files) == 1) and len(zipped_db_files) == 1: 
        print(f"Files found under {base_downloads_path}:")
        print(f"Unzipped: {unzipped_db_files}")
        print(f"Zipped: {zipped_db_files}")
        return None

    if not zipped_db_files:
        return None

    zipped_db_file = sorted(zipped_db_files)[-1]
    zipped_db_files = zipped_db_files[:-1]
    print(f"Found {len(zipped_db_files)+1} 7z files and the latest one is {zipped_db_file}")

    try:
        with py7zr.SevenZipFile(zipped_db_file, mode='r') as z:
            z.extractall(path=base_downloads_path)
            print("7z file extracted successfully. Now, deleting old files.")
            for unzipped_db_file in unzipped_db_files:
                os.remove(unzipped_db_file)
                print(f"Deleted {unzipped_db_file}")

            for zipped_file in zipped_db_files:
                os.remove(zipped_file)
                print(f"Deleted {zipped_file}")

    except Exception as e:
        print(f"Error extracting 7z file: {e}")

def calculate_price_change(prices_list):
    """Calculates price change and returns a dictionary with formatted text and direction."""
    if len(prices_list) < 2:
        return {'text': "N/A", 'direction': 'na'}

    first_price = prices_list[0]
    last_price = prices_list[-1]
    
    if first_price is None or last_price is None:
        return {'text': "N/A", 'direction': 'na'}

    if first_price == 0: # Avoid division by zero
        if last_price > 0:
            return {'text': f"{format_price(last_price)} (inf%)", 'direction': 'positive'}
        else:
            return {'text': "0,00 TL (0%)", 'direction': 'zero'}

    price_change_value = last_price - first_price
    percentage_change = (price_change_value / first_price) * 100
    
    formatted_text = f"{format_price(price_change_value)} ({percentage_change:.0f}%)"
    
    if price_change_value > 0:
        direction = 'positive'
    elif price_change_value < 0:
        direction = 'negative'
    else:
        direction = 'zero'
        formatted_text = "0,00 TL (0%)"

    return {'text': formatted_text, 'direction': direction}
