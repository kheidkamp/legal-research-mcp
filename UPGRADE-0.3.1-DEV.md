# Upgrade to Legal Research MCP 0.3.1-dev

1. Replace the Render DEV repository contents with this package, or apply the dedicated GitHub
   update package.
2. Commit/push to the branch deployed by Render.
3. Wait until Render is Live.
4. Verify `/health` returns `version: 0.3.1-dev`.
5. In Copilot Studio, open the existing `Legal Research DE` MCP server and confirm `get_case`
   remains present. No agent-skill change is required for this patch.
6. Run the positive direct `get_case` test:
   - court: `BFH`
   - case_number: `IX R 12/22`
   - decision_date: `2023-05-03`
   - focus: `Gewinnerzielungsabsicht Gestaltungsmissbrauch Veräußerungsverlust`
7. Expected positive gate:
   - `status=ok`
   - `coverage_status=complete`
   - `data.case` is populated from the official BFH decision
   - `data.content_gate.gate_state=open`
   - `data.content_gate.target_case_content_allowed=true`
   - `data.content_gate.target_case_primary_text_verified=true`
8. Re-run the pre-2010 negative control `VIII R 10/96 – 1998-07-07`; it must remain closed.

If the positive target still cannot be opened, capture the full `get_case` output. In 0.3.1-dev,
`search_diagnostics` should identify whether the failure occurred in form discovery, search
submission, exact matching, or document opening.
