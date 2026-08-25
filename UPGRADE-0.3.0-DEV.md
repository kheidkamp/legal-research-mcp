# Upgrade to Legal Research MCP 0.3.0-dev

1. Replace the repository contents with this package and commit/push to the branch deployed by
   Render.
2. Wait for Render to deploy and become Live.
3. Open `/health` and verify `version` is `0.3.0-dev`.
4. In Copilot Studio, refresh/rebind the existing `Legal Research DE` MCP server so the new
   `get_case` tool becomes visible.
5. Directly test `get_case` with:
   - court: `BFH`
   - case_number: `VIII R 10/96`
   - decision_date: `1998-07-07`
   - focus: `Anteilsveräußerung Ausschüttung Abwicklung Gestaltungsmissbrauch`
6. Expected gate:
   - `status=partial`
   - `target_case_content_allowed=false`
   - `reason_code=TARGET_DATE_BEFORE_BFH_ONLINE_COVERAGE`
   - `case=null`
7. Do **not** change the agent skill yet. First confirm the MCP contract in Preview. After that,
   update the skill routing so every named BFH decision must call `get_case` before target-case
   content is generated.
