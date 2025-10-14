# TR-Sepet

This document explains how to run the scraper and how to extend it by adding new e-commerce websites.

## Configuration

The application's behavior is controlled by two files in the `sepet_app/configs/` directory.

### 1. `shops.json`
This file lists the websites to be scraped. To add or remove a shop, you edit this file. Each shop requires:
- `shop_name`: A unique name for the shop.
- `base_url`: The website's home page URL.
- `scraper_module`: The full Python path to the file containing the scraper's logic (e.g., `sepet_app.scrapers.migros`).
- `scraper_class`: The name of the scraper class inside that file (e.g., `MigrosScraper`).

**Example `shops.json`:**

### 2. `food.csv`
A simple CSV file listing the product categories to search for on each website. The scraper reads the `Turkish_names` column.

**Example `food.csv`:**

## How to Run the Scraper

To ensure all modules are found correctly, you **must** run the application from the project's root directory (`TR-Sepet/`) using the `-m` flag.

This command correctly sets up the Python path, allowing the factory to dynamically import the scraper modules defined in `shops.json`.

## How to Add a New Scraper

Adding a new website is a simple three-step process that does not require changing the main application logic.

#### Step 1: Create the Scraper File
Create a new Python file in the `sepet_app/scrapers/` directory. For example, `sok.py`.

#### Step 2: Implement the Scraper Class
In your new file (`sok.py`), create a class that inherits from `BaseScraper` and implements the required `search` method. This method will contain the unique scraping logic for the new website.

#### Step 3: Update `shops.json`
Add a new entry for your scraper in the `sepet_app/configs/shops.json` file.
