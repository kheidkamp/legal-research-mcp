# Release Notes – Legal Research MCP 0.3.0-dev

## Scope

Hardens the case-law research path after repeated doctrinal-backfilling failures for named
historical BFH decisions whose primary text was not available through the current official
online path.

## Added

- Public MCP tool `get_case(court, case_number, decision_date, focus)`.
- Machine-readable `content_gate` for target-case claims.
- Deterministic fail-closed behavior for dated BFH decisions before the official online coverage
  window.
- Exact named-case discovery metadata in `search_primary_sources` with
  `required_retrieval_tool=get_case`.
- Official BFH host added to the strict read-only official-document allowlist.
- Initial BFH online case adapter for 2010+ exact case-number lookup and official decision
  retrieval.
- Unit/contract tests for the closed and open gate states.

## Critical invariant

When `data.content_gate.target_case_content_allowed=false`, downstream agents must not attribute
facts, holding, reasons, headnotes, quotations, paraphrases, or legal propositions to the target
case. Search snippets, secondary sources, model memory, later cases, and the user prompt do not
open the gate.

## Non-goals

- no historical statutory resolver;
- no complete citation graph;
- no automatic email retrieval of pre-2010 BFH decisions;
- no autonomous external action;
- no production authentication change.
