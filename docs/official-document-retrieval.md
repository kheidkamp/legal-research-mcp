# Official document retrieval contract (0.3.0-dev)

## Purpose

Open a concrete official document after discovery and return verifiable passage evidence. This tool is not a search engine and should normally be called only after an official URL/document identifier has been identified.

## Public MCP tool

`get_official_document_text`

Inputs are intentionally restricted to exactly three required strings for Copilot Studio compatibility:

- `document_ref`: supported official document identifier or allowlisted official HTTPS URL;
- `locator`: the requested location inside the document;
- `query`: the exact phrase or legal reference that must be verified.

No nullable unions, optional tuning parameters, arrays, or nested input objects are exposed by this tool. Passage count and context size remain internal defaults.

Example:

```text
document_ref: BR-Drs. 5/26
locator: Artikel 30 Nummer 1
query: § 8b Absatz 6 Satz 2
```

## Internal resolution

The server interprets `document_ref` internally:

- an `https://...` value is treated as an official URL and passes through the existing allowlist/security validation;
- any other value is treated as a supported official document identifier and resolved by the existing document adapter.

This does not weaken the SSRF boundary.

## Verification semantics

- `query_found=true` plus a requested locator that is also found -> targeted evidence may be `full_checked`;
- locator found but query not found -> `partial`; returned locator context is navigation evidence only;
- locator requested but not found -> no complete verification even if the query text appears elsewhere in the document;
- a PDF without an extractable text layer returns `unavailable`; OCR is intentionally not performed by this service.

## Security

The tool rejects arbitrary URLs. It accepts HTTPS only on an explicit official-host allowlist, validates every redirect hop, caps download size, and performs no browser/JavaScript execution.

## StoFöG regression target

For the v2.3.0 D1 regression:

- document: `BR-Drs. 5/26`;
- locator: `Artikel 30 Nummer 1`;
- query: `§ 8b Absatz 6 Satz 2`.

The expected official passage states that § 8b Absatz 6 Satz 2 is replaced by a new sentence. This expected result belongs to the regression test; the tool must still retrieve and verify the passage at runtime.
