# GitHub update – 0.3.2-dev

Targeted patch from `0.3.1-dev` to `0.3.2-dev` for BFH positive-case retrieval when the live search page does not expose a parseable search form to the Render service.

## Files materially changed

- `legal_mcp/__init__.py`
- `legal_mcp/bfh_cases.py`
- `tests/test_cases.py`
- `tests/test_official_documents.py` (version assertion only)
- `README.md`
- release/test/upgrade documentation for 0.3.2-dev

## Behavior

Prefer live-form replay. If form discovery fails specifically with `BFH_SEARCH_FORM_NOT_FOUND`, continue with a bounded direct-GET fallback against the official BFH decision-search URL. Only an exact official hit may open the case-content gate. An unverified no-hit fallback remains retryable `unavailable`, never definitive `not_found`.

After push, verify Render `/health` reports `0.3.2-dev`, then re-run the positive `IX R 12/22` direct `get_case` test.
