# GitHub update 0.2.0-dev -> 0.2.1-dev

This patch changes only the public MCP contract for `get_official_document_text` plus tests/docs/version metadata.

## Root files to replace/add

Replace:
- `mcp_server.py`
- `README.md`
- `SHA256SUMS.txt`

Add:
- `RELEASE-NOTES-0.2.1-DEV.md`
- `UPGRADE-0.2.1-DEV.md`
- `GITHUB-UPDATE-0.2.1-DEV.md`

## `legal_mcp/`

Replace:
- `legal_mcp/__init__.py`

No other `legal_mcp` implementation file changes.

## `tests/`

Replace:
- `tests/test_official_documents.py`

Add:
- `tests/test_mcp_contract.py`

No fixture changes are required.

## `docs/`

Replace:
- `docs/official-document-retrieval.md`
- `docs/render-free-deploy.md`

No other docs are required for the compatibility patch.

## After commit

1. Wait for Render auto-deploy.
2. Open `/health` and confirm `0.2.1-dev`.
3. Refresh/rebind `Legal Research DE` in Copilot Studio.
4. Run the isolated tool test first:

   `document_ref = BR-Drs. 5/26`

   `locator = Artikel 30 Nummer 1`

   `query = § 8b Absatz 6 Satz 2`

5. Only after the direct tool invocation appears in Activity Trace, rerun D1.
