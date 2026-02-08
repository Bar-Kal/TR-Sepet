import os
import sqlite3
import locale
import py7zr
import re
import math
from flask import render_template, current_app, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from collections import defaultdict

PER_PAGE = 20 #Number of products to show per page

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
    base_downloads_path = current_app.config['DATABASE_FOLDER']
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
        return [], {}
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
        return [], {}

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

def unzip_new_db_file(base_downloads_path: str = current_app.config['DATABASE_FOLDER']):
    """Finds all new zipped db files and unzips them"""
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

    if (len(unzipped_db_files) == 1) and len(zipped_db_files) == 1: # There is already a zipped and unzipped file
        print(f"Files found under {base_downloads_path}:")
        print(f"Unzipped: {unzipped_db_files}")
        print(f"Zipped: {zipped_db_files}")
        return None

    zipped_db_file = sorted(zipped_db_files)[-1]
    zipped_db_files = zipped_db_files[:-1]
    print(f"Found {len(zipped_db_files)} 7z files and the latest one is {zipped_db_file}")

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

# --- Route Definitions ---
@current_app.route('/robots.txt')
def robots_txt():
    return send_from_directory(current_app.static_folder, 'robots.txt')


@current_app.route('/sitemap.xml')
def sitemap():
    return send_from_directory(current_app.static_folder, 'sitemap.xml')


@current_app.route('/', methods=['GET'])
@current_app.route('/index', methods=['GET'])
def index():
    """Renders the landing page."""
    return render_template('index.html', title='Ara', search_query='', show_header_search=True)


@current_app.route('/products', methods=['GET'])
def products():
    """Renders the home page with shop and category dropdowns."""

    # --- Initialize variables ---
    charts_data = None
    no_results = True
    search_error = None
    pagination = None
    all_products = []

    # --- Load metadata from database ---
    db_path = get_db_path()
    shop_names, shop_logo_mapping = get_shop_names()
    available_food_categories = get_food_categories()

    # --- Get selected filters by user ---
    selected_shops = request.args.getlist('shops')
    selected_category_name = request.args.get('category')
    date_range = request.args.get('date_range')

    # Usually in first request selected_category_name is None
    if selected_category_name is None:
        selected_category_name = 'all'

    if not selected_shops:
        selected_shops = ['Carrefoursa']

    if date_range:
        try:
            start_date_str, end_date_str = date_range.split(' - ')
        except ValueError:
            start_date_str = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
            end_date_str = datetime.now().strftime('%Y-%m-%d')
    else:
        start_date_str = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        end_date_str = datetime.now().strftime('%Y-%m-%d')

    # --- Handle request ---
    page = request.args.get('page', 1, type=int)
    product_search = request.args.get('q')

    # Server-side validation for product_search
    if product_search is not None:
        if not product_search.strip(): # Handles empty string and whitespace-only strings
            product_search = None
            search_error = "Lütfen bir arama terimi girin."
        else:
            # Regex to allow alphanumeric characters and Turkish specific characters
            # Min 2, Max 30 characters
            pattern = r"^[a-zA-Z0-9çÇğĞıİöÖşŞüÜ\s]{2,30}$"
            if not re.match(pattern, product_search) or not (2 <= len(product_search) <= 30):
                print(f"Invalid search query '{product_search}' received. Ignoring.")
                product_search = None
                search_error = "Arama çubuğuna sadece harf, rakam ve Türkçe karakterler girebilirsiniz. En az 2, en fazla 30 karakter olmalıdır."

    # --- Query and Process Data ---
    if db_path:

        # First, query all products based on search, shops, and date to determine available categories
        for current_shop in selected_shops:
            query = (f'SELECT {current_shop}.Scrape_Timestamp, {current_shop}.Display_Name, {current_shop}.Discount_Price, {current_shop}.Price, '
                     f'shops_metadata.shop_name as Shop_Name, '
                     f'food_categories_metadata.TurkishName as Product_Name, food_categories_metadata.TurkishCategory as Category_Name, '
                     f'CONCAT(shops_metadata.base_url, {current_shop}.URL) as Product_URL FROM "{current_shop}"'
                     f'LEFT JOIN shops_metadata ON {current_shop}.Shop_ID = shops_metadata.shop_id '
                     f'LEFT JOIN food_categories_metadata ON {current_shop}.Product_ID = food_categories_metadata.product_id')
            params = []
            conditions = []

            if start_date_str and end_date_str:
                conditions.append("date(Scrape_Timestamp) BETWEEN ? AND ?")
                params.extend([start_date_str, end_date_str])

            if selected_category_name != 'all':
                conditions.append("Product_Name = ?")
                params.append(selected_category_name)

            if product_search:
                tr_pattern = get_turkish_regex_pattern(product_search)
                if ' ' in product_search:
                    conditions.append("Display_Name REGEXP ?")
                    params.append(tr_pattern)
                else:
                    conditions.append("Display_Name REGEXP ?")
                    params.append(rf'(^|\s){tr_pattern}')

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += f" ORDER BY Scrape_Timestamp "

            try:
                con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
                con.row_factory = sqlite3.Row
                con.create_function("REGEXP", 2, regexp)
                cursor = con.cursor()
                cursor.execute(query, params)
                rows = cursor.fetchall()
                con.close()

                if rows:
                    for row in rows:
                        product = dict(row)
                        all_products.append(product)

            except sqlite3.Error as e:
                print(f"Database query failed for shop {current_shop}: {e}")

        # Now, determine available categories from the full search results
        if all_products:
            if product_search:
                # Get the categories from all products found in the search
                available_food_categories = sorted(list(set(p['Product_Name'] for p in all_products)))
            else:
                # If no search term, all categories are considered available already in available_food_categories
                pass

            # Group rows by product name and shop name for the products to be displayed
            product_groups = defaultdict(list)
            for row in all_products:
                product_groups[(row['Display_Name'], row['Shop_Name'])].append(row)

            # --- Pagination Logic (based on the number of groups to display) ---
            total_items = len(product_groups)
            total_pages = math.ceil(total_items / PER_PAGE)
            offset = (page - 1) * PER_PAGE

            paginated_group_keys = list(product_groups.keys())[offset : offset + PER_PAGE]

            pagination = {
                'page': page,
                'total_pages': total_pages,
                'total_items': total_items,
                'per_page': PER_PAGE,
                'has_prev': page > 1,
                'has_next': page < total_pages
            }
            # --- End Pagination Logic ---

            charts_data = []

            # Loop ONLY through the keys for the current page
            for (product_name, shop_name_of_product) in paginated_group_keys:
                group_rows = product_groups[(product_name, shop_name_of_product)]
                prices, discount_prices, dates = [], [], []

                for row in group_rows:
                    prices.append(float(row['Price']))
                    discount_prices.append(float(row['Discount_Price']))
                    dates.append(datetime.strptime(row['Scrape_Timestamp'], '%Y-%m-%d %H:%M:%S'))

                valid_prices = [p for p in prices if p is not None]
                if not valid_prices:
                    continue

                valid_discount_prices = [p for p in discount_prices if p is not None]
                shop_logo = shop_logo_mapping.get(shop_name_of_product)

                chart_data = {
                    'product_name': product_name,
                    'product_category': group_rows[0]['Category_Name'],
                    'search_term': group_rows[0]['Product_Name'],
                    'labels': [d.strftime('%d %b') for d in dates],
                    'prices': prices,
                    'discount_prices': discount_prices,
                    'url': group_rows[-1]['Product_URL'],
                    'highest_price': format_price(max(valid_prices)),
                    'lowest_price': format_price(min(valid_prices)),
                    'lowest_discount_price': format_price(min(valid_discount_prices)) if valid_discount_prices else "N/A",
                    'highest_discount_price': format_price(max(valid_discount_prices)) if valid_discount_prices else "N/A",
                    'shop_logo': shop_logo
                }
                charts_data.append(chart_data)

            if charts_data:
                no_results = False

        return render_template('products.html',
                       title='Ürünler',
                       shop_names=shop_names,
                       food_categories=available_food_categories,
                       charts_data=charts_data,
                       category_name=selected_category_name,
                       selected_shops=selected_shops,
                       start_date=start_date_str,
                       end_date=end_date_str,
                       results_title='Fiyat Analizi',
                       no_results=no_results,
                       product_search=product_search or '',
                       search_query=product_search or '',
                       shop_logo_mapping=shop_logo_mapping,
                       search_error=search_error,
                       show_header_search=True,
                       pagination=pagination)




@current_app.route('/about')
def about():
    """Renders a simple about page."""
    return render_template('about.html', title='Hakkında')


@current_app.route('/privacy')
def privacy():
    """Renders the privacy policy page."""
    contact_email = os.getenv('CONTACT_EMAIL', 'default@example.com') # Provide a default email if env var is not set
    return render_template('privacy.html', title='Gizlilik Politikası', contact_email=contact_email)


@current_app.route('/upload_secure', methods=['POST'])
def upload_secure():
    """Handles secure file uploads."""
    secret_key = request.form.get('secret_key')
    if secret_key != current_app.config['UPLOAD_SECRET_KEY']:
        return jsonify({'error': 'Invalid secret key'}), 401

    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file:
        filename = secure_filename(file.filename)
        print(f'Upload endpoint was hit and a file is being uploaded named {filename}.')
        file.save(os.path.join(current_app.config['DATABASE_FOLDER'], filename))
        unzip_new_db_file(base_downloads_path=current_app.config['DATABASE_FOLDER'])
        return jsonify({'message': 'File successfully uploaded and unzipped'}), 200
    
    return jsonify({'error': 'File upload failed'}), 500

