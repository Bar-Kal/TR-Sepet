import os
from flask import render_template, current_app, redirect, request
from datetime import datetime, timedelta
import pandas as pd
from pathlib import Path
import random

# By using current_app, we access the application instance created by the factory.
# This is a clean way to access the app without circular imports.
import json
import locale

try:
    locale.setlocale(locale.LC_TIME, 'tr_TR.UTF-8')
except locale.Error:
    print("Turkish locale not supported, using default.")

def format_price(price):
    return f'{f"{price:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")} TL'

@current_app.route('/', methods=['GET', 'POST'])
@current_app.route('/index', methods=['GET', 'POST'])
def index():
    """Renders the home page with shop and category dropdowns."""
    # Load shop names from shops.json
    shops_path = Path(current_app.root_path) / 'configs' / 'shops.json'
    with open(shops_path, 'r', encoding='utf-8') as f:
        shops_data = json.load(f)
    shop_names = [shop['shop_name'] for shop in shops_data]
    shop_names.sort()

    # Load food categories from food.csv
    food_path = Path(current_app.root_path) / 'configs' / 'food.json'
    with open(food_path, 'r', encoding='utf-8') as f:
        food_file = pd.read_json(f)
        food_categories = food_file['TurkishName'].tolist()
    food_categories.sort()

    charts_data = None
    shop_name = None
    category_name = None
    start_date_str = None
    end_date_str = None

    if request.method == 'POST':
        shop_name = request.form.get('shop')
        category_name = request.form.get('category')
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
    else: # GET request
        shop_name = random.choice(shop_names)
        category_name = random.choice(food_categories)

    # Fetch and process data
    downloads_path = Path(current_app.root_path) / 'downloads' / shop_name
    all_data = []

    if downloads_path.exists():
        # Use glob to find all combined.csv files recursively
        for data_file in downloads_path.glob('**/combined.csv'):
            df = pd.read_csv(data_file, delimiter=';')
            df['Date'] = pd.to_datetime(df['Scrape_Timestamp']).dt.date
            all_data.append(df)

    results_title = f"Price Analysis for {category_name} from {shop_name}"
    no_results = False

    if all_data:
        full_df = pd.concat(all_data, ignore_index=True)

        if start_date_str and end_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            full_df = full_df[(full_df['Date'] >= start_date) & (full_df['Date'] <= end_date)]
        else:
            # Default to last 7 days
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=7)
            full_df = full_df[(full_df['Date'] >= start_date) & (full_df['Date'] <= end_date)]
            start_date_str = start_date.strftime('%Y-%m-%d')
            end_date_str = end_date.strftime('%Y-%m-%d')
        
        product_df = full_df[full_df['Search_Term'] == category_name]

        if not product_df.empty:
            # Group by product name and create a list of chart data
            charts_data = []
            for product_name, group in product_df.groupby('Display_Name'):
                group = group.sort_values('Date')
                latest_url = group['URL'].iloc[-1]
                highest_price = group['Price'].max()
                lowest_price = group['Price'].min()
                current_cheapest_price = group['Price'].iloc[-1]

                # Ensure 'Date' is datetime before formatting
                group['Date'] = pd.to_datetime(group['Date'])
                # Format dates to 'd MMM' (e.g., '5 Eki') using the set locale
                formatted_labels = [d.strftime('%d %b') for d in group['Date']]

                chart_data = {
                    'product_name': product_name,
                    'labels': formatted_labels,
                    'prices': group['Price'].tolist(),
                    'url': latest_url,
                    'highest_price': format_price(highest_price),
                    'lowest_price': format_price(lowest_price),
                    'current_cheapest_price': format_price(current_cheapest_price)
                }
                charts_data.append(chart_data)
        else:
            no_results = True
    else:
        no_results = True

    return render_template('index.html',
                           title='Home',
                           shop_names=shop_names,
                           food_categories=food_categories,
                           charts_data=charts_data,
                           category_name=category_name,
                           shop_name=shop_name,
                           start_date=start_date_str,
                           end_date=end_date_str,
                           results_title=results_title,
                           no_results=no_results)


@current_app.route('/about')
def about():
    """Renders a simple about page."""
    return "<h1>About This Application</h1>"


@current_app.route('/test')
def test():
    """Renders a simple about page."""
    dummy = request.args.to_dict()
    print(dummy['shop_name'])
    #combine_and_deduplicate_csvs(base_downloads_path=Path(os.path.join('sepet_app', 'downloads', '2025-test', 'A101')))
    return "<h1>You reached the Test endpoint</h1>"