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
from starlette.middleware.base import BaseHTTPMiddleware

class SmitheryBotMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # If it's SmitheryBot, we want to ensure we don't block them 
        # with strict Host or Origin checks at the Starlette level
        user_agent = request.headers.get("user-agent", "")
        if "SmitheryBot" in user_agent:
            # We can modify the scope or headers here if needed
            pass
        return await call_next(request)

# ... (rest of imports)

# Create the Starlette application with discovery routes
routes = [
    # 1. MCP Server Card
    Route("/.well-known/mcp/server-card.json", endpoint=lambda _: JSONResponse({
        "name": "Sepet Analizi API",
        "version": "1.0.0",
        "description": "Turkish supermarket price analysis API",
        "endpoints": {
            "sse": "/mcp/sse"
        }
    })),
    # 2. OAuth Discovery (Returning 401 as per Smithery's tip for 'unauthenticated')
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
    Route("/mcp/server-card.json", endpoint=lambda _: JSONResponse({
        "name": "Sepet Analizi API",
        "version": "1.0.0",
        "description": "Turkish supermarket price analysis API",
        "endpoints": {
            "sse": "/mcp/sse"
        }
    })),
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
