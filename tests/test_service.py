from pathlib import Path

import pytest

from legal_mcp.gesetze_im_internet import GesetzeImInternetAdapter
from legal_mcp.registry import resolve_law
from legal_mcp.service import LegalResearchService


class FakeAdapter(GesetzeImInternetAdapter):
    async def get_current_norm(self, entry, section):
        html = Path("tests/fixtures/kstg_8b_sample.html").read_text(encoding="utf-8")
        return self.parse_norm_html(html, entry, section)

    async def get_law_landing_text(self, entry):
        return (
            "Koerperschaftsteuergesetz (KStG)\nzuletzt geaendert durch Art. 30 G v. 4.2.2026 I Nr. 33",
            entry.landing_url,
        )


def test_norm_parser_reaches_actual_end():
    entry = resolve_law("KStG")
    html = Path("tests/fixtures/kstg_8b_sample.html").read_text(encoding="utf-8")
    parsed = GesetzeImInternetAdapter.parse_norm_html(html, entry, "8b")
    assert "Abs. 11" in parsed.structure
    assert "Abs. 10" in parsed.structure
    assert "Fussnote" not in parsed.text


@pytest.mark.asyncio
async def test_search_is_discovery_only():
    service = LegalResearchService(FakeAdapter())
    result = await service.search_primary_sources("§ 8b KStG")
    assert result["status"] == "ok"
    assert result["data"]["results"][0]["verification_level"] == "identified"


@pytest.mark.asyncio
async def test_current_norm_is_full_checked_for_today():
    service = LegalResearchService(FakeAdapter())
    result = await service.get_norm("KStG", "8b")
    assert result["status"] == "ok"
    assert result["data"]["coverage_status"] == "complete"
    assert "Abs. 11" in result["data"]["norm"]["structure"]
    assert result["data"]["norm"]["source"]["verification_level"] == "full_checked"


@pytest.mark.asyncio
async def test_historical_request_is_partial():
    service = LegalResearchService(FakeAdapter())
    result = await service.get_norm("KStG", "8b", "2021-06-30")
    assert result["status"] == "partial"
    assert result["data"]["coverage_status"] == "partial"


@pytest.mark.asyncio
async def test_amendment_trace_never_sets_latest_when_partial():
    service = LegalResearchService(FakeAdapter())
    result = await service.trace_norm_amendments("KStG", "8b", "2020-01-01", "2026-08-20")
    assert result["status"] == "partial"
    assert result["data"]["coverage_status"] == "partial"
    assert result["data"]["latest_verified_amendment"] is None
    assert result["data"]["newest_verified_change"] is None
    assert result["data"]["checked_later_acts"][0]["provision_specific_effect_verified"] is False


def test_render_transport_allowlist(monkeypatch):
    from legal_mcp.render_config import build_transport_allowlists

    monkeypatch.setenv("RENDER_EXTERNAL_HOSTNAME", "legal-research-mcp-dev.onrender.com")
    hosts, origins = build_transport_allowlists()
    assert "legal-research-mcp-dev.onrender.com" in hosts
    assert "legal-research-mcp-dev.onrender.com:*" in hosts
    assert "https://legal-research-mcp-dev.onrender.com" in origins
    assert "*" not in hosts
