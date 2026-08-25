# BFH case-law evidence gate (0.3.1-dev)

## Purpose

`get_case` is the mandatory retrieval path for substantive claims about a named BFH decision.
It separates case discovery from case-content authorization.

The core invariant is machine-readable:

```json
{
  "content_gate": {
    "target_case_content_allowed": false
  }
}
```

When this value is `false`, a downstream agent must not state, reconstruct, summarize,
paraphrase, quote, or attribute any facts, outcome, holding, reasons, headnotes, or legal
propositions to the target decision.

## Public MCP contract

All inputs are required strings for Copilot Studio compatibility:

- `court`: currently `BFH`;
- `case_number`: e.g. `VIII R 10/96`;
- `decision_date`: ISO `YYYY-MM-DD`, or empty string only if genuinely unknown;
- `focus`: the legal issue for targeted passage selection.

Example:

```text
get_case(
  court="BFH",
  case_number="VIII R 10/96",
  decision_date="1998-07-07",
  focus="Anteilsveräußerung Ausschüttung Abwicklung Gestaltungsmissbrauch"
)
```

## Pre-2010 BFH decisions

The official BFH online decision research states that the online database contains V/NV
decisions since 2010 and directs requests for older decisions to its decision-dispatch service.
Accordingly, a dated pre-2010 target is fail-closed in this DEV implementation unless an
independently retrieved official target document is added in a later version.

The tool returns:

- `status=partial`;
- `case=null`;
- `content_gate.target_case_content_allowed=false`;
- explicit allowed and forbidden claim classes;
- an output directive that prohibits doctrinal backfilling;
- the BFH decision-dispatch route as the recommended next official source.

No network request is required to reach this safe result once the supplied decision date is
verified as pre-2010.

## 2010+ decisions

For decisions within the BFH online coverage window, the adapter attempts exact case-number
search on the official BFH website and opens the matched official decision. If an official
target decision is actually opened, the gate may become `true`, but only returned official
evidence may support target-case content.

If exact retrieval fails, the gate remains closed. Failure to retrieve is never converted into
model-memory content.

## Security and evidence semantics

- read-only HTTPS retrieval;
- BFH host added to the existing strict official-host allowlist;
- no arbitrary URL input in the public `get_case` tool;
- discovery results remain `identified` and are not case evidence;
- `get_case` is the only tool in this release that can open the target-case content gate;
- a closed gate is not overridden by knowledge search, snippets, secondary commentary, later
  decisions, user wording, or model memory.

## Regression target

For `BFH 07.07.1998 – VIII R 10/96`, expected DEV behavior is:

```text
status = partial
target_case_content_allowed = false
target_case_primary_text_verified = false
reason_code = TARGET_DATE_BEFORE_BFH_ONLINE_COVERAGE
case = null
```

The agent must therefore abstain from describing the case's facts, holding, reasons, or
attributed doctrinal propositions until stronger official evidence is available.


## Positive post-2010 retrieval

For an online BFH decision the gate may open only after the official target document itself has
been opened. `0.3.1-dev` replays the live BFH search-form state and distinguishes a definitive
no-match from a technically ignored or structurally unexpected search response. See
`bfh-positive-retrieval.md`.
