import os
import pandas as pd
import random
import locale
from flask import render_template, current_app, request
from datetime import datetime, timedelta
from pathlib import Path

try:
    locale.setlocale(locale.LC_TIME, 'tr_TR.UTF-8')
except locale.Error:
    print("Türkçe yerel ayarı desteklenmiyor, varsayılan kullanılıyor.")

def format_price(price):
    return f'{f"{price:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")} TL'

@current_app.route('/', methods=['GET', 'POST'])
@current_app.route('/index', methods=['GET', 'POST'])
def index():
    """Renders the home page with shop and category dropdowns."""
    shop_names = sorted(list(current_app.pickled_shop_data.keys()))

    # Load food categories and create a mapping
    food_path = Path(os.path.join(current_app.root_path, '..', 'scraper' , 'configs' , 'food.json'))
    with open(food_path, 'r', encoding='utf-8') as f:
        food_file = pd.read_json(f)
        food_categories = food_file['TurkishName'].tolist()
        category_mapping = food_file.set_index('category_id')['TurkishCategory'].to_dict()
    food_categories.sort()

    shops_path = Path(os.path.join(current_app.root_path, '..', 'scraper', 'configs', 'shops.json'))
    with open(shops_path, 'r', encoding='utf-8') as f:
        shops_file = pd.read_json(f)
        shop_logo_mapping = shops_file.set_index('shop_name')['logo'].to_dict()

    charts_data = None
    shop_name = None
    category_name = None
    start_date_str = None
    end_date_str = None

    if request.method == 'POST':
        shop_name = request.form.get('shop')
        category_name = request.form.get('category')
        date_range = request.form.get('date_range')
        product_search = request.form.get('product_search')
        
        if date_range:
            try:
                start_date_str, end_date_str = date_range.split(' - ')
            except ValueError:
                start_date_str, end_date_str = None, None
        else:
            start_date_str, end_date_str = None, None
            
        print(f"POST request: date_range='{date_range}', product_search='{product_search}'")
    else: # GET request
        if shop_names:
            shop_name = random.choice(shop_names)
        if food_categories:
            category_name = random.choice(food_categories)
        product_search = None
        start_date_str, end_date_str = None, None

    full_df = None
    if shop_name and shop_name in current_app.pickled_shop_data:
        df = current_app.pickled_shop_data[shop_name].copy()
        print(f"Processing data for shop: {shop_name}")
        try:
            df['Date'] = pd.to_datetime(df['Scrape_Timestamp'], errors='coerce').dt.normalize()
            df.dropna(subset=['Date'], inplace=True)
            full_df = df
        except KeyError:
            print(f"KeyError: 'Scrape_Timestamp' not found for shop {shop_name}")

    results_title = f"{shop_name} için {category_name} Fiyat Analizi"
    no_results = False

    if full_df is not None and not full_df.empty:

        if start_date_str and end_date_str:
            start_date = pd.to_datetime(start_date_str)
            end_date = pd.to_datetime(end_date_str)
            full_df = full_df[(full_df['Date'] >= start_date) & (full_df['Date'] <= end_date)]
        else:
            end_date_dt = datetime.now().date()
            start_date_dt = end_date_dt - timedelta(days=7)
            
            start_date = pd.to_datetime(start_date_dt)
            end_date = pd.to_datetime(end_date_dt)

            full_df = full_df[(full_df['Date'] >= start_date) & (full_df['Date'] <= end_date)]
        
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        
        full_df['Price'] = pd.to_numeric(full_df['Price'], errors='coerce')
        full_df['Discount_Price'] = pd.to_numeric(full_df['Discount_Price'], errors='coerce')
        full_df.dropna(subset=['Price'], inplace=True)

        product_df = full_df[full_df['Search_Term'] == category_name]
        if product_search:
            product_df = product_df[product_df['Display_Name'].str.contains(product_search, case=False, na=False)]

        if not product_df.empty:
            charts_data = []
            shop_logo = shop_logo_mapping.get(shop_name)
            for product_name, group in product_df.groupby('Display_Name'):
                group = group.sort_values('Date')
                
                latest_url = group['URL'].iloc[-1]
                highest_price = group['Price'].max()
                lowest_price = group['Price'].min()
                
                discount_prices = group['Discount_Price'].fillna(0).tolist()
                lowest_discount_price = group['Discount_Price'].min()
                highest_discount_price = group['Discount_Price'].max()

                category_id = group['category_id'].iloc[0]
                product_category = category_mapping.get(category_id, "Bilinmeyen Kategori")

                formatted_labels = [d.strftime('%d %b') for d in group['Date']]

                chart_data = {
                    'product_name': product_name,
                    'product_category': product_category,
                    'labels': formatted_labels,
                    'prices': group['Price'].tolist(),
                    'discount_prices': discount_prices,
                    'url': latest_url,
                    'highest_price': format_price(highest_price),
                    'lowest_price': format_price(lowest_price),
                    'lowest_discount_price': format_price(lowest_discount_price) if pd.notna(lowest_discount_price) else "N/A",
                    'highest_discount_price': format_price(highest_discount_price) if pd.notna(highest_discount_price) else "N/A",
                    'shop_logo': shop_logo
                }
                charts_data.append(chart_data)
        else:
            no_results = True
    else:
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
    return render_template("about.html")


@current_app.route('/test')
def test():
    """Renders a simple about page."""
    dummy = request.args.to_dict()
    print(dummy['shop_name'])
    #combine_and_deduplicate_csvs(base_downloads_path=Path(os.path.join('sepet_app', 'downloads', '2025-test', 'A101')))
    return "<h1>Test endpointine ulaştınız</h1>"