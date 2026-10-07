from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from legal_mcp import bfh_cases, gesetze_im_internet, official_documents
from legal_mcp.bfh_cases import BFHCaseAdapter, CaseSourceUnavailable
from legal_mcp.gesetze_im_internet import (
    GesetzeImInternetAdapter,
    OfficialSourceTooLarge,
    UnsupportedOfficialSource,
    UpstreamUnavailable,
)
from legal_mcp.network_security import UnsafeNetworkTarget, assert_public_dns_for_url, validate_https_allowlisted_url
from legal_mcp.official_documents import (
    OfficialDocumentAdapter,
    OfficialDocumentTooLarge,
    OfficialDocumentUnavailable,
    UnsafeOfficialDocumentUrl,
    UnsupportedOfficialDocument,
)


def _public_dns_noop(*args, **kwargs):
    return ("93.184.216.34",)


def test_strict_url_policy_rejects_scheme_host_userinfo_and_port():
    allowed = {"example.org"}
    bad = [
        "http://example.org/x",
        "https://evil.example/x",
        "https://user:pass@example.org/x",
        "https://example.org:444/x",
        "https://sub.example.org/x",
    ]
    for value in bad:
        with pytest.raises(UnsafeNetworkTarget):
            validate_https_allowlisted_url(value, allowed)
    assert validate_https_allowlisted_url("https://example.org/x", allowed) == "https://example.org/x"


@pytest.mark.parametrize(
    "resolved",
    [
        "127.0.0.1",
        "10.0.0.1",
        "172.16.0.1",
        "192.168.1.5",
        "169.254.169.254",
        "::1",
        "fc00::1",
        "fe80::1",
    ],
)
def test_dns_guard_rejects_non_public_addresses(resolved):
    def resolver(host, port, type=None):
        family = 10 if ":" in resolved else 2
        return [(family, 1, 6, "", (resolved, port, 0, 0) if family == 10 else (resolved, port))]

    with pytest.raises(UnsafeNetworkTarget):
        assert_public_dns_for_url("https://example.org/x", resolver=resolver)


def test_dns_guard_accepts_public_address():
    def resolver(host, port, type=None):
        return [(2, 1, 6, "", ("93.184.216.34", port))]

    assert assert_public_dns_for_url("https://example.org/x", resolver=resolver) == ("93.184.216.34",)


@pytest.mark.asyncio
async def test_official_document_redirect_cannot_escape_allowlist(monkeypatch):
    monkeypatch.setattr(official_documents, "assert_public_dns_for_url", _public_dns_noop)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "https://example.com/secret"}, request=request)

    adapter = OfficialDocumentAdapter(transport=httpx.MockTransport(handler))
    with pytest.raises(UnsafeOfficialDocumentUrl):
        await adapter._fetch_bytes("https://dserver.bundestag.de/brd/2026/0005-26.pdf")


@pytest.mark.asyncio
async def test_official_document_enforces_response_size(monkeypatch):
    monkeypatch.setattr(official_documents, "assert_public_dns_for_url", _public_dns_noop)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/html", "content-length": "11"},
            content=b"hello world",
            request=request,
        )

    adapter = OfficialDocumentAdapter(max_bytes=10, transport=httpx.MockTransport(handler))
    with pytest.raises(OfficialDocumentTooLarge):
        await adapter._fetch_bytes("https://www.recht.bund.de/x")


@pytest.mark.asyncio
async def test_official_document_rejects_unexpected_content_type(monkeypatch):
    monkeypatch.setattr(official_documents, "assert_public_dns_for_url", _public_dns_noop)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-type": "application/javascript"}, content=b"alert(1)", request=request)

    adapter = OfficialDocumentAdapter(transport=httpx.MockTransport(handler))
    with pytest.raises(UnsupportedOfficialDocument):
        await adapter._fetch_bytes("https://www.recht.bund.de/x")


@pytest.mark.asyncio
async def test_official_document_timeout_fails_closed(monkeypatch):
    monkeypatch.setattr(official_documents, "assert_public_dns_for_url", _public_dns_noop)

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)

    adapter = OfficialDocumentAdapter(transport=httpx.MockTransport(handler))
    with pytest.raises(OfficialDocumentUnavailable):
        await adapter._fetch_bytes("https://www.recht.bund.de/x")


def test_official_html_parser_does_not_surface_script_content():
    data = b"<html><body><main>SAFE_FACT<script>FAIL_JS_EXEC</script></main></body></html>"
    parsed = OfficialDocumentAdapter.parse_html(data, "https://www.recht.bund.de/x", "text/html")
    assert "SAFE_FACT" in parsed.pages[0]
    assert "FAIL_JS_EXEC" not in parsed.pages[0]


@pytest.mark.asyncio
async def test_gii_redirect_cannot_escape_allowlist(monkeypatch):
    monkeypatch.setattr(gesetze_im_internet, "assert_public_dns_for_url", _public_dns_noop)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "https://example.com/escape"}, request=request)

    adapter = GesetzeImInternetAdapter(transport=httpx.MockTransport(handler))
    with pytest.raises(UpstreamUnavailable):
        await adapter._fetch("https://www.gesetze-im-internet.de/kstg_1977/")


@pytest.mark.asyncio
async def test_gii_enforces_response_size(monkeypatch):
    monkeypatch.setattr(gesetze_im_internet, "assert_public_dns_for_url", _public_dns_noop)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-type": "text/html"}, content=b"01234567890", request=request)

    adapter = GesetzeImInternetAdapter(max_bytes=10, transport=httpx.MockTransport(handler))
    with pytest.raises(OfficialSourceTooLarge):
        await adapter._fetch("https://www.gesetze-im-internet.de/kstg_1977/")


@pytest.mark.asyncio
async def test_gii_rejects_unexpected_content_type(monkeypatch):
    monkeypatch.setattr(gesetze_im_internet, "assert_public_dns_for_url", _public_dns_noop)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-type": "application/javascript"}, content=b"alert(1)", request=request)

    adapter = GesetzeImInternetAdapter(transport=httpx.MockTransport(handler))
    with pytest.raises(UnsupportedOfficialSource):
        await adapter._fetch("https://www.gesetze-im-internet.de/kstg_1977/")


@pytest.mark.asyncio
async def test_gii_timeout_fails_closed(monkeypatch):
    monkeypatch.setattr(gesetze_im_internet, "assert_public_dns_for_url", _public_dns_noop)

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)

    adapter = GesetzeImInternetAdapter(transport=httpx.MockTransport(handler))
    with pytest.raises(UpstreamUnavailable):
        await adapter._fetch("https://www.gesetze-im-internet.de/kstg_1977/")


def test_gii_visible_text_drops_script_content():
    text = GesetzeImInternetAdapter._visible_text(
        "<html><body><main>SAFE_FACT<script>FAIL_JS_EXEC</script></main></body></html>"
    )
    assert "SAFE_FACT" in text
    assert "FAIL_JS_EXEC" not in text


@pytest.mark.asyncio
async def test_bfh_redirect_cannot_escape_allowlist(monkeypatch):
    monkeypatch.setattr(bfh_cases, "assert_public_dns_for_url", _public_dns_noop)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "https://example.com/escape"}, request=request)

    adapter = BFHCaseAdapter(transport=httpx.MockTransport(handler))
    with pytest.raises(CaseSourceUnavailable):
        await adapter._fetch_html("https://www.bundesfinanzhof.de/de/entscheidungen/entscheidungen-online/")


@pytest.mark.asyncio
async def test_bfh_enforces_response_size(monkeypatch):
    monkeypatch.setattr(bfh_cases, "assert_public_dns_for_url", _public_dns_noop)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-type": "text/html"}, content=b"01234567890", request=request)

    adapter = BFHCaseAdapter(max_bytes=10, transport=httpx.MockTransport(handler))
    with pytest.raises(CaseSourceUnavailable) as exc:
        await adapter._fetch_html("https://www.bundesfinanzhof.de/de/entscheidungen/entscheidungen-online/")
    assert exc.value.reason_code == "BFH_RESPONSE_TOO_LARGE"


@pytest.mark.asyncio
async def test_bfh_rejects_unexpected_content_type(monkeypatch):
    monkeypatch.setattr(bfh_cases, "assert_public_dns_for_url", _public_dns_noop)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-type": "application/javascript"}, content=b"alert(1)", request=request)

    adapter = BFHCaseAdapter(transport=httpx.MockTransport(handler))
    with pytest.raises(CaseSourceUnavailable) as exc:
        await adapter._fetch_html("https://www.bundesfinanzhof.de/de/entscheidungen/entscheidungen-online/")
    assert exc.value.reason_code == "BFH_CONTENT_TYPE_REJECTED"


@pytest.mark.asyncio
async def test_bfh_timeout_fails_closed(monkeypatch):
    monkeypatch.setattr(bfh_cases, "assert_public_dns_for_url", _public_dns_noop)

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)

    adapter = BFHCaseAdapter(transport=httpx.MockTransport(handler))
    with pytest.raises(CaseSourceUnavailable):
        await adapter._fetch_html("https://www.bundesfinanzhof.de/de/entscheidungen/entscheidungen-online/")


def test_no_browser_or_javascript_runtime_dependency_is_present():
    req = Path("requirements.txt").read_text(encoding="utf-8").casefold()
    forbidden = ["selenium", "playwright", "pyppeteer", "javascript", "nodejs"]
    assert not any(value in req for value in forbidden)
