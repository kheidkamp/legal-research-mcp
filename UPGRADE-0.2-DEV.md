# Upgrade checklist: 0.1-dev -> 0.2-dev

1. Upload/replace the repository files from this package.
2. Commit to the branch connected to Render.
3. Wait for Render deploy status `Live`.
4. Verify `https://legal-research-mcp-dev.onrender.com/health` reports `0.2.0-dev`.
5. In Copilot Studio, open `Legal Research DE` and confirm `get_official_document_text` is available/enabled.
6. Run D1 in a new Preview chat.
7. Confirm Activity Trace calls the new tool with the StoFöG official document and returns the Art. 30 passage.
8. Keep the agent unpublished until D1 passes.
