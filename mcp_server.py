from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from legal_mcp.render_config import build_transport_allowlists
from legal_mcp.service import LegalResearchService


allowed_hosts, allowed_origins = build_transport_allowlists()
transport_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=True,
    allowed_hosts=allowed_hosts,
    allowed_origins=allowed_origins,
)

mcp = FastMCP(
    "Legal Research DE",
    stateless_http=True,
    json_response=True,
    transport_security=transport_security,
    instructions=(
        "Read-only German legal research service. Discovery results are not evidence. "
        "Use get_norm for current official statutory text. Use trace_norm_amendments for "
        "provision-specific amendment-history requests and respect its coverage limits. "
        "After a concrete official document or amendment candidate is identified, use "
        "get_official_document_text to open the exact official PDF/HTML passage before "
        "asserting a concrete amendment command."
    ),
)
service = LegalResearchService()


@mcp.tool()
async def search_primary_sources(
    query: str,
    source_types: list[str] | None = None,
    jurisdiction: str = "DE",
    as_of_date: str | None = None,
    max_results: int = 10,
) -> dict:
    """Discover official German primary-source candidates.

    Discovery only: every returned source has verification_level=identified and must
    be opened with a retrieval tool before its legal content is relied upon.
    """
    return await service.search_primary_sources(query, source_types, jurisdiction, as_of_date, max_results)


@mcp.tool()
async def get_norm(
    law: str,
    section: str,
    as_of_date: str | None = None,
    include_structure: bool = True,
    include_application_rules: bool = False,
) -> dict:
    """Retrieve official consolidated text of a specific German statutory provision.

    Use for precise statements about current statutory text. Historical requests are
    marked partial until a historical-version resolver is implemented. The response
    includes verification and coverage metadata; never infer more coverage than stated.
    """
    return await service.get_norm(law, section, as_of_date, include_structure, include_application_rules)


@mcp.tool()
async def trace_norm_amendments(
    law: str,
    section: str,
    from_date: str,
    to_date: str,
    include_non_changes: bool = True,
) -> dict:
    """Trace amendments affecting one statutory provision over a date window.

    A definitive 'latest amendment' is permitted only when coverage_status=complete
    and latest_verified_amendment is populated. partial/unknown requires narrower
    wording or independent official fallback evidence. Whole-statute amendment headers
    are discovery leads only.
    """
    return await service.trace_norm_amendments(law, section, from_date, to_date, include_non_changes)


@mcp.tool()
async def get_official_document_text(
    url: str | None = None,
    document_id: str | None = None,
    locator: str | None = None,
    query: str | None = None,
    max_passages: int = 3,
    context_chars: int = 1400,
) -> dict:
    """Open an identified official German legal PDF/HTML document and return exact passages.

    Use this after discovery/candidate lock when a concrete official document must be
    verified, especially an amending act. Provide either an allowlisted official HTTPS
    URL or a supported document_id such as 'BR-Drs. 5/26', 'BT-Drs. 21/3343', or
    'BGBl. 2026 I Nr. 33'. Use locator to narrow the document (for example 'Artikel 30')
    and query for the exact phrase that must be verified (for example
    '§ 8b Absatz 6 Satz 2'). A query match returns page-aware full_checked evidence;
    a locator-only result does not prove the requested amendment command.
    """
    return await service.get_official_document_text(url, document_id, locator, query, max_passages, context_chars)
