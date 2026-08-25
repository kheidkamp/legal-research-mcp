# Upgrade to 0.3.3-dev

1. Replace the files from the 0.3.3-dev GitHub update archive in the existing repository.
2. Commit and push.
3. Wait for Render deployment.
4. Verify `/health` reports `0.3.3-dev`.
5. Do not change the agent skill.
6. Test `get_case(BFH, IX R 12/22, 2023-05-03)` directly.
7. If the gate opens, run the original S9 positive agent test.
8. Re-run `VIII R 10/96` as the negative pre-2010 control.
