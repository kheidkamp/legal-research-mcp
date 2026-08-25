# GitHub update – 0.3.1-dev

Targeted patch from `0.3.0-dev` to `0.3.1-dev` for BFH positive case retrieval.

Recommended commit message:

```text
fix: harden live BFH case search submission
```

After push, verify Render `/health` reports `0.3.1-dev`, then run the positive `IX R 12/22`
`get_case` test before resuming RC2 release testing.

The agent skill is intentionally unchanged.
