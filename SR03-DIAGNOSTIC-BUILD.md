# SR03 temporary deployed diagnostic build

Version: `0.3.4-dev-sr03diag1`

Purpose: temporarily deploy the exact SR03 `0.3.4-dev` retrieval-security implementation with a startup-only deterministic diagnostic harness for SR03-LR04 through SR03-LR09.

The security-critical retrieval files remain byte-identical to the clean `0.3.4-dev` candidate:

- `legal_mcp/network_security.py`
- `legal_mcp/official_documents.py`
- `legal_mcp/gesetze_im_internet.py`
- `legal_mcp/bfh_cases.py`

The build adds `legal_mcp/sr03_diagnostics.py`, an HTTP read-only result route at `/sr03/diagnostics`, and changes only the version label plus app startup wiring.

The startup diagnostic uses `httpx.MockTransport` and an injected fake DNS resolver. It performs **zero external network calls**. It checks:

- SR03-LR04 / SEC-RES-004: foreign-host redirect rejected;
- SR03-LR05 / SEC-RES-005: link-local/private DNS result rejected;
- SR03-LR06 / SEC-RES-006: response-size limit enforced;
- SR03-LR07 / SEC-RES-007: timeout fails closed;
- SR03-LR08 / SEC-RES-008: executable/unexpected content type rejected;
- SR03-LR09 / SEC-RES-009: script-node content removed from visible extraction.

The service refuses to start if any of the six diagnostics fails.

After evidence is captured, redeploy the clean `0.3.4-dev` commit. Do not retain this temporary diagnostic route for the final production candidate.
