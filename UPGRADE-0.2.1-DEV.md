# Upgrade 0.2.0-dev -> 0.2.1-dev

1. Replace the changed root files and package files in the existing GitHub repository.
2. Keep the existing Render service and MCP URL unchanged.
3. Let Render auto-deploy the new commit.
4. Verify `/health` reports `0.2.1-dev`.
5. In Copilot Studio, refresh/rebind the existing `Legal Research DE` MCP server if needed.
6. Verify `get_official_document_text` appears and can be invoked in Preview.

The public tool now requires exactly `document_ref`, `locator`, and `query`, all strings.
