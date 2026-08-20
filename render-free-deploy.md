# Render Free deployment and 0.2-dev upgrade

This document deploys/upgrades the Legal Research MCP DEV service on Render Free in Frankfurt.

## Security boundary

This deployment is intentionally unauthenticated and is only for DEV connectivity/research testing with Copilot Studio.
Do not publish the Copilot agent and do not send confidential client or matter facts through this endpoint.
Free Render services are not intended for production use.

## Existing 0.1-dev service: upgrade path

If `legal-research-mcp-dev` is already connected to the GitHub repository:

1. Replace/add the files from the 0.2-dev package in the repository root.
2. Commit and push to the branch Render deploys.
3. Render should start a new deploy automatically.
4. Wait for status `Live`.
5. Open:

`https://legal-research-mcp-dev.onrender.com/health`

Expected JSON:

```json
{"status":"healthy","service":"legal-research-mcp","version":"0.2.0-dev"}
```

The MCP endpoint remains:

`https://legal-research-mcp-dev.onrender.com/mcp`

## New repository / service path

The repository root must contain at least:

- `render.yaml`
- `Dockerfile`
- `app.py`
- `mcp_server.py`
- `requirements.txt`
- `legal_mcp/`

Recommended path: create/apply the included Render Blueprint.

## DNS-rebinding protection

The MCP Python SDK validates the HTTP Host header. This project reads Render's runtime variable `RENDER_EXTERNAL_HOSTNAME` and adds that exact hostname to the MCP allowlist.

If you later attach a custom domain, set:

`MCP_PUBLIC_HOSTNAME=legal-mcp.example.de`

and redeploy.

## Copilot Studio after the server update

The MCP server now exposes four tools:

- `search_primary_sources`
- `get_norm`
- `trace_norm_amendments`
- `get_official_document_text`

Open the existing `Legal Research DE` tool in Copilot Studio and verify that the fourth tool is visible and enabled. If the exposed-tool list does not refresh automatically, edit/save the existing MCP server entry so Copilot Studio reconnects and rereads the server tool list.

If individual MCP tools were selectively enabled rather than `Allow all`, explicitly enable the new tool.

## D1 verification after 0.2-dev deploy

Start a new Preview chat and run the existing D1 prompt.

In Activity Trace, the desired path is approximately:

```text
trace_norm_amendments
  -> candidate identified
  -> get_official_document_text
       document_id = BR-Drs. 5/26
       locator     = Artikel 30
       query       = § 8b Absatz 6 Satz 2
  -> final answer
```

The new tool should return a passage from the official document containing the concrete command that § 8b Absatz 6 Satz 2 is replaced. The agent must still independently close the later amendment period before making a definitive latest-amendment statement.

## Free-instance behavior

Render Free Web Services can spin down after inactivity. The first request after idle can be slow. This is acceptable for the DEV proof of concept.
