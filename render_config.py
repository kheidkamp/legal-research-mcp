from __future__ import annotations

import os
from urllib.parse import urlparse


def _hostname(value: str | None) -> str | None:
    if not value:
        return None
    candidate = value.strip()
    if not candidate:
        return None
    if "://" in candidate:
        candidate = urlparse(candidate).hostname or ""
    else:
        candidate = candidate.split("/", 1)[0].split(":", 1)[0]
    candidate = candidate.strip().lower()
    return candidate or None


def build_transport_allowlists() -> tuple[list[str], list[str]]:
    """Build a fail-closed Host/Origin allowlist for local and Render deployment."""
    hosts = ["localhost:*", "127.0.0.1:*", "[::1]:*"]
    origins = ["http://localhost:*", "http://127.0.0.1:*", "http://[::1]:*"]

    seen: set[str] = set()
    for raw in (
        os.getenv("RENDER_EXTERNAL_HOSTNAME"),
        os.getenv("MCP_PUBLIC_HOSTNAME"),
    ):
        host = _hostname(raw)
        if not host or host in seen:
            continue
        seen.add(host)
        hosts.extend([host, f"{host}:*"])
        origins.extend([f"https://{host}", f"https://{host}:*"])

    return hosts, origins
