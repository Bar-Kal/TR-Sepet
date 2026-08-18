import os
from fastmcp import FastMCP
import httpx
from typing import List, Optional

# Initialize the MCP Server
mcp = FastMCP("Sepet Analizi API")

# Use environment variable for local testing, default to the production URL
API_BASE_URL = os.getenv("SEPET_API_URL", "https://www.sepetanalizi.com")

@mcp.tool()
async def search_market_products(
    product: Optional[str] = None, 
    category: str = "all", 
    shops: Optional[List[str]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = 1
) -> dict:
    """
    Search for supermarket food prices in Turkey.
    Returns product price history, current prices, and discount information.
    
    Args:
        product (string): The search term for the product (e.g., "süt", "peynir"). Must be 2-30 characters long containing only letters, numbers, and Turkish characters.
        category (string): The product category to filter by (e.g., "Süt ve Süt Ürünleri"). Leave as "all" for no category filter. Use the 'get_available_categories' tool to see all valid category names.
        shops (list of strings): List of specific shop names to filter by (e.g., ["Migros", "A101"]). Use the 'get_available_shops' tool to see all valid shop names. If omitted, default shops are used.
        start_date (string): Start date for the price history timeline in YYYY-MM-DD format (e.g., "2024-01-01").
        end_date (string): End date for the price history timeline in YYYY-MM-DD format.
        page (integer): Page number for paginated results. Default is 1.
    """
    params = {"category": category, "page": page}
    if product:
        params["q"] = product
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    
    # httpx handles lists in params differently; we append them
    # as multiple 'shops' keys to match request.GET.getlist('shops') in Django
    req_params = list(params.items())
    if shops:
        for shop in shops:
            req_params.append(("shops", shop))

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE_URL}/api/products", params=req_params)
        response.raise_for_status()
        return response.json()

@mcp.tool()
async def get_available_shops() -> dict:
    """
    Get a list of all available Turkish supermarkets supported by the API.
    Agents should use this tool first if they need to discover the exact spelling 
    of shop names to use in the 'shops' parameter of search_market_products.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE_URL}/api/shops")
        response.raise_for_status()
        return response.json()

@mcp.tool()
async def get_available_categories() -> dict:
    """
    Get a list of all available food categories supported by the API.
    Agents should use this tool first if they need to discover valid category 
    names to use in the 'category' parameter of search_market_products.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE_URL}/api/categories")
        response.raise_for_status()
        return response.json()

if __name__ == "__main__":
    # Standard stdio run for local debugging
    mcp.run()