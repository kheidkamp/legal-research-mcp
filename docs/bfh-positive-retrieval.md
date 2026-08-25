# BFH positive named-case retrieval – 0.3.2-dev

## Search contract

`get_case` must not treat discovery or an unverified search response as proof of target-case content.
The adapter therefore uses two bounded transports against the official BFH decision-search page.

### Preferred: live-form replay

1. open the official BFH decision-search page;
2. identify the GET form containing the `Aktenzeichen` control;
3. serialize its current visible and hidden TYPO3/Extbase state;
4. overlay the requested query;
5. verify no-hit responses before treating them as definitive.

### Controlled fallback: direct GET

Some live responses returned to the Render service may expose the decision list without a parseable
search `<form>`. `BFH_SEARCH_FORM_NOT_FOUND` therefore no longer terminates positive retrieval.
The adapter submits the official visible field names directly to the same official BFH search URL.

An exact official result row matching the requested case number (and supplied decision date, when
present) is sufficient to proceed to document opening. A direct-fallback no-hit without reflected
query state is **not** definitive evidence of absence and returns retryable
`BFH_SEARCH_DIRECT_FALLBACK_UNVERIFIED`.

## Controlled strategies

For a supplied date:

1. `Aktenzeichen + decision date`;
2. `Aktenzeichen` alone;
3. quoted `"Aktenzeichen"` in `Suchbegriff`.

The third strategy follows the BFH's own search instructions for a file number that is not found
through the dedicated field.

## Diagnostics

Technical failures remain closed and retryable. Relevant reason codes include:

- `BFH_SEARCH_FORM_METHOD_UNSUPPORTED`
- `BFH_SEARCH_RESPONSE_UNEXPECTED`
- `BFH_SEARCH_DIRECT_FALLBACK_UNVERIFIED`
- `BFH_CASE_DOCUMENT_OPEN_FAILED`

`BFH_SEARCH_FORM_NOT_FOUND` is recorded inside `search_diagnostics.form_discovery` when the direct
GET fallback is used, rather than terminating the request immediately.

Only after supported search strategies have produced a verifiably processed no-match may the
service return `TARGET_CASE_NOT_FOUND_IN_OFFICIAL_BFH_ONLINE_RESEARCH`.
