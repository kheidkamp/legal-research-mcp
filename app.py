from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from legal_mcp import __version__
from mcp_server import mcp


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncExitStack() as stack:
        await stack.enter_async_context(mcp.session_manager.run())
        yield


app = FastAPI(title="Legal Research MCP", version=__version__, lifespan=lifespan)


@app.get("/health")
async def health():
    return JSONResponse({"status": "healthy", "service": "legal-research-mcp", "version": __version__})


# Mount after the health route so Render probes do not hit the MCP JSON-RPC endpoint.
app.mount("/", mcp.streamable_http_app())
