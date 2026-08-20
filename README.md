# Legal Research MCP MVP 0.1-dev - Render Free

Render-ready connectivity MVP for the planned `legal-tax-advisor-de` v2.3.0 research layer.

## What it does now

- `search_primary_sources`: controlled discovery for a small validated registry (KStG, EStG, AO, GewStG). Discovery only.
- `get_norm`: retrieves the current official consolidated provision from `gesetze-im-internet.de` and returns structure/evidence metadata.
- `trace_norm_amendments`: safe connectivity implementation. It may expose a whole-statute amendment header as a discovery lead, but deliberately returns `partial/unknown` and never sets `latest_verified_amendment` until a provision-specific resolver exists.

This last behavior is intentional: it prevents the RC2/RC3 class of false "latest amendment" assertions.

## Render deployment

Use the included `render.yaml` Blueprint. The service is configured as:

- Web Service
- Docker runtime
- Free plan
- Frankfurt region
- `/health` health check
- dynamic binding to Render's `PORT`
- MCP endpoint at `/mcp`
- explicit Host allowlisting from `RENDER_EXTERNAL_HOSTNAME`

Detailed steps: `docs/render-free-deploy.md`.

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
uvicorn app:app --reload --port 8080
```

Local endpoints:

- Health: `http://localhost:8080/health`
- MCP: `http://localhost:8080/mcp`

## Not implemented yet

- historical statutory versions;
- provision-specific amendment-chain resolution;
- Bundesgesetzblatt / recht.bund.de adapter;
- Bundestag/Bundesrat legislative-material adapter;
- case law and BMF guidance;
- production authentication.

## DEV security boundary

The first Render deployment is intentionally unauthenticated to isolate protocol/connectivity testing. It is a DEV proof of concept only. Do not publish the Copilot agent and do not send confidential client/matter facts through the endpoint.

Free Render Web Services spin down after 15 minutes of inactivity and are not intended for production use.

## Copilot Studio handshake

Keep the existing v2.2.3 skill unchanged until the Render MCP endpoint is live and the three tools have been exercised successfully in Activity Trace.
