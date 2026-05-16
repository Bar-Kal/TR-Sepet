import os
import sqlite3
import re
from datetime import datetime, timedelta
from collections import defaultdict
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.urls import reverse
from werkzeug.utils import secure_filename
from .utils import (
    get_db_path, get_shop_names, get_food_categories, regexp,
    get_turkish_regex_pattern, unzip_new_db_file, calculate_price_change, format_price
)

PER_PAGE = 20

def _get_product_data(request):
    """Internal helper to fetch product data based on request parameters."""
    charts_data = []
    table_data = []
    no_results = True
    search_error = None
    pagination = None
    page_obj = []
    
    db_path = get_db_path()
    shop_names, shop_logo_mapping = get_shop_names()
    available_food_categories = get_food_categories()

    selected_shops = request.GET.getlist('shops')
    selected_category_name = request.GET.get('category', 'all')
    date_range_param = request.GET.get('date_range')
    start_date_param = request.GET.get('start_date')
    end_date_param = request.GET.get('end_date')

    if not selected_shops:
        selected_shops = ['Carrefoursa']

    if start_date_param and end_date_param:
        start_date_str = start_date_param
        end_date_str = end_date_param
    elif date_range_param:
        try:
            start_date_str, end_date_str = date_range_param.split(' - ')
        except ValueError:
            start_date_str = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
            end_date_str = datetime.now().strftime('%Y-%m-%d')
    else:
        start_date_str = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        end_date_str = datetime.now().strftime('%Y-%m-%d')

    page_num = request.GET.get('page', 1)
    product_search = request.GET.get('q')

    if product_search is not None:
        if not product_search.strip():
            product_search = None
            search_error = "Lütfen bir arama terimi girin."
        else:
            pattern = r"^[a-zA-Z0-9çÇğĞıİöÖşŞüÜ\s]{2,30}$"
            if not re.match(pattern, product_search) or not (2 <= len(product_search) <= 30):
                product_search = None
                search_error = "Arama çubuğuna sadece harf, rakam ve Türkçe karakterler girebilirsiniz. En az 2, en fazla 30 karakter olmalıdır."

    if db_path:
        all_matching_groups = []
        
        # Step 1: Discovery - Find unique products matching filters
        try:
            con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            con.create_function("REGEXP", 2, regexp)
            cursor = con.cursor()
            
            for current_shop in selected_shops:
                query = (f'SELECT DISTINCT {current_shop}.Display_Name, shops_metadata.shop_name as Shop_Name '
                         f'FROM "{current_shop}" '
                         f'LEFT JOIN shops_metadata ON {current_shop}.Shop_ID = shops_metadata.shop_id '
                         f'LEFT JOIN food_categories_metadata ON {current_shop}.Product_ID = food_categories_metadata.product_id')
                
                params = []
                conditions = ["food = 1"]

                if start_date_str and end_date_str:
                    conditions.append("date(Scrape_Timestamp) BETWEEN ? AND ?")
                    params.extend([start_date_str, end_date_str])

                if selected_category_name != 'all':
                    conditions.append("food_categories_metadata.TurkishName = ?")
                    params.append(selected_category_name)

                if product_search:
                    tr_pattern = get_turkish_regex_pattern(product_search)
                    if ' ' in product_search:
                        conditions.append(f"{current_shop}.Display_Name REGEXP ?")
                        params.append(tr_pattern)
                    else:
                        conditions.append(f"{current_shop}.Display_Name REGEXP ?")
                        params.append(rf'(^|\s){tr_pattern}')

                if conditions:
                    query += " WHERE " + " AND ".join(conditions)

                cursor.execute(query, params)
                rows = cursor.fetchall()
                for row in rows:
                    all_matching_groups.append({'display_name': row[0], 'shop_name': row[1], 'table_name': current_shop})
            
            con.close()
        except sqlite3.Error as e:
            print(f"Discovery query failed: {e}")

        if all_matching_groups:
            all_matching_groups.sort(key=lambda x: (x['display_name'], x['shop_name']))
            
            paginator = Paginator(all_matching_groups, PER_PAGE)
            try:
                page_obj = paginator.page(page_num)
            except PageNotAnInteger:
                page_obj = paginator.page(1)
            except EmptyPage:
                page_obj = paginator.page(paginator.num_pages)

            pagination = {
                'page': page_obj.number,
                'total_pages': paginator.num_pages,
                'total_items': paginator.count,
                'has_prev': page_obj.has_previous(),
                'has_next': page_obj.has_next(),
                'page_range': list(range(max(1, page_obj.number - 2), min(paginator.num_pages, page_obj.number + 2) + 1)),
                'start': max(1, page_obj.number - 2),
                'end': min(paginator.num_pages, page_obj.number + 2)
            }

            # Step 2: Batch Fetch Detail Data
            # Group paginated items by table name to minimize queries
            items_by_table = defaultdict(list)
            for item in page_obj:
                items_by_table[item['table_name']].append(item['display_name'])

            # Dictionary to store results for sorting them back into page order
            detail_results = {}

            try:
                con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
                con.row_factory = sqlite3.Row
                cursor = con.cursor()

                for table_name, display_names in items_by_table.items():
                    placeholders = ', '.join(['?'] * len(display_names))
                    query = (f'SELECT {table_name}.Scrape_Timestamp, {table_name}.Display_Name, {table_name}.Discount_Price, {table_name}.Price, '
                             f'shops_metadata.shop_name as Shop_Name, '
                             f'food_categories_metadata.TurkishName as Product_Name, food_categories_metadata.TurkishCategory as Category_Name, '
                             f'shops_metadata.base_url || {table_name}.URL as Product_URL FROM "{table_name}" '
                             f'LEFT JOIN shops_metadata ON {table_name}.Shop_ID = shops_metadata.shop_id '
                             f'LEFT JOIN food_categories_metadata ON {table_name}.Product_ID = food_categories_metadata.product_id '
                             f'WHERE {table_name}.Display_Name IN ({placeholders}) AND food = 1')
                    
                    params = list(display_names)
                    if start_date_str and end_date_str:
                        query += " AND date(Scrape_Timestamp) BETWEEN ? AND ?"
                        params.extend([start_date_str, end_date_str])
                    
                    query += " ORDER BY Scrape_Timestamp"
                    
                    cursor.execute(query, params)
                    rows = cursor.fetchall()
                    
                    # Group rows by product name within this table
                    table_product_groups = defaultdict(list)
                    for r in rows:
                        table_product_groups[r['Display_Name']].append(dict(r))
                    
                    for d_name, group in table_product_groups.items():
                        detail_results[(d_name, table_name)] = group

                con.close()
            except sqlite3.Error as e:
                print(f"Batch detail query failed: {e}")

            # Step 3: Process the results in the correct page order
            for item in page_obj:
                group_rows = detail_results.get((item['display_name'], item['table_name']))
                if not group_rows:
                    continue

                prices, discount_prices, dates = [], [], []
                for row in group_rows:
                    prices.append(float(row['Price']) if row['Price'] is not None else None)
                    discount_prices.append(float(row['Discount_Price']) if row['Discount_Price'] is not None else None)
                    dates.append(datetime.strptime(row['Scrape_Timestamp'], '%Y-%m-%d %H:%M:%S'))

                valid_prices = [p for p in prices if p is not None]
                if not valid_prices: continue
                valid_discount_prices = [p for p in discount_prices if p is not None]

                # Find dates for min/max prices
                min_p = min(valid_prices)
                max_p = max(valid_prices)
                min_price_date = dates[prices.index(min_p)].strftime('%Y-%m-%d')
                max_price_date = dates[prices.index(max_p)].strftime('%Y-%m-%d')

                if valid_discount_prices:
                    min_d = min(valid_discount_prices)
                    max_d = max(valid_discount_prices)
                    min_discount_date = dates[discount_prices.index(min_d)].strftime('%Y-%m-%d')
                    max_discount_date = dates[discount_prices.index(max_d)].strftime('%Y-%m-%d')
                else:
                    min_d = max_d = min_discount_date = max_discount_date = None

                charts_data.append({
                    'product_name': item['display_name'],
                    'product_category': group_rows[0]['Category_Name'],
                    'search_term': group_rows[0]['Product_Name'],
                    'labels': [d.strftime('%d %b') for d in dates],
                    'prices': prices,
                    'discount_prices': discount_prices,
                    'url': group_rows[-1]['Product_URL'],
                    'highest_price': format_price(max_p),
                    'lowest_price': format_price(min_p),
                    'lowest_discount_price': format_price(min_d) if min_d is not None else "N/A",
                    'highest_discount_price': format_price(max_d) if max_d is not None else "N/A",
                    'shop_logo': shop_logo_mapping.get(item['shop_name'], '')
                })

                table_data.append({
                    'shop_name': item['shop_name'],
                    'product_name': item['display_name'],
                    'product_category': group_rows[0]['Category_Name'],
                    'price_details': {
                        'start_price': prices[0],
                        'end_price': prices[-1],
                        'min_price': min_p,
                        'max_price': max_p,
                    },
                    'discount_details': {
                        'start_price': discount_prices[0],
                        'end_price': discount_prices[-1],
                        'min_price': min_d,
                        'max_price': max_d,
                    },
                    'dates': {
                        'start_date': dates[0].strftime('%Y-%m-%d'),
                        'end_date': dates[-1].strftime('%Y-%m-%d'),
                        'min_price_date': min_price_date,
                        'max_price_date': max_price_date,
                        'min_discount_price_date': min_discount_date,
                        'max_discount_price_date': max_discount_date,
                    },
                    'price_change': calculate_price_change(prices),
                    'discount_price_change': calculate_price_change(valid_discount_prices),
                    'url': group_rows[-1]['Product_URL'],
                    # Helper for template display
                    'display_price': f"{format_price(prices[0])} - {format_price(prices[-1])}" if len(prices) > 1 else format_price(prices[0]),
                    'display_discount_price': f"{format_price(discount_prices[0])} - {format_price(discount_prices[-1])}" if len(discount_prices) > 1 else format_price(discount_prices[0]),
                })

            if charts_data:
                no_results = False

    # Meta and Sidebar Data
    if product_search and db_path and not search_error:
        try:
            con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            cursor = con.cursor()
            categories = set()
            for current_shop in selected_shops:
                cursor.execute(f'SELECT DISTINCT food_categories_metadata.TurkishName FROM "{current_shop}" '
                               f'LEFT JOIN food_categories_metadata ON {current_shop}.Product_ID = food_categories_metadata.product_id '
                               f'WHERE {current_shop}.Display_Name REGEXP ? AND food = 1', [get_turkish_regex_pattern(product_search)])
                categories.update([r[0] for r in cursor.fetchall() if r[0]])
            available_food_categories = sorted(list(categories))
            con.close()
        except: pass

    return {
        'charts_data': charts_data,
        'table_data': table_data,
        'no_results': no_results,
        'search_error': search_error,
        'pagination': pagination,
        'shop_names': shop_names,
        'shop_logo_mapping': shop_logo_mapping,
        'available_food_categories': available_food_categories,
        'product_search': product_search,
        'selected_shops': selected_shops,
        'selected_category_name': selected_category_name,
        'start_date_str': start_date_str,
        'end_date_str': end_date_str,
        'db_path': db_path
    }

def index(request):
    """Renders the landing page."""
    context = {
        'title': 'Ara',
        'search_query': '',
        'show_header_search': True,
        'meta_description': "Türkiye'deki süpermarketlerin gıda fiyatlarını karşılaştırın. En uygun fiyatlı ürünleri bulun ve bütçenizi koruyun."
    }
    return render(request, 'index.html', context)

def products(request):
    """Renders the home page with shop and category dropdowns."""
    data = _get_product_data(request)
    
    meta_description = f"'{data['product_search']}' için market fiyatları" if data['product_search'] else "Market gıda fiyat analizi."
    shops_list = [{'name': s, 'logo': data['shop_logo_mapping'].get(s, ''), 'selected': s in data['selected_shops']} for s in data['shop_names']]
    
    q_dict = request.GET.copy()
    q_dict.pop('page', None)
    pagination_base_url = f"{request.path}?{q_dict.urlencode()}&page=" if q_dict else f"{request.path}?page="

    context = {
        'title': f"{data['product_search'] or 'Ürünler'} - Fiyat Analizi",
        'shops': shops_list,
        'food_categories': data['available_food_categories'],
        'charts_data': data['charts_data'],
        'category_name': data['selected_category_name'],
        'selected_shops': data['selected_shops'],
        'start_date': data['start_date_str'],
        'end_date': data['end_date_str'],
        'results_title': 'Fiyat Analizi',
        'no_results': data['no_results'],
        'product_search': data['product_search'] or '',
        'search_query': data['product_search'] or '',
        'search_error': data['search_error'],
        'show_header_search': True,
        'pagination': data['pagination'],
        'pagination_base_url': pagination_base_url,
        'table_data': data['table_data'],
        'meta_description': meta_description
    }
    return render(request, 'products.html', context)

def api_products(request):
    """API endpoint that returns product data in JSON format."""
    data = _get_product_data(request)
    
    # Clean up results for the API response
    api_results = []
    for row in data['table_data']:
        # Create a copy and remove display/formatting fields
        api_item = {k: v for k, v in row.items() if k not in ['display_price', 'display_discount_price']}
        
        # Flatten and clean price_change
        if 'price_change' in api_item:
            pc = api_item['price_change']
            api_item['price_change'] = {
                'price': pc.get('price'),
                'percentage': pc.get('percentage')
            }
            
        # Flatten and clean discount_price_change
        if 'discount_price_change' in api_item:
            dpc = api_item['discount_price_change']
            api_item['discount_price_change'] = {
                'price': dpc.get('price'),
                'percentage': dpc.get('percentage')
            }

        api_results.append(api_item)

    return JsonResponse({
        'results': api_results,
        'source': 'sepetanalizi.com',
        'currency': 'TL',
        'date_range': {
            'start_date': data['start_date_str'],
            'end_date': data['end_date_str']
        },
        'search_error': data['search_error']
    })

def api_shops(request):
    """API endpoint that returns a list of all available shop names."""
    shop_names, _ = get_shop_names()
    return JsonResponse({
        'shops': shop_names
    })

def about(request): return render(request, 'about.html', {'title': 'Hakkında'})
def privacy(request):
    return render(request, 'privacy.html', {'title': 'Gizlilik Politikası', 'contact_email': os.getenv('CONTACT_EMAIL', 'default@example.com')})

@csrf_exempt
def upload_secure(request):
    if request.method != 'POST' or request.POST.get('secret_key') != settings.UPLOAD_SECRET_KEY:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    file = request.FILES.get('file')
    if file:
        filename = secure_filename(file.name)
        os.makedirs(settings.DATABASE_FOLDER, exist_ok=True)
        file_path = os.path.join(settings.DATABASE_FOLDER, filename)
        with open(file_path, 'wb+') as dest:
            for chunk in file.chunks(): dest.write(chunk)
        unzip_new_db_file()
        return JsonResponse({'message': 'Success'}, status=200)
    return JsonResponse({'error': 'Failed'}, status=400)

def robots_txt(request):
    content = (
        "User-agent: *\n"
        "Disallow: /.idea/\n"
        "Disallow: /.git/\n"
        "Disallow: /__pycache__/\n"
        "Disallow: /sepet_app/scraper/downloads/\n\n"
        "Sitemap: /sitemap.xml"
    )
    return HttpResponse(content, content_type="text/plain")

def sitemap(request):
    today = datetime.now().strftime('%Y-%m-%d')
    pages = [[f"https://www.sepetanalizi.com{reverse(n)}", today] for n in ['index', 'about', 'privacy', 'products']]
    return render(request, 'sitemap_template.xml', {'pages': pages}, content_type='application/xml')

def custom_404(request, exception=None): return render(request, '404.html', status=404)
