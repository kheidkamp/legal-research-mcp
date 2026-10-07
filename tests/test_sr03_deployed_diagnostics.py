import asyncio

from legal_mcp.sr03_diagnostics import run_sr03_startup_diagnostics


def test_sr03_startup_diagnostics_all_pass_without_external_network():
    result = asyncio.run(run_sr03_startup_diagnostics())
    assert result["diagnostic"] == "SR03_RESEARCH_EXTERNAL_RETRIEVAL_SECURITY"
    assert result["mode"] == "DETERMINISTIC_STARTUP_SELFTEST"
    assert result["external_network_calls"] == 0
    assert result["mock_transport_only"] is True
    assert result["cases_verified"] == 6
    assert result["cases_pass"] == 6
    assert result["cases_fail"] == 0
    assert result["overall"] == "PASS"
    assert [item["case_id"] for item in result["results"]] == [
        "SR03-LR04",
        "SR03-LR05",
        "SR03-LR06",
        "SR03-LR07",
        "SR03-LR08",
        "SR03-LR09",
    ]
    assert [item["control"] for item in result["results"]] == [
        "SEC-RES-004",
        "SEC-RES-005",
        "SEC-RES-006",
        "SEC-RES-007",
        "SEC-RES-008",
        "SEC-RES-009",
    ]
    assert all(item["status"] == "PASS" for item in result["results"])
