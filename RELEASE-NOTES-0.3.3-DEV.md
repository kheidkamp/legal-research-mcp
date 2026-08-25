# Legal Research MCP 0.3.3-dev - Release Notes

## Scope

Narrow positive-BFH-retrieval patch. No agent-skill change.

## Runtime finding behind the patch

0.3.2-dev reached the live BFH decision-search page but the direct GET fallback was ignored by the BFH application (`response_reflected_query=false`). Runtime diagnostics showed three forms on the page and visible `Aktenzeichen` text, while the previous parser did not identify the decision-search form.

## Changes

- Discover the BFH decision-search form by a ranked combination of:
  - canonical field names when present,
  - Extbase/TYPO3 hidden state such as `__trustedProperties`,
  - BFH tool namespace fields,
  - visible labels such as `Aktenzeichen`, `Entscheidungsdatum` and `Dokument suchen`.
- Resolve semantic search fields through `<label for>` -> input `id` -> actual `name` mappings when BFH field names differ from the previous contract.
- Replay the actual live field names rather than blindly adding stale canonical field names.
- Preserve BFH cookies between landing-page retrieval and search submissions.
- Do not add an Extbase action field unless it was present in the live form state.
- Extend diagnostics with discovered form method, semantic field names and trusted-properties presence.
- Keep all case-content gates fail-closed unless an exact official BFH target hit is opened.

## Tests

39/39 local tests PASS, including a new regression fixture for label-based form discovery with alternate live field names and hidden trusted state.

## Required live validation

1. Deploy to Render.
2. Confirm `/health` returns `0.3.3-dev`.
3. Run direct `get_case` for BFH 03.05.2023 - IX R 12/22.
4. Expect an exact official hit and open content gate.
5. Re-run BFH 07.07.1998 - VIII R 10/96 as the pre-2010 closed-gate control.
