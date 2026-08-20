from __future__ import annotations

import hashlib
import re
import uuid
from datetime import date, datetime, timezone
from typing import Any

from . import __version__


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def today_iso() -> str:
    return date.today().isoformat()


def sha256_text(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text).strip()
    return "sha256:" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:24]
    return f"{prefix}_{digest}"


def envelope(status: str, data: dict[str, Any], warnings: list[str] | None = None) -> dict[str, Any]:
    return {
        "request_id": str(uuid.uuid4()),
        "status": status,
        "retrieved_at": now_iso(),
        "tool_version": __version__,
        "warnings": warnings or [],
        "data": data,
    }
