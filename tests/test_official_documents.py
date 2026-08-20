from pathlib import Path

import pytest

from legal_mcp.official_documents import (
    OfficialDocumentAdapter,
    ParsedOfficialDocument,
    UnsafeOfficialDocumentUrl,
)
from legal_mcp.service import LegalResearchService


FIXTURE = Path('tests/fixtures/official_amendment_sample.pdf')


class FakeOfficialDocumentAdapter(OfficialDocumentAdapter):
    async def open_document(self, url: str) -> ParsedOfficialDocument:
        return self.parse_pdf(FIXTURE.read_bytes(), url)


def test_resolve_bundesrat_document_id():
    url = OfficialDocumentAdapter.resolve_document_id('BR-Drs. 5/26')
    assert url == 'https://dserver.bundestag.de/brd/2026/0005-26.pdf'


def test_resolve_bundestag_document_id():
    url = OfficialDocumentAdapter.resolve_document_id('BT-Drs. 21/3343')
    assert url == 'https://dserver.bundestag.de/btd/21/033/2103343.pdf'


def test_resolve_bgbl_document_id():
    url = OfficialDocumentAdapter.resolve_document_id('BGBl. 2026 I Nr. 33')
    assert url == 'https://www.recht.bund.de/bgbl/1/2026/33/VO.html'


def test_url_allowlist_blocks_non_official_host():
    with pytest.raises(UnsafeOfficialDocumentUrl):
        OfficialDocumentAdapter.validate_official_url('https://example.com/document.pdf')


def test_url_allowlist_blocks_http():
    with pytest.raises(UnsafeOfficialDocumentUrl):
        OfficialDocumentAdapter.validate_official_url('http://dserver.bundestag.de/brd/2026/0005-26.pdf')


def test_pdf_parser_and_locator_query_match():
    parsed = OfficialDocumentAdapter.parse_pdf(
        FIXTURE.read_bytes(),
        'https://dserver.bundestag.de/brd/2026/0005-26.pdf',
    )
    adapter = OfficialDocumentAdapter()
    matches, locator_found, query_found = adapter.find_passages(
        parsed,
        locator='Artikel 30',
        query='§ 8b Absatz 6 Satz 2',
    )
    assert locator_found is True
    assert query_found is True
    assert matches
    assert matches[0]['page'] == 2
    assert 'wird durch den folgenden Satz ersetzt' in matches[0]['passage']


@pytest.mark.asyncio
async def test_service_returns_full_checked_amendment_passage():
    service = LegalResearchService(document_adapter=FakeOfficialDocumentAdapter())
    result = await service.get_official_document_text(
        document_id='BR-Drs. 5/26',
        locator='Artikel 30',
        query='§ 8b Absatz 6 Satz 2',
    )
    assert result['status'] == 'ok'
    assert result['tool_version'] == '0.2.0-dev'
    assert result['data']['coverage_status'] == 'complete'
    assert result['data']['query_found'] is True
    assert result['data']['evidence'][0]['verification_level'] == 'full_checked'
    assert result['data']['evidence'][0]['page'] == 2


@pytest.mark.asyncio
async def test_service_query_not_found_is_partial_not_proof():
    service = LegalResearchService(document_adapter=FakeOfficialDocumentAdapter())
    result = await service.get_official_document_text(
        document_id='BR-Drs. 5/26',
        locator='Artikel 30',
        query='§ 8b Absatz 4 Satz 8',
    )
    assert result['status'] == 'partial'
    assert result['data']['coverage_status'] == 'partial'
    assert result['data']['query_found'] is False
    assert result['data']['matches'][0]['match_type'] == 'locator_only_query_not_found'
    assert result['data']['evidence'][0]['verification_level'] == 'opened'


@pytest.mark.asyncio
async def test_requested_locator_must_be_found_for_complete_verification():
    service = LegalResearchService(document_adapter=FakeOfficialDocumentAdapter())
    result = await service.get_official_document_text(
        document_id='BR-Drs. 5/26',
        locator='Artikel 999',
        query='§ 8b Absatz 6 Satz 2',
    )
    assert result['status'] == 'partial'
    assert result['data']['coverage_status'] == 'partial'
    assert result['data']['locator_found'] is False
    assert result['data']['query_found'] is True
    assert result['data']['document']['source']['verification_level'] == 'opened'
