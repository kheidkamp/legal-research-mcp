from __future__ import annotations

from unittest.mock import patch

import httpx

from .network_security import assert_public_dns_for_url
from .official_documents import (
    OfficialDocumentAdapter,
    OfficialDocumentTooLarge,
    OfficialDocumentUnavailable,
    UnsafeOfficialDocumentUrl,
    UnsupportedOfficialDocument,
)


def _public_dns_noop(*args, **kwargs):
    return ("93.184.216.34",)


def _record(results: list[dict], case_id: str, control: str, passed: bool, detail: str) -> None:
    results.append(
        {
            "case_id": case_id,
            "control": control,
            "status": "PASS" if passed else "FAIL",
            "detail": detail,
        }
    )


async def run_sr03_startup_diagnostics() -> dict:
    """Run deterministic, zero-network retrieval-security diagnostics.

    This diagnostic harness is for the temporary SR03 DEV build only. It exercises
    the deployed 0.3.4 retrieval implementation with httpx.MockTransport or pure
    resolver injection. No external network request is issued by these diagnostics.
    The app runs this function before the ASGI server begins accepting requests.
    """

    results: list[dict] = []

    # SR03-LR04: an allowlisted starting URL may not redirect to a foreign host.
    def redirect_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            302,
            headers={"location": "https://example.com/secret"},
            request=request,
        )

    redirect_adapter = OfficialDocumentAdapter(transport=httpx.MockTransport(redirect_handler))
    redirect_pass = False
    redirect_detail = "foreign-host redirect was not rejected"
    with patch("legal_mcp.official_documents.assert_public_dns_for_url", _public_dns_noop):
        try:
            await redirect_adapter._fetch_bytes("https://dserver.bundestag.de/brd/2026/0005-26.pdf")
        except UnsafeOfficialDocumentUrl:
            redirect_pass = True
            redirect_detail = "foreign-host redirect rejected before follow"
    _record(results, "SR03-LR04", "SEC-RES-004", redirect_pass, redirect_detail)

    # SR03-LR05: an allowlisted hostname resolving to link-local/private space is blocked.
    def private_resolver(host, port, type=None):
        return [(2, 1, 6, "", ("169.254.169.254", port))]

    ssrf_pass = False
    ssrf_detail = "private/link-local DNS resolution was not rejected"
    try:
        assert_public_dns_for_url(
            "https://dserver.bundestag.de/brd/2026/0005-26.pdf",
            resolver=private_resolver,
            error_cls=UnsafeOfficialDocumentUrl,
            label="official-document",
        )
    except UnsafeOfficialDocumentUrl:
        ssrf_pass = True
        ssrf_detail = "link-local/private DNS resolution rejected"
    _record(results, "SR03-LR05", "SEC-RES-005", ssrf_pass, ssrf_detail)

    # SR03-LR06: response-size limit is enforced before payload processing.
    def size_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/html", "content-length": "11"},
            content=b"hello world",
            request=request,
        )

    size_adapter = OfficialDocumentAdapter(max_bytes=10, transport=httpx.MockTransport(size_handler))
    size_pass = False
    size_detail = "oversized response was not rejected"
    with patch("legal_mcp.official_documents.assert_public_dns_for_url", _public_dns_noop):
        try:
            await size_adapter._fetch_bytes("https://www.recht.bund.de/test")
        except OfficialDocumentTooLarge:
            size_pass = True
            size_detail = "response exceeding max_bytes rejected"
    _record(results, "SR03-LR06", "SEC-RES-006", size_pass, size_detail)

    # SR03-LR07: transport timeout fails closed.
    def timeout_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("SR03 deterministic timeout", request=request)

    timeout_adapter = OfficialDocumentAdapter(transport=httpx.MockTransport(timeout_handler))
    timeout_pass = False
    timeout_detail = "timeout did not fail closed"
    with patch("legal_mcp.official_documents.assert_public_dns_for_url", _public_dns_noop):
        try:
            await timeout_adapter._fetch_bytes("https://www.recht.bund.de/test")
        except OfficialDocumentUnavailable:
            timeout_pass = True
            timeout_detail = "read timeout converted to fail-closed unavailable result"
    _record(results, "SR03-LR07", "SEC-RES-007", timeout_pass, timeout_detail)

    # SR03-LR08: executable/unexpected content types are rejected.
    def content_type_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "application/javascript"},
            content=b"alert('SR03_FAIL_JS')",
            request=request,
        )

    content_adapter = OfficialDocumentAdapter(transport=httpx.MockTransport(content_type_handler))
    content_pass = False
    content_detail = "application/javascript was not rejected"
    with patch("legal_mcp.official_documents.assert_public_dns_for_url", _public_dns_noop):
        try:
            await content_adapter._fetch_bytes("https://www.recht.bund.de/test")
        except UnsupportedOfficialDocument:
            content_pass = True
            content_detail = "application/javascript content type rejected"
    _record(results, "SR03-LR08", "SEC-RES-008", content_pass, content_detail)

    # SR03-LR09: script nodes are removed from HTML extraction and never surfaced.
    safe_marker = "SR03_SAFE_VISIBLE_TEXT"
    script_marker = "SR03_FAIL_SCRIPT_SURFACED"
    parsed = OfficialDocumentAdapter.parse_html(
        (
            "<html><head><title>SR03</title></head><body><main>"
            + safe_marker
            + "<script>"
            + script_marker
            + "</script></main></body></html>"
        ).encode("utf-8"),
        "https://www.recht.bund.de/test",
        "text/html",
    )
    visible_text = " ".join(parsed.pages)
    script_pass = safe_marker in visible_text and script_marker not in visible_text
    script_detail = (
        "visible source text preserved while script-node content removed"
        if script_pass
        else "script-node content was surfaced or visible text was lost"
    )
    _record(results, "SR03-LR09", "SEC-RES-009", script_pass, script_detail)

    passed = sum(1 for item in results if item["status"] == "PASS")
    failed = len(results) - passed
    return {
        "diagnostic": "SR03_RESEARCH_EXTERNAL_RETRIEVAL_SECURITY",
        "mode": "DETERMINISTIC_STARTUP_SELFTEST",
        "external_network_calls": 0,
        "mock_transport_only": True,
        "cases_verified": len(results),
        "cases_pass": passed,
        "cases_fail": failed,
        "overall": "PASS" if failed == 0 else "FAIL",
        "results": results,
    }
