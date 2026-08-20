# Production hardening after the Render DEV proof of concept

The free Render deployment is intentionally unauthenticated so MCP protocol/connectivity can be isolated first. Do not publish the Copilot agent or send confidential matter facts through this DEV endpoint.

Before production:

1. Add OAuth 2.0 authentication compatible with Copilot Studio rather than leaving the MCP public.
2. Keep DNS-rebinding protection enabled and allow only the actual public MCP hostname(s).
3. Keep the research MCP read-only.
4. Preserve the strict official-document URL allowlist and redirect-hop validation; do not replace it with arbitrary URL fetching.
5. Keep document download-size and request-size limits; add rate limiting and abuse protection.
6. Log tool metadata, status, latency, source identifiers and evidence identifiers; do not log full user prompts or confidential matter text by default.
7. Pin and regularly update the MCP SDK, PDF parser, HTTP client and other dependencies, including security patches.
8. Move from a sleeping Free instance to a production plan or another production-grade hosting setup if latency/SLA matters.
9. Add malware/content-type controls if future versions accept user-supplied files rather than official read-only URLs.
10. Re-run the full v2.3.0 contract and regression suites before publication.

Microsoft Entra ID can still be used as the OAuth identity provider even when the MCP application itself is hosted on Render; the hosting platform and identity provider do not have to be the same.
