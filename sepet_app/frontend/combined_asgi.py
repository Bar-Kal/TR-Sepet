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
from starlette.routing import Mount

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

# Create the combined application
# We mount the MCP routes first, then fall back to Django for everything else
app = Starlette(
    routes=[
        # Mounting mcp_app at /mcp will result in:
        # /mcp/sse
        # /mcp/messages
        Mount("/mcp", app=mcp_app),
        Mount("/", app=django_app),
    ]
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
