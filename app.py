from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from legal_mcp import __version__
from legal_mcp.sr03_diagnostics import run_sr03_startup_diagnostics
from mcp_server import mcp


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Temporary SR03 diagnostic build: exercise the deployed retrieval-security
    # implementation before accepting requests. The diagnostics are deterministic
    # and issue zero external network calls.
    diagnostic = await run_sr03_startup_diagnostics()
    app.state.sr03_diagnostic = diagnostic
    if diagnostic.get("overall") != "PASS":
        raise RuntimeError("SR03 startup retrieval-security diagnostic failed closed")

    async with AsyncExitStack() as stack:
        await stack.enter_async_context(mcp.session_manager.run())
        yield


app = FastAPI(title="Legal Research MCP", version=__version__, lifespan=lifespan)


@app.get("/health")
async def health():
    return JSONResponse({"status": "healthy", "service": "legal-research-mcp", "version": __version__, "sr03_diagnostic_build": "diag1"})


@app.get("/sr03/diagnostics")
async def sr03_diagnostics():
    return JSONResponse(app.state.sr03_diagnostic)


# Mount after the HTTP diagnostic routes so they do not hit the MCP JSON-RPC endpoint.
app.mount("/", mcp.streamable_http_app())
