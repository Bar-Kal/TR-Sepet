import os
import sqlite3
import locale
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
    base_downloads_path = current_app.config['DATABASE_PATH']
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

# --- Route Definitions ---
@current_app.route('/', methods=['GET', 'POST'])
@current_app.route('/index', methods=['GET', 'POST'])
def index():
    """Renders the home page with shop and category dropdowns."""
    shop_names = get_shop_names()

    # --- Load static JSON configs ---
    food_path = Path(os.path.join(current_app.root_path, '..', 'scraper', 'configs', 'food.json'))
    with open(food_path, 'r', encoding='utf-8') as f:
        # Using json library is more direct than pandas for reading json
        import json
        food_file = json.load(f)
        food_categories = sorted([item['TurkishName'] for item in food_file])
        category_mapping = {item['category_id']: item['TurkishCategory'] for item in food_file}

    shops_path = Path(os.path.join(current_app.root_path, '..', 'scraper', 'configs', 'shops.json'))
    with open(shops_path, 'r', encoding='utf-8') as f:
        import json
        shops_file = json.load(f)
        shop_logo_mapping = {item['shop_name']: item['logo'] for item in shops_file}

    # --- Initialize variables ---
    charts_data = None
    shop_name = None
    category_name = None
    start_date_str = None
    end_date_str = None
    product_search = None
    no_results = True

    # --- Handle request ---
    if request.method == 'POST':
        shop_name = request.form.get('shop')
        category_name = request.form.get('category')
        date_range = request.form.get('date_range')
        product_search = request.form.get('product_search')
        if date_range:
            try:
                start_date_str, end_date_str = date_range.split(' - ')
            except ValueError:
                pass # Keep them as None
    else: # GET request, set some defaults
        if shop_names:
            shop_name = shop_names[0]
        if food_categories:
            category_name = "Süt" # A common default
        end_date_str = datetime.now().strftime('%Y-%m-%d')
        start_date_str = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

    results_title = f"{shop_name or ''} için {category_name or ''} Fiyat Analizi"

    # --- Query and Process Data ---
    db_path = get_db_path()
    if shop_name and category_name and db_path and shop_name in shop_names:
        
        # Build query dynamically and safely
        query = f'SELECT Display_Name, Price, Discount_Price, URL, category_id, Scrape_Timestamp FROM "{shop_name}" WHERE Search_Term = ?'
        params = [category_name]

        if start_date_str and end_date_str:
            query += " AND date(Scrape_Timestamp) BETWEEN ? AND ?"
            params.extend([start_date_str, end_date_str])

        if product_search:
            query += " AND Display_Name LIKE ?"
            params.append(f'%{product_search}%')

        query += " ORDER BY Scrape_Timestamp"

        try:
            con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            con.row_factory = sqlite3.Row # Access columns by name
            cursor = con.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            con.close()
            
            if rows:
                # Group rows by product name in Python
                product_groups = defaultdict(list)
                for row in rows:
                    product_groups[row['Display_Name']].append(dict(row))
                
                charts_data = []
                shop_logo = shop_logo_mapping.get(shop_name)
                
                for product_name, group_rows in product_groups.items():
                    # Process each group to find stats and format for chart
                    prices = []
                    discount_prices = []
                    dates = []
                    
                    for row in group_rows:
                        try:
                            prices.append(float(row['Price']))
                        except (ValueError, TypeError):
                            prices.append(None) # Handle non-numeric price
                        
                        try:
                            discount_prices.append(float(row['Discount_Price']))
                        except (ValueError, TypeError):
                            discount_prices.append(None)

                        try:
                            dates.append(datetime.strptime(row['Scrape_Timestamp'], '%Y-%m-%d %H:%M:%S.%f'))
                        except ValueError:
                            dates.append(datetime.strptime(row['Scrape_Timestamp'], '%Y-%m-%d %H:%M:%S'))


                    # Filter out None values for calculations
                    valid_prices = [p for p in prices if p is not None]
                    valid_discount_prices = [p for p in discount_prices if p is not None]

                    if not valid_prices:
                        continue # Skip products with no valid price data

                    chart_data = {
                        'product_name': product_name,
                        'product_category': category_mapping.get(group_rows[0]['category_id'], "Bilinmeyen"),
                        'labels': [d.strftime('%d %b') for d in dates],
                        'prices': prices,
                        'discount_prices': discount_prices,
                        'url': group_rows[-1]['URL'], # Latest URL
                        'highest_price': format_price(max(valid_prices)),
                        'lowest_price': format_price(min(valid_prices)),
                        'lowest_discount_price': format_price(min(valid_discount_prices)) if valid_discount_prices else "N/A",
                        'highest_discount_price': format_price(max(valid_discount_prices)) if valid_discount_prices else "N/A",
                        'shop_logo': shop_logo
                    }
                    charts_data.append(chart_data)

                if charts_data:
                    no_results = False

        except sqlite3.Error as e:
            print(f"Database query failed: {e}")
            no_results = True

    return render_template('index.html',
                           title='Anasayfa',
                           shop_names=shop_names,
                           food_categories=food_categories,
                           charts_data=charts_data,
                           category_name=category_name,
                           shop_name=shop_name,
                           start_date=start_date_str,
                           end_date=end_date_str,
                           results_title=results_title,
                           no_results=no_results,
                           product_search=product_search or '')


@current_app.route('/about')
def about():
    """Renders a simple about page."""
    return render_template('about.html', title='Hakkında')

# Keeping other routes as they were, they seem unrelated to the product data
@current_app.route('/test')
def test():
    """Renders a simple about page."""
    dummy = request.args.to_dict()
    print(dummy.get('shop_name', 'No shop_name provided'))
    return "<h1>Test endpointine ulaştınız</h1>"

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
        file.save(os.path.join(current_app.config['DATABASE_PATH'], filename))
        return jsonify({'message': 'File successfully uploaded'}), 200
    
    return jsonify({'error': 'File upload failed'}), 500
