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
        "Read-only German legal research MVP. Discovery results are not evidence. "
        "Use get_norm to open current official statutory text. Use trace_norm_amendments "
        "for provision-specific amendment-history requests and respect coverage_status: "
        "only complete permits a definitive latest-amendment assertion."
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
    and latest_verified_amendment is populated. partial/unknown requires abstention or
    narrower wording. Whole-statute amendment headers are discovery leads only.
    """
    return await service.trace_norm_amendments(law, section, from_date, to_date, include_non_changes)
