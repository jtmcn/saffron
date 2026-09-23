---
id: b-e51967
title: REBUT's extraction turn stops emitting an `<output>` block once SA-0141 lands, and the glossary and §5.3 say every extraction turn does
status: open
tier: 2
by_hand: true
filed: 2026-09-23
specs: [SA-0141]
prs: []
commits: []
cites: [§5.3]
related: [b-4e0868, 42]
---

## Problem

Found 2026-09-23, writing `SA-0141`.

`CONTEXT.md` defines an *extraction turn* as a turn that resumes a session
to emit a validated `<output>` block. It calls that how every structured
artifact is produced. `DESIGN.md` §5.3 says the Agent SDK has no first-class
structured-output guarantee, and quotes the prompt that asks for the block.

`SA-0141` sends REBUT's rebuttal extraction turn and its verdict sessions a
schema through the SDK's `output_format`. The host reads the value from the
result, and neither turn asks for a block. Both documents are `protected`,
so the cell cannot change either.

The glossary entry also reaches both REBUT sessions. It sits in
`CONTEXT.md` §2, which IMPLEMENT and REVIEW both inject
(`saffron/agents/context.py:30-31`).

## Done looks like

The *Extraction turn* entry in `CONTEXT.md` says the turn emits either a
schema-constrained value or an `<output>` block, and that the host validates
both. `DESIGN.md` §5.3 records what the pinned SDK measured, citing
`docs/evidence/2026-09-23-structured-output-spike.md`. It names which turns
use the schema. Both land after `SA-0141` merges, not before.

## Record

- 2026-09-23: filed with `SA-0141`, the first slice of b-4e0868.
