# Test Evidence – Legal Research MCP 0.3.2-dev

Local test suite result: **38 passed**.

New regression coverage includes:

1. Form missing + exact result returned through direct GET -> exact case hit accepted.
2. Form missing + no exact result + no reflected query -> `BFH_SEARCH_DIRECT_FALLBACK_UNVERIFIED` and retryable fail-closed behavior.
3. Service envelope preserves `gate_state=closed` and `retryable=true` for the unverified direct fallback.
4. Existing live-form replay, quoted-fulltext fallback, ignored-query detection, definitive no-match diagnostics, pre-2010 gate, official-document retrieval and other MCP tests remain green.

The local suite cannot prove live BFH connectivity because the build container has no outbound DNS/network access. Live verification on Render remains mandatory.
