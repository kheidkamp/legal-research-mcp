from datetime import date
from pathlib import Path

import pytest

from legal_mcp.bfh_cases import BFHCaseAdapter, CaseSourceNotFound, CaseSourceUnavailable, RetrievedCase, normalize_case_number
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
    assert result['tool_version'] == '0.3.2-dev'
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


class FixtureBFHSearchAdapter(BFHCaseAdapter):
    def __init__(self, responses):
        super().__init__()
        self.responses = list(responses)
        self.requests = []

    async def _fetch_html(self, url, params=None):
        self.requests.append((url, dict(params or {})))
        if not self.responses:
            raise AssertionError('unexpected extra BFH fetch')
        html = self.responses.pop(0)
        return html, url


def _bfh_form_html(case_value='', search_value='', result_row=''):
    return f'''<!doctype html><html><body>
    <form method="get" action="/de/entscheidungen/entscheidungen-online/">
      <input type="hidden" name="tx_eossearch_eossearch[__referrer][@action]" value="index" />
      <input type="hidden" name="tx_eossearch_eossearch[__trustedProperties]" value="trusted-token" />
      <input name="tx_eossearch_eossearch[searchTerms][aktenzeichen]" value="{case_value}" />
      <input name="tx_eossearch_eossearch[searchTerms][ecli]" value="" />
      <input name="tx_eossearch_eossearch[searchTerms][norm]" value="" />
      <input name="tx_eossearch_eossearch[dateRange][start]" value="" />
      <input name="tx_eossearch_eossearch[dateRange][end]" value="" />
      <input name="tx_eossearch_eossearch[searchTerms][searchTerm]" value='{search_value}' />
      <button type="submit" name="tx_eossearch_eossearch[action]" value="index">Dokument suchen</button>
    </form>
    <table><tr><th>Veröffentlichung</th><th>V/NV</th><th>Senat</th><th>Entscheidung vom</th><th>Aktenzeichen</th><th>Titel</th></tr>
    {result_row}
    </table></body></html>'''


@pytest.mark.asyncio
async def test_live_form_state_is_replayed_for_exact_case_search():
    row = '''<tr><td>10.08.2023</td><td>V</td><td>IX. Senat</td><td>03.05.2023</td><td>IX R 12/22</td>
    <td><a href="/de/entscheidung/entscheidungen-online/detail/STRE202310153/">Gewinnerzielungsabsicht</a></td></tr>'''
    adapter = FixtureBFHSearchAdapter([
        _bfh_form_html(),
        _bfh_form_html(case_value='IX R 12/22', result_row=row),
    ])
    hits = await adapter.search_exact_case('IX R 12/22', date(2023, 5, 3))
    assert len(hits) == 1
    assert hits[0].canonical_url.endswith('/STRE202310153/')
    submitted = adapter.requests[1][1]
    assert submitted['tx_eossearch_eossearch[__trustedProperties]'] == 'trusted-token'
    assert submitted['tx_eossearch_eossearch[searchTerms][aktenzeichen]'] == 'IX R 12/22'
    assert submitted['tx_eossearch_eossearch[dateRange][start]'] == '03.05.2023'
    assert submitted['tx_eossearch_eossearch[dateRange][end]'] == '03.05.2023'


@pytest.mark.asyncio
async def test_bfh_search_uses_quoted_fulltext_fallback_after_reflected_no_match():
    row = '''<tr><td>10.08.2023</td><td>V</td><td>IX. Senat</td><td>03.05.2023</td><td>IX R 12/22</td>
    <td><a href="/de/entscheidung/entscheidungen-online/detail/STRE202310153/">Gewinnerzielungsabsicht</a></td></tr>'''
    adapter = FixtureBFHSearchAdapter([
        _bfh_form_html(),
        _bfh_form_html(case_value='IX R 12/22'),
        _bfh_form_html(case_value='IX R 12/22'),
        _bfh_form_html(search_value='&quot;IX R 12/22&quot;', result_row=row),
    ])
    hits = await adapter.search_exact_case('IX R 12/22', date(2023, 5, 3))
    assert len(hits) == 1
    assert len(adapter.requests) == 4
    submitted = adapter.requests[3][1]
    assert submitted['tx_eossearch_eossearch[searchTerms][aktenzeichen]'] == ''
    assert submitted['tx_eossearch_eossearch[searchTerms][searchTerm]'] == '"IX R 12/22"'


@pytest.mark.asyncio
async def test_ignored_search_submission_is_unavailable_not_not_found():
    adapter = FixtureBFHSearchAdapter([
        _bfh_form_html(),
        _bfh_form_html(),  # server returned default page, query not reflected
    ])
    with pytest.raises(Exception) as excinfo:
        await adapter.search_exact_case('IX R 12/22', date(2023, 5, 3))
    exc = excinfo.value
    assert getattr(exc, 'reason_code', None) == 'BFH_SEARCH_RESPONSE_UNEXPECTED'
    assert getattr(exc, 'diagnostics', {}).get('stage') == 'search_submission'


@pytest.mark.asyncio
async def test_definitive_reflected_no_match_has_diagnostics():
    adapter = FixtureBFHSearchAdapter([
        _bfh_form_html(),
        _bfh_form_html(case_value='IX R 99/22'),
        _bfh_form_html(case_value='IX R 99/22'),
        _bfh_form_html(search_value='&quot;IX R 99/22&quot;'),
    ])
    with pytest.raises(Exception) as excinfo:
        await adapter.search_exact_case('IX R 99/22', date(2023, 5, 3))
    exc = excinfo.value
    assert getattr(exc, 'reason_code', None) == 'TARGET_CASE_NOT_FOUND_IN_OFFICIAL_BFH_ONLINE_RESEARCH'
    diagnostics = getattr(exc, 'diagnostics', {})
    assert diagnostics.get('stage') == 'exact_match'
    assert len(diagnostics.get('attempts', [])) == 3


class RaisingCaseAdapter(FakeCaseAdapter):
    def __init__(self, exc):
        super().__init__()
        self.exc = exc

    async def retrieve_case(self, court, case_number, decision_date, focus):
        raise self.exc


@pytest.mark.asyncio
async def test_service_reports_unexpected_search_response_as_retryable_unavailable():
    adapter = RaisingCaseAdapter(CaseSourceUnavailable(
        'search response ignored query',
        reason_code='BFH_SEARCH_RESPONSE_UNEXPECTED',
        diagnostics={'stage': 'search_submission'},
    ))
    result = await LegalResearchService(case_adapter=adapter).get_case(
        court='BFH', case_number='IX R 12/22', decision_date='2023-05-03', focus='Gestaltungsmissbrauch'
    )
    assert result['status'] == 'unavailable'
    assert result['data']['content_gate']['gate_state'] == 'closed'
    assert result['data']['content_gate']['reason_code'] == 'BFH_SEARCH_RESPONSE_UNEXPECTED'
    assert result['data']['content_gate']['retryable'] is True
    assert result['data']['search_diagnostics']['stage'] == 'search_submission'


@pytest.mark.asyncio
async def test_service_reports_definitive_search_no_match_with_diagnostics():
    adapter = RaisingCaseAdapter(CaseSourceNotFound(
        'no exact case matched',
        diagnostics={'stage': 'exact_match', 'attempts': [{'strategy': 'aktenzeichen_only'}]},
    ))
    result = await LegalResearchService(case_adapter=adapter).get_case(
        court='BFH', case_number='IX R 99/22', decision_date='2023-05-03', focus='test'
    )
    assert result['status'] == 'not_found'
    assert result['data']['content_gate']['gate_state'] == 'closed'
    assert result['data']['content_gate']['reason_code'] == 'TARGET_CASE_NOT_FOUND_IN_OFFICIAL_BFH_ONLINE_RESEARCH'
    assert result['data']['content_gate']['retryable'] is False
    assert result['data']['search_diagnostics']['stage'] == 'exact_match'


def _bfh_result_only_html(result_row=''):
    return f'''<!doctype html><html><head><title>Entscheidungen online</title></head><body>
    <h2>Dokumentsuche</h2><div>Aktenzeichen</div>
    <table><tr><th>Veröffentlichung</th><th>V/NV</th><th>Senat</th><th>Entscheidung vom</th><th>Aktenzeichen</th><th>Titel</th></tr>
    {result_row}
    </table></body></html>'''


@pytest.mark.asyncio
async def test_missing_search_form_uses_direct_get_fallback_and_accepts_exact_official_hit():
    row = '''<tr><td>10.08.2023</td><td>V</td><td>IX. Senat</td><td>03.05.2023</td><td>IX R 12/22</td>
    <td><a href="/de/entscheidung/entscheidungen-online/detail/STRE202310153/">Gewinnerzielungsabsicht</a></td></tr>'''
    adapter = FixtureBFHSearchAdapter([
        _bfh_result_only_html(),
        _bfh_result_only_html(result_row=row),
    ])
    hits = await adapter.search_exact_case('IX R 12/22', date(2023, 5, 3))
    assert len(hits) == 1
    assert hits[0].decision_date == '2023-05-03'
    assert hits[0].canonical_url.endswith('/STRE202310153/')
    submitted = adapter.requests[1][1]
    assert submitted['tx_eossearch_eossearch[searchTerms][aktenzeichen]'] == 'IX R 12/22'
    assert submitted['tx_eossearch_eossearch[action]'] == 'index'


@pytest.mark.asyncio
async def test_missing_search_form_without_exact_hit_remains_retryable_unavailable():
    adapter = FixtureBFHSearchAdapter([
        _bfh_result_only_html(),
        _bfh_result_only_html(),
        _bfh_result_only_html(),
        _bfh_result_only_html(),
    ])
    with pytest.raises(CaseSourceUnavailable) as excinfo:
        await adapter.search_exact_case('IX R 12/22', date(2023, 5, 3))
    exc = excinfo.value
    assert exc.reason_code == 'BFH_SEARCH_DIRECT_FALLBACK_UNVERIFIED'
    diagnostics = exc.diagnostics
    assert diagnostics['stage'] == 'search_submission'
    assert diagnostics['form_discovery']['mode'] == 'direct_get_fallback'
    assert len(diagnostics['attempts']) == 3
    assert all(attempt['transport'] == 'direct_get_fallback' for attempt in diagnostics['attempts'])


@pytest.mark.asyncio
async def test_service_reports_direct_get_fallback_unverified_as_retryable_unavailable():
    adapter = RaisingCaseAdapter(CaseSourceUnavailable(
        'direct fallback unverified',
        reason_code='BFH_SEARCH_DIRECT_FALLBACK_UNVERIFIED',
        diagnostics={'stage': 'search_submission', 'form_discovery': {'mode': 'direct_get_fallback'}},
    ))
    result = await LegalResearchService(case_adapter=adapter).get_case(
        court='BFH', case_number='IX R 12/22', decision_date='2023-05-03', focus='Gestaltungsmissbrauch'
    )
    assert result['status'] == 'unavailable'
    assert result['data']['content_gate']['gate_state'] == 'closed'
    assert result['data']['content_gate']['reason_code'] == 'BFH_SEARCH_DIRECT_FALLBACK_UNVERIFIED'
    assert result['data']['content_gate']['retryable'] is True
    assert result['data']['search_diagnostics']['form_discovery']['mode'] == 'direct_get_fallback'
