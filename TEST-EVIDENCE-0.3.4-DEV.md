# Test Evidence - Legal Research MCP 0.3.4-dev

## Baseline

Source baseline: `legal-research-mcp-render-mvp-0.3.3-dev.zip`

Baseline SHA-256:

`f01865b8decc2a2c06f8d9a989fb2c37b42c4d1b863fe72851bfe5c868568a1c`

Baseline local suite before hardening: `39 passed`.

## Hardened suite

Command:

`python -m pytest -q`

Expected: `64 passed`.

New regression file: `tests/test_research_network_security.py`.

### Security controls exercised

- HTTPS downgrade rejection.
- Exact-host allowlist enforcement.
- Credentials and non-standard HTTPS ports rejected.
- Public-DNS guard rejects private, loopback, link-local and local IPv6 targets.
- Redirect from an allowlisted official host to a non-allowlisted host fails closed.
- Response-size limits enforced both by declared length and streamed byte count paths.
- Timeouts map to fail-closed upstream/source unavailable states.
- JavaScript Content-Type rejected.
- HTML script content is removed and not surfaced as source text.
- No browser/JavaScript execution dependency is present.

## Runtime requirement

Local deterministic tests do not prove the deployed Render instance is running 0.3.4-dev. After deployment, verify `/health` and perform the SR03 live retrieval/security confirmation before closing SEC-RES-002 through SEC-RES-009.
