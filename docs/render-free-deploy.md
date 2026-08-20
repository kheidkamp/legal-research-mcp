# Render Free deployment

This document deploys the Legal Research MCP connectivity MVP as a free Render Web Service in Frankfurt.

## Security boundary

This deployment is intentionally unauthenticated and is only for DEV connectivity testing with Copilot Studio.
Do not publish the Copilot agent and do not send confidential client or matter facts through this endpoint.
Free Render services are not intended for production use.

## 1. Put the project in a Git repository

Render deploys Git-backed services from GitHub, GitLab, or Bitbucket repositories you connect to your Render account.
Create a new private repository, copy the contents of this project into the repository root, and push it.
The repository root must contain at least:

- `render.yaml`
- `Dockerfile`
- `app.py`
- `mcp_server.py`
- `requirements.txt`
- `legal_mcp/`

Do not commit `.env` files or credentials.

## 2. Create the Render service

Recommended path: use the included Blueprint.

1. Sign in to the Render Dashboard.
2. Create a new Blueprint and connect the repository.
3. Keep the Blueprint path as `render.yaml`.
4. Review the planned service:
   - type: Web Service
   - runtime: Docker
   - plan: Free
   - region: Frankfurt
   - health check: `/health`
5. Create/apply the Blueprint.

Render builds the Docker image and starts the service. The Docker container binds to Render's `PORT` environment variable (default `10000`).

## 3. Verify deployment

When the deploy is Live, Render shows the public URL, for example:

`https://legal-research-mcp-dev.onrender.com`

Open:

`https://<your-host>/health`

Expected JSON:

```json
{"status":"healthy","service":"legal-research-mcp","version":"0.1.0-dev"}
```

The MCP endpoint is:

`https://<your-host>/mcp`

Do not judge `/mcp` by opening it in a normal browser tab. MCP uses protocol-specific HTTP requests. Test the endpoint from Copilot Studio or an MCP client.

## 4. DNS-rebinding protection

The MCP Python SDK validates the HTTP Host header. This project reads Render's runtime variable `RENDER_EXTERNAL_HOSTNAME` and adds that exact hostname to the MCP allowlist. This avoids a common `421 Misdirected Request / Invalid Host header` failure without disabling DNS-rebinding protection.

If you later attach a custom domain, set this Render environment variable manually:

`MCP_PUBLIC_HOSTNAME=legal-mcp.example.de`

Then redeploy.

## 5. Free-instance behavior

Render Free Web Services spin down after 15 minutes without inbound traffic. The first request after idle can therefore be slow. This is acceptable for the connectivity proof of concept but is not a production target.

## 6. Next step in Copilot Studio

Keep the existing v2.2.3 skill unchanged.

In the DEV agent:

1. Build -> Tools -> Add a tool -> Model Context Protocol (MCP).
2. Name: `Legal Research DE`.
3. Server URL: `https://<your-host>/mcp`.
4. Authentication: None (DEV connectivity test only).
5. Add the server and verify that these tools appear:
   - `search_primary_sources`
   - `get_norm`
   - `trace_norm_amendments`
6. In Preview, inspect Activity Trace during the test prompts.

Only after this succeeds should v2.3.0-alpha1 change the skill/router.
