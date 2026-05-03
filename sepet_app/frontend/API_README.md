# Sepet API Documentation 🛒

The Sepet API allows you to query the grocery price database directly. It returns structured JSON data containing product details, price history, and store links.

## Base URL
- **Products:** `/api/products`
- **Shops:** `/api/shops`

## Endpoints

### 1. Products API (`/api/products`)
Allows querying the product database with filters.

### 2. Shops API (`/api/shops`)
Returns a list of all available shop names in the database. Useful for discovery before filtering products.

#### Example Request
`GET /api/shops`

#### Example Response
```json
{
  "shops": ["A101", "Carrefoursa", "Migros", "Onur Market", "Tk Koop Market"]
}
```

## Query Parameters (Products API)

| Parameter | Description | Example |
| :--- | :--- | :--- |
| `q` | Search keyword (min 2 chars). | `?q=sut` |
| `shops` | Filter by shop name (can be used multiple times). | `?shops=Migros&shops=A101` |
| `category` | Filter by specific category. | `?category=Peynir` |
| `start_date` | Start of date range (YYYY-MM-DD). | `?start_date=2026-01-01` |
| `end_date` | End of date range (YYYY-MM-DD). | `?end_date=2026-03-01` |
| `page` | Pagination page number. | `?page=2` |

*Note: If no date range is provided, the API defaults to the last 90 days.*

## Example Requests

### 1. Simple Keyword Search
Get the latest prices for milk across all stores.
`GET /api/products?q=sut`

### 2. Specific Stores & Date Range
Find tea prices in Migros and Carrefoursa for a specific month.
`GET /api/products?q=cay&shops=Migros&shops=Carrefoursa&start_date=2026-01-01&end_date=2026-01-31`

### 3. Category Search
Get all products in the "Zeytinyağı" category.
`GET /api/products?category=Zeytinyağı`

## Response Structure

```json
{
  "results": [
    {
      "shop_name": "Migros",
      "product_name": "Tam Yağlı Süt 1L",
      "product_category": "Süt",
      "url": "https://www.migros.com.tr/...",
      "dates": {
        "start_date": "2026-02-01",
        "end_date": "2026-04-30",
        "min_price_date": "2026-02-05",
        "max_price_date": "2026-04-30",
        "min_discount_price_date": "2026-03-15",
        "max_discount_price_date": "2026-04-30"
      },
      "price_details": {
        "start_price": 32.50,
        "end_price": 35.00,
        "min_price": 32.50,
        "max_price": 35.00
      },
      "discount_details": {
        "start_price": 29.90,
        "end_price": 32.00,
        "min_price": 28.50,
        "max_price": 32.00
      },
      "price_change": {
        "price": 2.50,
        "percentage": 7.69
      },
      "discount_price_change": {
        "price": 2.10,
        "percentage": 7.02
      }
    }
  ],
  "currency": "TL",
  "date_range": {
    "start_date": "2026-02-04",
    "end_date": "2026-05-04"
  },
  "search_error": null
}
```
