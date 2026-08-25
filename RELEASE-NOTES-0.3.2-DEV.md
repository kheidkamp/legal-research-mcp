# Release Notes – Legal Research MCP 0.3.2-dev

## Purpose

0.3.2-dev is a narrow follow-up patch to the positive BFH `get_case` retrieval path.
It does not change the structured fail-closed target-case evidence gate introduced in 0.3.0-dev.

## Triggering live defect

Under 0.3.1-dev, the direct positive test for BFH, 03.05.2023 – IX R 12/22 failed with:

- `status=unavailable`
- `reason_code=BFH_SEARCH_FORM_NOT_FOUND`
- `search_diagnostics.stage=search_form_discovery`

The BFH decision is within the official post-2010 online corpus, but the HTML returned to the Render service did not expose a search `<form>` that matched the expected field structure.

## Changes

- The adapter still prefers replaying the live BFH TYPO3/Extbase search form when it is detectable.
- If the form is not parseable, the adapter now falls back to controlled direct GET submissions using the official visible BFH search field names.
- Direct fallback runs the same bounded strategies:
  1. case number + decision date;
  2. case number only;
  3. quoted case number in `Suchbegriff`.
- An exact BFH result row containing the requested case number and date can open the positive retrieval path even when the form itself was not parseable.
- A no-hit direct fallback without reflected query state is **not** treated as definitive `not_found`; it remains `unavailable` with `reason_code=BFH_SEARCH_DIRECT_FALLBACK_UNVERIFIED`.
- Diagnostics now identify whether transport used `live_form_replay` or `direct_get_fallback`.

## Safety invariants unchanged

- Pre-2010 named BFH cases remain deterministically closed.
- Search/discovery results alone are not target-case evidence.
- Only a successfully opened official target decision may set `target_case_content_allowed=true`.
- Secondary sources, snippets, later decisions, model memory and user wording cannot override a closed gate.

## Validation

Local unit/regression suite: **38/38 PASS**.

Live positive retrieval must still be verified after deployment because the build environment has no outbound network access to BFH.
