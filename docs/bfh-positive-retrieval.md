# BFH positive named-case retrieval – 0.3.1-dev

## Search contract

`get_case` must not treat a raw GET with only a subset of visible parameters as proof that the BFH
search endpoint processed the query. The BFH page is a TYPO3/Extbase form and may include hidden
state fields.

The adapter therefore:

1. opens the official BFH decision-search page;
2. identifies the GET form containing the `Aktenzeichen` control;
3. serializes its current controls and hidden state;
4. overlays the requested query;
5. verifies that a no-hit response reflects the submitted query before classifying it as a real
   no-match.

## Controlled strategies

For a supplied date:

1. `Aktenzeichen + decision date`;
2. `Aktenzeichen` alone;
3. quoted `"Aktenzeichen"` in `Suchbegriff`.

The third strategy follows the BFH's own search instructions for a file number that is not found
through the dedicated field.

## Diagnostics

Technical failures remain closed and retryable. Reason codes include:

- `BFH_SEARCH_FORM_NOT_FOUND`
- `BFH_SEARCH_FORM_METHOD_UNSUPPORTED`
- `BFH_SEARCH_RESPONSE_UNEXPECTED`
- `BFH_CASE_DOCUMENT_OPEN_FAILED`

Only after all reflected supported search strategies produce no exact match may the service return
`TARGET_CASE_NOT_FOUND_IN_OFFICIAL_BFH_ONLINE_RESEARCH`.
