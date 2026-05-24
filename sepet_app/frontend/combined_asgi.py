import os
import sys
from pathlib import Path

# Add the project root and frontend directory to sys.path
# This ensures we can import mcp_server and the Django config
BASE_DIR = Path(__file__).resolve().parent # sepet_app/frontend
PROJECT_ROOT = BASE_DIR.parent.parent      # project root

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

from django.core.asgi import get_asgi_application
from starlette.applications import Starlette
from starlette.routing import Mount, Route
from starlette.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

# Import the mcp instance from our mcp_server.py
try:
    from mcp_server import mcp
except ImportError as e:
    print(f"Error importing mcp_server: {e}")
    # Try alternate import if needed
    try:
        import mcp_server
        mcp = mcp_server.mcp
    except Exception as e2:
        print(f"Failed again: {e2}")
        raise

# Initialize Django ASGI application
django_app = get_asgi_application()

# Get the Starlette app for MCP
# mcp.sse_app() returns a Starlette application with /sse and /messages routes
mcp_app = mcp.sse_app()

class SmitheryBotMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Access headers from scope directly to avoid consuming request body
            headers = dict(scope.get("headers", []))
            user_agent = headers.get(b"user-agent", b"").decode("utf-8", "ignore")
            if "SmitheryBot" in user_agent:
                # Logic for SmitheryBot can be added here
                pass
        
        await self.app(scope, receive, send)

# ... (rest of imports)

# 1. MCP Server Card
server_card_data = {
    "serverInfo": {
        "name": "Sepet Analizi API",
        "version": "1.0.0"
    },
    "authentication": {
        "required": False
    },
    "tools": [
        {
            "name": "search_market_products",
            "description": "Search for supermarket food prices in Turkey. Returns product price history, current prices, and discount information.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "product": {
                        "type": "string", 
                        "description": "The search term for the product (e.g., 'süt', 'peynir'). Must be 2-30 characters long containing only letters, numbers, and Turkish characters.",
                        "examples": ["süt", "peynir", "makarna"]
                    },
                    "category": {
                        "type": "string", 
                        "description": "The product category to filter by (e.g., 'Süt ve Süt Ürünleri'). Use 'all' for no category filter. Use 'get_available_categories' to see valid names.",
                        "default": "all"
                    },
                    "shops": {
                        "type": "array", 
                        "items": {"type": "string"}, 
                        "description": "List of specific shop names to filter by (e.g., ['Migros', 'A101']). Use 'get_available_shops' to see valid names.",
                        "examples": [["Migros", "A101"]]
                    },
                    "start_date": {
                        "type": "string", 
                        "description": "Start date for price history in YYYY-MM-DD format.",
                        "examples": ["2024-01-01"]
                    },
                    "end_date": {
                        "type": "string", 
                        "description": "End date for price history in YYYY-MM-DD format.",
                        "examples": ["2024-12-31"]
                    },
                    "page": {
                        "type": "integer", 
                        "description": "Page number for paginated results (20 items per page).",
                        "default": 1
                    }
                }
            },
            "outputSchema": {
                "type": "object",
                "properties": {
                    "results": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "shop_name": {"type": "string"},
                                "product_name": {"type": "string"},
                                "product_category": {"type": "string"},
                                "url": {"type": "string"},
                                "price_details": {
                                    "type": "object",
                                    "properties": {
                                        "start_price": {"type": "number"},
                                        "end_price": {"type": "number"},
                                        "min_price": {"type": "number"},
                                        "max_price": {"type": "number"}
                                    }
                                }
                            }
                        }
                    },
                    "currency": {"type": "string", "default": "TL"},
                    "source": {"type": "string", "default": "www.sepetanalizi.com"},
                    "date_range": {
                        "type": "object",
                        "properties": {
                            "start_date": {"type": "string"},
                            "end_date": {"type": "string"}
                        }
                    }
                }
            }
        },
        {
            "name": "get_available_shops",
            "description": "Get a list of all available Turkish supermarkets supported by the API. Use this to discover valid shop names for the 'shops' parameter.",
            "inputSchema": {"type": "object", "properties": {}},
            "outputSchema": {
                "type": "object",
                "properties": {
                    "shops": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                }
            }
        },
        {
            "name": "get_available_categories",
            "description": "Get a list of all available food categories supported by the API. Use this to discover valid category names for the 'category' parameter.",
            "inputSchema": {"type": "object", "properties": {}},
            "outputSchema": {
                "type": "object",
                "properties": {
                    "categories": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                }
            }
        }
    ],
    "endpoints": {
        "sse": "/mcp/sse"
    }
}

routes = [
    Route("/.well-known/mcp/server-card.json", endpoint=lambda _: JSONResponse(server_card_data)),
    Route("/mcp/server-card.json", endpoint=lambda _: JSONResponse(server_card_data)),
    # ... rest of routes
    # This signals to the scanner that we are reachable but have no specific OAuth config
    Route("/.well-known/oauth-authorization-server", endpoint=lambda _: JSONResponse(
        {"error": "not_supported"}, status_code=401
    )),
    Route("/.well-known/openid-configuration", endpoint=lambda _: JSONResponse(
        {"error": "not_supported"}, status_code=401
    )),
    Route("/.well-known/oauth-protected-resource", endpoint=lambda _: JSONResponse(
        {"error": "not_supported"}, status_code=401
    )),
    Route("/.well-known/oauth-protected-resource/mcp/sse", endpoint=lambda _: JSONResponse(
        {"error": "not_supported"}, status_code=401
    )),
    Mount("/mcp", app=mcp_app),
    Mount("/", app=django_app),
]

app = Starlette(routes=routes)

# Add Middlewares in order
app.add_middleware(SmitheryBotMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
