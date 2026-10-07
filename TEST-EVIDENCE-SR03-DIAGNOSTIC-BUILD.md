# SR03 deployed diagnostic build - local evidence

Date: 2026-10-07

Baseline: clean Legal Research MCP `0.3.4-dev` security-hardening package.

Local regression after adding the temporary startup diagnostic harness:

```text
65 passed
```

The 65 tests comprise the clean 0.3.4 suite plus `tests/test_sr03_deployed_diagnostics.py`.
The deterministic startup self-test reports:

```text
cases_verified=6
cases_pass=6
cases_fail=0
external_network_calls=0
mock_transport_only=true
overall=PASS
```

Security-critical files are byte-identical to clean 0.3.4-dev. See
`SR03-DIAGNOSTIC-SECURITY-CRITICAL-HASHES.txt`.

This build is temporary DEV evidence tooling only. After capturing `/sr03/diagnostics`,
redeploy the clean 0.3.4-dev commit and verify `/health` again.
