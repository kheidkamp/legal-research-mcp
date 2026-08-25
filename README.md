# Legal Research MCP MVP 0.3.0-dev - Render Free

Render-ready read-only research MCP for the planned `legal-tax-advisor-de` v2.3.0 research layer.

## What 0.3.0-dev changes

0.3.0-dev hardens named BFH case research with a structured evidence gate. The trigger was a
repeated failure mode in which an agent correctly recognized that an older target decision was
not available in the official online source but still reconstructed and attributed a supposed
holding from other material.

- adds public `get_case(court, case_number, decision_date, focus)`;
- returns a binding machine-readable `content_gate`;
- pre-2010 BFH target decisions fail closed under the official online coverage limitation;
- named-case discovery now points explicitly to `get_case`;
- adds initial official BFH retrieval for 2010+ decisions;
- retains the existing norm/amendment/document tools and security boundary.

## Tools

### `search_primary_sources`
Controlled discovery for a small validated legislation registry (KStG, EStG, AO, GewStG). Discovery only.

### `get_norm`
Retrieves the current official consolidated provision from `gesetze-im-internet.de` and returns structure/evidence metadata.

### `trace_norm_amendments`
Safe amendment-history connectivity implementation. It may expose a whole-statute amendment header as a discovery lead but deliberately remains `partial/unknown` until a provision-specific chain resolver is implemented.

### `get_case`
Mandatory target-case retrieval/evidence gate for named BFH decisions. If
`data.content_gate.target_case_content_allowed=false`, no facts, holding, reasons, headnotes,
quotes, paraphrases, or attributed legal propositions may be stated about the target case.

See `docs/case-law-evidence-gate.md`.

### `get_official_document_text`
Opens an identified official document and verifies an exact passage.

Public MCP inputs (all required strings):

- `document_ref`: supported official document ID or allowlisted official HTTPS URL;
- `locator`: targeted location such as `Artikel 30 Nummer 1`;
- `query`: exact phrase to verify such as `§ 8b Absatz 6 Satz 2`.

Supported document-id shortcuts include:

- `BR-Drs. 5/26` -> Bundesrat document server PDF;
- `BT-Drs. 21/3343` -> Bundestag document server PDF;
- `BGBl. 2026 I Nr. 33` -> official `recht.bund.de` promulgation page.

Example amendment verification target:

```text
get_official_document_text(
  document_ref="BR-Drs. 5/26",
  locator="Artikel 30 Nummer 1",
  query="§ 8b Absatz 6 Satz 2"
)
```

A successful normalized query match returns `coverage_status=complete` and `full_checked` passage evidence. A locator-only result is navigation evidence and must not be treated as proof of the requested amendment phrase.

## Public schema target

The Copilot-facing contract is intentionally simple:

```json
{
  "type": "object",
  "properties": {
    "document_ref": {"type": "string"},
    "locator": {"type": "string"},
    "query": {"type": "string"}
  },
  "required": ["document_ref", "locator", "query"]
}
```

## SSRF / download safety

`get_official_document_text` remains deliberately constrained:

- HTTPS only;
- exact official-host allowlist;
- every redirect hop is revalidated;
- credentials and non-standard ports are rejected;
- download size capped at 20 MB;
- PDF text extraction only, no JavaScript/browser execution;
- read-only requests only.

Current allowlisted families include the official Bundestag/Bundesrat document server, `recht.bund.de`, `gesetze-im-internet.de`, Bundestag/Bundesrat web hosts, the Federal Ministry of Finance website, and the Bundesfinanzhof website.

## Render deployment

Use the included `render.yaml` Blueprint. The service remains configured as:

- Web Service;
- Docker runtime;
- Free plan;
- Frankfurt region;
- `/health` health check;
- dynamic binding to Render's `PORT`;
- MCP endpoint at `/mcp`;
- explicit Host allowlisting from `RENDER_EXTERNAL_HOSTNAME`.

Detailed steps: `docs/render-free-deploy.md`.

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest -q
uvicorn app:app --reload --port 8080
```

Local endpoints:

- Health: `http://localhost:8080/health`
- MCP: `http://localhost:8080/mcp`

## Still not implemented

- historical statutory version resolver;
- complete provision-specific amendment-chain resolver;
- automatic discovery of every Bundesgesetzblatt/Bundestag/Bundesrat document;
- broader multi-court case-law retrieval and citation graph;
- comprehensive BMF guidance retrieval;
- production authentication.

## DEV security boundary

The Render Free deployment remains intentionally unauthenticated for DEV testing. Do not publish the Copilot agent and do not send confidential client/matter facts through the endpoint.

Free Render Web Services can spin down after inactivity and are not a production target.

## 0.2.1 -> 0.3.0 upgrade

1. Replace the repository contents with the 0.3.0-dev package and commit/push to the branch Render deploys.
2. Wait for the Render deployment to become Live.
3. Verify `/health` returns version `0.3.0-dev`.
4. In Copilot Studio, refresh or rebind the existing `Legal Research DE` MCP server and verify that the new `get_case` tool is visible in Preview.
5. Run the direct pre-2010 case-gate test from `UPGRADE-0.3.0-DEV.md`.
6. Only after that gate is confirmed, update the agent skill so named BFH case research must call `get_case`.

See `UPGRADE-0.3.0-DEV.md`, `docs/case-law-evidence-gate.md`, and `docs/render-free-deploy.md`.
