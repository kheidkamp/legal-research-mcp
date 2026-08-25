# Upgrade to Legal Research MCP 0.3.2-dev

1. Apply the `0.3.2-dev` repository update to the currently deployed 0.3.1-dev repository.
2. Commit and push to the branch used by Render.
3. Wait for Render to report the deployment as Live.
4. Verify `/health` returns `version: 0.3.2-dev`.
5. No `legal-tax-advisor-de` skill change is required.
6. Directly test `get_case` with:
   - court: `BFH`
   - case_number: `IX R 12/22`
   - decision_date: `2023-05-03`
   - focus: `Anteilsveräußerung, Gestaltungsmissbrauch, Veräußerung eigener Anteile`
7. PASS target: official target decision opened and `data.content_gate.gate_state=open` / `target_case_content_allowed=true`.
8. If still closed, capture the complete `search_diagnostics` object before further changes.
9. Re-run `VIII R 10/96`, `1998-07-07` as the negative pre-2010 control; it must remain closed.
