# Upgrade to 0.3.4-dev

1. Replace the Render DEV repository with this package (or apply the accompanying 0.3.3-to-0.3.4 diff).
2. Commit and push to the branch used by the Render service.
3. Wait for the deployment to become Live.
4. Verify `/health` reports `0.3.4-dev`.
5. Refresh/rebind the Copilot Studio `Legal Research DE` MCP connection if required.
6. Re-run the existing positive BFH `IX R 12/22` and closed pre-2010 case-gate controls.
7. Run the SR03 live retrieval-security confirmation.

Do not publish to production from this DEV release. Authentication, platform/DLP and final v3 permission gates remain separate controls.
