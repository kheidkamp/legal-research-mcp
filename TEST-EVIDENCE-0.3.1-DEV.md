# Test Evidence – Legal Research MCP 0.3.1-dev

## Triggering runtime defect

Under `0.3.0-dev`, direct `get_case(BFH, IX R 12/22, 2023-05-03, ...)` returned:

- `status=not_found`
- `reason_code=TARGET_CASE_NOT_FOUND_IN_OFFICIAL_BFH_ONLINE_RESEARCH`
- `gate_state=closed`

The fail-closed behavior was safe, but the positive retrieval result was functionally wrong for
an online BFH decision.

## Patch verification

Local automated suite after the patch:

```text
35 passed
```

Coverage includes:

- unchanged pre-2010 fail-closed gate;
- unchanged open-gate service contract for a retrieved official case;
- live-form-state replay including hidden trusted-properties fields;
- exact case+date search;
- quoted full-text fallback;
- ignored/unreflected search submission classified as retryable `unavailable`, not `not_found`;
- definitive reflected no-match with structured diagnostics;
- service-level propagation of diagnostic reason codes.

## Live validation still required

The build environment has no outbound network access. Therefore the final BFH live search must be
validated after Render deployment with `IX R 12/22`.
