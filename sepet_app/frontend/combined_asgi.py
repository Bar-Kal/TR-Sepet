import os
import sys
from pathlib import Path

# Add the project root and frontend directory to sys.path
# This ensures we can import mcp_server and the Django config
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(PROJECT_ROOT))
sys.path.append(str(PROJECT_ROOT / "sepet_app" / "frontend"))

from django.core.asgi import get_asgi_application
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from mcp.server.sse import SseServerTransport

# Set Django settings module before importing anything that needs it
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Import the mcp instance from our mcp_server.py
try:
    from mcp_server import mcp
except ImportError as e:
    print(f"Error importing mcp_server: {e}")
    raise

# Initialize Django ASGI application
django_app = get_asgi_application()

# Setup MCP SSE Transport
# Clients will connect to /mcp/sse and send messages to /mcp/messages/
sse = SseServerTransport("/mcp/messages/")

async def handle_sse(request):
    """
    Handle the SSE connection for MCP.
    """
    async with sse.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await mcp.run_async(
            streams[0], # read_stream
            streams[1], # write_stream
            mcp.create_initialization_options()
        )

# Create the combined application
# We mount the MCP routes first, then fall back to Django for everything else
app = Starlette(
    routes=[
        Route("/mcp/sse", endpoint=handle_sse),
        Mount("/mcp/messages/", app=sse.handle_post_message),
        Mount("/", app=django_app),
    ]
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
