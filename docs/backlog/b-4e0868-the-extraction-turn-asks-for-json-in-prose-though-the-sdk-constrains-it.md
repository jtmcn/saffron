---
id: b-4e0868
title: The extraction turn asks for JSON in prose, though the pinned SDK can constrain it to a schema
status: open
tier: 2
filed: 2026-09-23
specs: [SA-0141]
cites: [§5.3]
related: [42, 60]
---

## Problem

§5.3 says the Agent SDK has no first-class structured-output guarantee. That
was true when it was written. It is false for the SDK the cell image pins.

`claude-agent-sdk==0.2.142` (`images/cell-base.python.Dockerfile`) accepts
`ClaudeAgentOptions.output_format` as `{"type": "json_schema", "schema": ...}`.
It hands the schema to the bundled CLI as `--json-schema`. The parsed value
comes back on `ResultMessage.structured_output`. Read from the wheel itself,
2026-09-23.

Saffron uses none of it. Every extraction turn asks for an `<output>` block in
prose, and the host finds it with a regex. Two measured losses came from that
gap:

- Item 42, `SA-0040`: a rebuttal lost to `Illegal trailing comma`, after a
  turn that cost $2.59. The body then read as a confirmed disagreement.
- Item 60, `SA-0053`: a lens report missing `findings.0.severity` ended the
  attempt at $3.61. The fix was a re-prompt, which costs a whole turn.

A schema-constrained turn rules out both shapes.

`images/agent_runner.py` drops the field today. Its `result` event carries no
`structured_output`, so the host could not read it even if a turn asked.

## Done looks like

Three questions, answered in a real cell before any spec is written:

1. Does `--json-schema` hold on a resumed session in the pinned CLI? The
   extraction turn resumes the implementer's session, so a fresh one is no
   substitute.
2. Does the CLI accept the schemas Pydantic generates for `Plan`,
   `ScopeProposal`, the lens report and the rebuttal? Those use
   `extra="forbid"` and `Literal` fields.
3. What does a turn that cannot satisfy the schema return? The SDK source
   names no `subtype` for it.

If all three pass, one spec does the rest:

- The runner's `result` event carries `structured_output`.
- Each extraction turn sends `model_json_schema()` and reads the result.
- §5.3 records what the SDK now does.

The host still validates with Pydantic, because the runner runs inside the cell
and can forge any field. The semantic checks in `validate_plan` and
`validate_scope_proposal` stay. The prompt forbidding file changes stays. The
re-prompt stays as the backstop.

**Not** Jev. TypeSafe's System One also guarantees its output, but only as a
closed answer: a yes-or-no probability, a distribution over labels, or a score.
A plan, a finding's claim and a rebuttal's argument are free text. Jev also
reads supplied state and cannot resume the session that did the work.

Jev could fit a closed field that a free-text artifact carries, such as a
finding's severity. That makes a vendor load-bearing inside a task. The
observer design keeps Jev outside core, and nothing reads its scores yet. So
that choice waits on the observer's record, and this item does not make it.

## Record

- 2026-09-23: filed from a session asking whether to adopt Pydantic AI.
  The answer was no. The extraction turn already does what Pydantic AI
  offers, and the SDK option does it more cheaply.
- 2026-09-23: `SA-0141` written, the first slice. It covers REBUT's rebuttal
  extraction turn and its verdict sessions. REVIEW, the plan checkpoint and
  the notes turn are later slices.
