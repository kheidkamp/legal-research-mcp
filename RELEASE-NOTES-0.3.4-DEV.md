# Legal Research MCP 0.3.4-dev - Release Notes

## Scope

Security-hardening release for outbound official-source retrieval. The 0.3.3-dev legal-evidence behavior is preserved; this release changes the network boundary, not the substantive legal-research contract.

## Hardened controls

- HTTPS-only outbound research retrieval.
- Exact official-host allowlists; no wildcard or arbitrary-host fetch path.
- Manual redirect handling with allowlist validation on every hop.
- DNS resolution guard rejects loopback, private, link-local, multicast, unspecified, reserved and other non-global addresses before every request/redirect hop.
- Bounded response sizes for official documents, Gesetze im Internet and BFH search responses.
- Explicit bounded request timeouts across all live retrieval adapters.
- Content-Type allowlists; executable/JavaScript responses are rejected as research content.
- HTML is parsed as inert text; script/style/noscript/svg nodes are removed and no browser/JavaScript runtime is used.

## Preserved behavior

- Read-only MCP operations.
- Existing official-document host allowlist.
- Case-law evidence gate remains fail-closed.
- `get_case`, `get_norm`, `trace_norm_amendments`, `search_primary_sources` and `get_official_document_text` public tool contracts remain unchanged.
- Render DNS-rebinding protection for the MCP ingress remains enabled.

## Tests

`python -m pytest -q`

Expected for this source package: `64 passed`.

The security regression suite covers URL validation, DNS/private-network rejection, redirect escape blocking, response-size limits, timeout fail-closed behavior, Content-Type rejection and inert HTML/script handling.

## Production note

This release closes the local implementation/test portion of the outbound research retrieval controls. A deployed live-runtime confirmation is still required before the corresponding v3 release-blocking controls are treated as closed.
