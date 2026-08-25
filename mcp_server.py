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
        "For every named BFH decision, call get_case before attributing any facts, holding, "
        "reasons, headnotes, quotations, paraphrases, or legal propositions to that decision. "
        "The get_case data.content_gate is binding: when target_case_content_allowed=false, "
        "do not generate target-case content from memory, knowledge search, snippets, secondary "
        "sources, later decisions, or the user prompt. After a concrete official document or "
        "amendment candidate is identified, use get_official_document_text to open the exact "
        "official PDF/HTML passage before asserting a concrete amendment command."
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
async def get_case(
    court: str,
    case_number: str,
    decision_date: str,
    focus: str,
) -> dict:
    """Retrieve one named BFH decision and return a binding target-case evidence gate.

    MANDATORY for substantive claims about a named BFH decision. All four inputs are
    required strings for Copilot Studio compatibility. Use ISO YYYY-MM-DD for
    ``decision_date`` (or an empty string if genuinely unknown) and describe the legal
    issue in ``focus``.

    The response contains ``data.content_gate.target_case_content_allowed``. If it is
    false, the downstream agent MUST NOT state, reconstruct, summarize, paraphrase, quote,
    or attribute any facts, outcome, holding, reasons, headnotes, or legal propositions to
    the target case, even with caveats such as "sinngemäß", "zugeschrieben" or
    "rekonstruiert". Other search results, snippets, secondary sources, model memory,
    later decisions, and the user prompt do not override a closed gate.
    """
    return await service.get_case(
        court=court.strip(),
        case_number=case_number.strip(),
        decision_date=decision_date.strip(),
        focus=focus.strip(),
    )


@mcp.tool()
async def get_official_document_text(
    document_ref: str,
    locator: str,
    query: str,
) -> dict:
    """Open an identified official German legal PDF/HTML document and verify an exact passage.

    Provide three required strings only. ``document_ref`` is either a supported official
    document identifier such as ``BR-Drs. 5/26`` / ``BT-Drs. 21/3343`` /
    ``BGBl. 2026 I Nr. 33`` or an allowlisted official HTTPS URL. ``locator`` narrows the
    document (for example ``Artikel 30 Nummer 1``) and ``query`` is the exact legal phrase
    to verify (for example ``§ 8b Absatz 6 Satz 2``). A matching passage returns
    page-aware full_checked evidence. Do not infer a concrete amendment command when the
    query is not verified.
    """
    document_ref = document_ref.strip()
    locator = locator.strip()
    query = query.strip()
    if document_ref.lower().startswith("https://"):
        return await service.get_official_document_text(
            url=document_ref,
            locator=locator,
            query=query,
        )
    return await service.get_official_document_text(
        document_id=document_ref,
        locator=locator,
        query=query,
    )
