# Release Notes – Legal Research MCP 0.3.1-dev

## Scope

Targeted patch for the positive BFH `get_case` retrieval path. `0.3.0-dev` correctly failed closed,
but an end-to-end test with the online BFH decision `03.05.2023 – IX R 12/22` returned
`not_found` although the decision exists in the official BFH online collection.

## Fixed

- Opens the current BFH decision-search page before submitting a query.
- Serializes and replays the current GET form state, including TYPO3/Extbase hidden fields such as
  `__referrer` and `__trustedProperties`.
- Submits the complete visible search field set instead of only a partial query object.
- Search sequence is now deterministic:
  1. exact case number + supplied decision date;
  2. exact case number without date;
  3. quoted case number in the full-text field, matching the BFH's own search guidance.
- Result-link parsing accepts stable `STRE...` detail routes across German/English path variants.
- A response that does not reflect the submitted query is no longer classified as a definitive
  `not_found`; it returns a retryable technical failure with diagnostics.
- Definitive no-match and document-open failures expose structured `search_diagnostics`.

## Safety invariant

The `content_gate` remains fail closed. A retrieval/search failure never permits target-case
facts, holdings, reasons, quotations, paraphrases, or attributed legal propositions.

## Regression target

The required positive live test is:

- court: `BFH`
- case_number: `IX R 12/22`
- decision_date: `2023-05-03`

Expected end-to-end result after deployment: official BFH target document opened,
`gate_state=open`, `target_case_content_allowed=true`.
