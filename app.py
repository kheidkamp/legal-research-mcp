from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from mcp_server import mcp


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncExitStack() as stack:
        await stack.enter_async_context(mcp.session_manager.run())
        yield


app = FastAPI(title="Legal Research MCP", version="0.1.0-dev", lifespan=lifespan)


@app.get("/health")
async def health():
    return JSONResponse({"status": "healthy", "service": "legal-research-mcp", "version": "0.1.0-dev"})


# Mount after the health route so Container Apps probes do not hit the MCP JSON-RPC endpoint.
app.mount("/", mcp.streamable_http_app())
