# Test Evidence – 0.3.0-dev

## Automated tests

`python -m pytest -q`

Expected: all tests pass.

Coverage includes:

- legislation discovery remains discovery-only;
- current norm retrieval and historical downgrade;
- official amendment-document retrieval;
- SSRF/official-host safety;
- Copilot-compatible simple `get_case` public contract;
- named BFH case discovery remains `identified` and requires `get_case`;
- pre-2010 named case returns a closed content gate without target-case content;
- opened post-2010 official target case can open the gate only with returned evidence.

## Direct deterministic regression

Input:

```text
court=BFH
case_number=VIII R 10/96
decision_date=1998-07-07
focus=Anteilsveräußerung Ausschüttung Abwicklung Gestaltungsmissbrauch
```

Expected key output:

```json
{
  "status": "partial",
  "data": {
    "case": null,
    "content_gate": {
      "target_case_content_allowed": false,
      "target_case_primary_text_verified": false,
      "reason_code": "TARGET_DATE_BEFORE_BFH_ONLINE_COVERAGE"
    }
  }
}
```
