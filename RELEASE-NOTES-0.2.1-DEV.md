# Legal Research MCP 0.2.1-dev

Compatibility patch for Microsoft Copilot Studio tool registration.

## Changed

- Simplified the public `get_official_document_text` MCP input schema to exactly three required strings:
  - `document_ref`
  - `locator`
  - `query`
- Removed nullable/union parameters and optional tuning parameters from the public tool schema.
- `document_ref` accepts either a supported official document ID or an allowlisted official HTTPS URL; ID-vs-URL resolution now happens inside the server.
- Kept the existing official-document adapter, SSRF protections, PDF/HTML parsing, passage hashing, page-aware evidence, and verification semantics unchanged.
- Service/health/tool envelope version: `0.2.1-dev`.

## Purpose

Copilot Studio displayed the 0.2.0-dev tool in MCP configuration but did not expose it to the Preview orchestrator. This patch minimizes the JSON Schema surface without weakening evidence or security controls.
