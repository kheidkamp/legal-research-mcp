from datetime import date
from pathlib import Path

import pytest

from legal_mcp.bfh_cases import BFHCaseAdapter, RetrievedCase, normalize_case_number
from legal_mcp.service import LegalResearchService


class FakeCaseAdapter(BFHCaseAdapter):
    def __init__(self, retrieved=None):
        super().__init__()
        self.retrieved = retrieved
        self.calls = []

    async def retrieve_case(self, court, case_number, decision_date, focus):
        self.calls.append((court, case_number, decision_date, focus))
        return self.retrieved


def test_case_number_normalization():
    assert normalize_case_number(' viii   r  10 / 1996 ') == 'VIII R 10/96'
    assert normalize_case_number('I B 102/09') == 'I B 102/09'


def test_bfh_url_validator_blocks_non_bfh_host():
    with pytest.raises(Exception):
        BFHCaseAdapter._validate_bfh_url('https://example.com/de/entscheidung/')


def test_bfh_url_validator_accepts_official_bfh_host():
    url = BFHCaseAdapter._validate_bfh_url(
        'https://www.bundesfinanzhof.de/de/entscheidungen/entscheidungen-online/'
    )
    assert url.startswith('https://www.bundesfinanzhof.de/')


def test_bfh_search_parser_finds_exact_case():
    html = Path('tests/fixtures/bfh_search_sample.html').read_text(encoding='utf-8')
    hits = BFHCaseAdapter.parse_search_results(html, 'IX R 7/17')
    assert len(hits) == 1
    assert hits[0].case_number == 'IX R 7/17'
    assert hits[0].decision_date == '2017-12-06'
    assert hits[0].canonical_url.endswith('/STRE201810036/')


@pytest.mark.asyncio
async def test_pre_2010_case_closes_content_gate_without_fetch():
    adapter = FakeCaseAdapter()
    service = LegalResearchService(case_adapter=adapter)
    result = await service.get_case(
        court='BFH',
        case_number='VIII R 10/96',
        decision_date='1998-07-07',
        focus='Anteilsveräußerung Ausschüttung Abwicklung Gestaltungsmissbrauch',
    )
    assert result['status'] == 'partial'
    assert result['tool_version'] == '0.3.0-dev'
    gate = result['data']['content_gate']
    assert gate['gate_state'] == 'closed'
    assert gate['must_stop_target_case_content'] is True
    assert gate['target_case_content_allowed'] is False
    assert gate['target_case_primary_text_verified'] is False
    assert gate['reason_code'] == 'TARGET_DATE_BEFORE_BFH_ONLINE_COVERAGE'
    assert 'target_case_holding' in gate['forbidden_claim_classes']
    assert 'STOP target-case content generation' in gate['output_directive']
    assert result['data']['case'] is None
    assert adapter.calls == []


@pytest.mark.asyncio
async def test_post_2010_opened_official_case_opens_gate():
    retrieved = RetrievedCase(
        court='BFH',
        case_number='IX R 7/17',
        decision_date='2017-12-06',
        decision_type='Urteil',
        title='Veräußerung von Anteilen an Kapitalgesellschaften',
        ecli='ECLI:DE:BFH:2017:U.061217.IXR7.17.0',
        canonical_url='https://www.bundesfinanzhof.de/de/entscheidung/entscheidungen-online/detail/STRE201810036/',
        content_hash='sha256:abc',
        text='official text',
        passages=[{
            'locator': 'BFH official decision text',
            'page': None,
            'passage': 'Auf der Ebene des veräußernden Gesellschafters ...',
            'passage_hash': 'sha256:def',
            'match_type': 'focus_token_window',
            'focus_token_hits': 3,
        }],
    )
    adapter = FakeCaseAdapter(retrieved=retrieved)
    service = LegalResearchService(case_adapter=adapter)
    result = await service.get_case(
        court='BFH',
        case_number='IX R 7/17',
        decision_date='2017-12-06',
        focus='Veräußerung eigener Anteile',
    )
    assert result['status'] == 'ok'
    assert result['data']['coverage_status'] == 'complete'
    assert result['data']['content_gate']['gate_state'] == 'open'
    assert result['data']['content_gate']['must_stop_target_case_content'] is False
    assert result['data']['content_gate']['target_case_content_allowed'] is True
    assert result['data']['content_gate']['target_case_primary_text_verified'] is True
    assert result['data']['case']['source']['verification_level'] == 'full_checked'
    assert result['data']['case']['evidence'][0]['verification_level'] == 'full_checked'


@pytest.mark.asyncio
async def test_named_case_discovery_is_identified_and_requires_get_case():
    service = LegalResearchService(case_adapter=FakeCaseAdapter())
    result = await service.search_primary_sources('BFH VIII R 10/96 vom 07.07.1998', source_types=['case'])
    assert result['status'] == 'ok'
    item = result['data']['results'][0]
    assert item['source_type'] == 'case'
    assert item['verification_level'] == 'identified'
    assert item['required_retrieval_tool'] == 'get_case'
    assert 'No case proposition is verified' in item['match_summary']
