# Legal Research MCP 0.2-dev release notes

## Added

- `get_official_document_text` MCP tool.
- Official-document identifier resolution for BR/BT Drucksachen and BGBl. references.
- Strict official-host HTTPS allowlist and per-redirect validation.
- 20 MB document download cap.
- Text-native PDF extraction with page-aware passage evidence.
- HTML/plain-text official document extraction.
- Locator + exact normalized query verification semantics.
- Regression tests for the StoFöG D1 amendment-action failure mode.

## Changed

- Service/health/tool envelope version: `0.2.0-dev`.
- MCP server instructions now route identified amendment documents to the new retrieval tool.
- `pypdf` added as runtime dependency.

## Unchanged by design

- `trace_norm_amendments` remains conservative and does not claim a complete provision-specific amendment chain.
- Historical norm-version resolution is still not implemented.
- DEV deployment remains unauthenticated and must not be used for confidential matter data or production publication.
