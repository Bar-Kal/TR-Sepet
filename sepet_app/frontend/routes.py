import os
import sqlite3
import locale
import py7zr
import re
import math
from flask import render_template, current_app, request, jsonify
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

# --- Locale and Formatting ---
try:
    locale.setlocale(locale.LC_TIME, 'tr_TR.UTF-8')
except locale.Error:
    print("Türkçe yerel ayarı desteklenmiyor, varsayılan kullanılıyor.")

def format_price(price):
    if price is None:
        return "N/A"
    return f'{f"{price:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")} TL'

# --- Database Helper Functions ---
def get_db_path():
    """Finds the path to the latest database file."""
    base_downloads_path = current_app.config['DATABASE_FOLDER']
    print(f"Get DB from: {base_downloads_path}")
    if not os.path.isdir(base_downloads_path):
        return None
    db_files = [os.path.join(base_downloads_path, f) for f in os.listdir(base_downloads_path) if f.endswith('.db')]
    if not db_files:
        return None
    return sorted(db_files)[-1]

def get_shop_names():
    """Gets a list of all shop names (tables) from the database."""
    db_path = get_db_path()
    if not db_path:
        return []
    try:
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cursor = con.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        shops = [row[0] for row in cursor.fetchall()]
        con.close()
        return shops
    except sqlite3.Error as e:
        print(f"Database error while fetching shop names: {e}")
        return []

def unzip_new_db_file():
    """Finds all new zipped db files and unzips them"""
    base_downloads_path = current_app.config['DATABASE_FOLDER']
    if not os.path.isdir(base_downloads_path):
        return None
    zipped_db_files = [os.path.join(base_downloads_path, f) for f in os.listdir(base_downloads_path) if f.endswith('.7z')]
    unzipped_db_files = [os.path.join(base_downloads_path, f) for f in os.listdir(base_downloads_path) if f.endswith('.db')]

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
@current_app.route('/', methods=['GET'])
@current_app.route('/index', methods=['GET'])
def index():
    """Renders the landing page."""
    return render_template('index.html', title='Ara', search_query='', show_header_search=True)


@current_app.route('/products', methods=['GET'])
def products():
    """Renders the home page with shop and category dropdowns."""
    shop_names = get_shop_names()

    # --- Load static JSON configs ---
    food_path = Path(os.path.join(current_app.root_path, '..', 'scraper', 'configs', 'food.json'))
    with open(food_path, 'r', encoding='utf-8') as f:
        import json
        food_file = json.load(f)
        food_categories = sorted([item['TurkishName'] for item in food_file])
        available_food_categories = food_categories
        category_mapping = {item['category_id']: item['TurkishCategory'] for item in food_file}

    shops_path = Path(os.path.join(current_app.root_path, '..', 'scraper', 'configs', 'shops.json'))
    with open(shops_path, 'r', encoding='utf-8') as f:
        import json
        shops_file = json.load(f)
        shop_logo_mapping = {item['shop_name']: item['logo'].replace('static/', '') for item in shops_file}

    # --- Initialize variables ---
    charts_data = None
    no_results = True
    search_error = None
    pagination = None

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

    selected_shops = request.args.getlist('shops')
    category_name = request.args.get('category')
    date_range = request.args.get('date_range')

    if not selected_shops:
        selected_shops = shop_names
    
    if not category_name:
        category_name = "all"

    if date_range:
        try:
            start_date_str, end_date_str = date_range.split(' - ')
        except ValueError:
            start_date_str = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            end_date_str = datetime.now().strftime('%Y-%m-%d')
    else:
        start_date_str = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        end_date_str = datetime.now().strftime('%Y-%m-%d')


    results_title = f"Fiyat Analizi"

    # --- Query and Process Data ---
    db_path = get_db_path()
    if db_path: # Removed category_name from this check

        all_products = []
        shops_to_query = selected_shops

        # First, query all products based on search, shops, and date to determine available categories
        for current_shop in shops_to_query:
            query = f'SELECT Display_Name, Price, Discount_Price, URL, category_id, Scrape_Timestamp, Search_Term FROM "{current_shop}"'
            params = []
            conditions = []

            if start_date_str and end_date_str:
                conditions.append("date(Scrape_Timestamp) BETWEEN ? AND ?")
                params.extend([start_date_str, end_date_str])

            if product_search:
                if ' ' in product_search:
                    conditions.append("Display_Name LIKE ?")
                    params.append(f'%{product_search}%')
                else:
                    conditions.append("(Display_Name LIKE ? OR Display_Name LIKE ?)")
                    params.extend([f'{product_search}%', f'% {product_search}%'])

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY Scrape_Timestamp"

            try:
                con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
                con.row_factory = sqlite3.Row
                cursor = con.cursor()
                cursor.execute(query, params)
                rows = cursor.fetchall()
                con.close()

                if rows:
                    for row in rows:
                        product = dict(row)
                        product['shop_name'] = current_shop
                        all_products.append(product)

            except sqlite3.Error as e:
                print(f"Database query failed for shop {current_shop}: {e}")

        # Now, determine available categories from the full search results
        if all_products:
            if product_search:
                # Get the categories from all products found in the search
                available_food_categories = sorted(list(set(p['Search_Term'] for p in all_products)))
            else:
                # If no search term, all categories are considered available
                available_food_categories = food_categories

            # Filter the fetched products by the selected category for display
            if category_name and category_name != 'all':
                products_to_display = [p for p in all_products if p['Search_Term'] == category_name]
            else:
                products_to_display = all_products

            # Group rows by product name and shop name for the products to be displayed
            product_groups = defaultdict(list)
            for row in products_to_display:
                product_groups[(row['Display_Name'], row['shop_name'])].append(row)

            # --- Pagination Logic (based on the number of groups to display) ---
            PER_PAGE = 40
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
                    try:
                        prices.append(float(row['Price']))
                    except (ValueError, TypeError):
                        prices.append(None)

                    try:
                        discount_prices.append(float(row['Discount_Price']))
                    except (ValueError, TypeError):
                        discount_prices.append(None)

                    try:
                        dates.append(datetime.strptime(row['Scrape_Timestamp'], '%Y-%m-%d %H:%M:%S.%f'))
                    except ValueError:
                        dates.append(datetime.strptime(row['Scrape_Timestamp'], '%Y-%m-%d %H:%M:%S'))

                valid_prices = [p for p in prices if p is not None]
                if not valid_prices:
                    continue

                valid_discount_prices = [p for p in discount_prices if p is not None]
                shop_logo = shop_logo_mapping.get(shop_name_of_product)

                chart_data = {
                    'product_name': product_name,
                    'product_category': category_mapping.get(group_rows[0]['category_id'], "Bilinmeyen"),
                    'search_term': group_rows[0]['Search_Term'],
                    'labels': [d.strftime('%d %b') for d in dates],
                    'prices': prices,
                    'discount_prices': discount_prices,
                    'url': group_rows[-1]['URL'],
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
                       category_name=category_name,
                       selected_shops=selected_shops,
                       start_date=start_date_str,
                       end_date=end_date_str,
                       results_title=results_title,
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
        file.save(os.path.join(current_app.config['DATABASE_FOLDER'], filename))
        unzip_new_db_file()
        return jsonify({'message': 'File successfully uploaded and unzipped'}), 200
    
    return jsonify({'error': 'File upload failed'}), 500

