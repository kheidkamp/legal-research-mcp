# Legal Research MCP Interface v0.2

## Status

This is the interface delta for Legal Research MCP implementation `0.3.1-dev`.
It preserves the v0.1 evidence model and adds a binding machine-readable gate for named BFH
case content.

## Normative rule for named cases

For every substantive claim about a named BFH decision, call `get_case` first.

The field below is authoritative for target-case content generation:

```json
{
  "data": {
    "content_gate": {
      "gate_version": "1",
      "gate_state": "closed | open",
      "must_stop_target_case_content": true,
      "target_case_content_allowed": false
    }
  }
}
```

If `target_case_content_allowed=false` or `must_stop_target_case_content=true`, no downstream
agent may state, reconstruct, summarize, paraphrase, quote, or attribute target-case facts,
holding, reasons, headnotes, or legal propositions.

A closed gate cannot be overridden by discovery results, knowledge-search snippets, secondary
sources, user wording, model memory, or later decisions.

## Tool: get_case

### Input

All fields are required strings for Copilot Studio compatibility.

```json
{
  "court": "BFH",
  "case_number": "VIII R 10/96",
  "decision_date": "1998-07-07",
  "focus": "Anteilsveräußerung Ausschüttung Abwicklung Gestaltungsmissbrauch"
}
```

`decision_date` may be an empty string only if genuinely unknown.

### Closed-gate output

```json
{
  "status": "partial | not_found | unavailable | error",
  "data": {
    "case": null,
    "input_reference": {
      "court": "BFH",
      "case_number": "VIII R 10/96",
      "decision_date": "1998-07-07",
      "verification_level": "user_supplied_or_parsed_input"
    },
    "content_gate": {
      "gate_version": "1",
      "gate_state": "closed",
      "must_stop_target_case_content": true,
      "target_case_content_allowed": false,
      "target_case_primary_text_verified": false,
      "later_judicial_description_verified": false,
      "reason_code": "...",
      "allowed_claim_classes": [],
      "forbidden_claim_classes": [],
      "output_directive": "..."
    }
  }
}
```

### Open-gate output

An open gate is permitted only after the official target decision has actually been opened.
The tool returns the official source plus checked evidence passages. Target-case content may be
stated only to the extent supported by those returned passages.

## BFH online coverage

The current official BFH online decision research states that V/NV decisions since 2010 are
available online and directs users seeking earlier decisions to its decision-dispatch service.
Accordingly, the DEV adapter fails closed for a dated pre-2010 target rather than reconstructing
case content.

## Versioning

This is a backward-compatible evidence-field addition to the v0.1 interface and therefore a
minor interface revision.


## Additive diagnostic field in 0.3.1-dev

Closed `get_case` responses caused by post-2010 search/retrieval problems may include
`data.search_diagnostics`. This field is diagnostic only and never opens the target-case content
gate.
