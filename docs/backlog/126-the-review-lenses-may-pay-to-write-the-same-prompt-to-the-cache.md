---
id: 126
title: The REVIEW lenses may pay to write the same prompt to the cache three times
status: open
filed: 2026-09-14
specs: [SA-0090]
prs: []
commits: []
cites: []
related: []
---

## Problem

Found 2026-09-14 checking REVIEW against the prompt-cache advice in
`keli-wen/agentic-harness-patterns-skill`.

The three lenses run one after another with the same tools, and most of each
system prompt is the same five values: the vocabulary sections (21,600
characters on this repo), `CLAUDE.md` (12,372), the gate table, the diff and the
task. Each template opens with its own lens's paragraph, and puts its remit,
severity and output text before four of the five. `agent_options` sets the
one-hour TTL on every session, and a one-hour cache write costs twice base
input where a read costs a tenth. Cells authenticate with a subscription token,
so the cost is plan usage and rate-limit headroom rather than an invoice, and
`total_cost_usd` is the client's estimate of it.

Reordering the templates is not enough. A cache read lands only where an
earlier request placed a breakpoint, and the CLI, not Saffron, places them.
`system_prompt` is one string, so a breakpoint at its end still covers each
lens's own text. A shape that could work keeps the system prompt byte-identical
across the lenses and moves each remit into the turn's prompt. That holds only
if the CLI puts a breakpoint at the end of the system prompt, which nobody has
checked.

## Done looks like

`SA-0090`'s per-step counts, read from one night's event log after a base-image
rebuild, showing what the second and third lens's *first* step read from the
cache. A result's counts cannot answer this: they are cumulative over the
session's steps, and every later step reads the session's own earlier writes.
If the first step reads only the tools, a spec for the shape above, ratified only after a lens-scoring
comparison, because moving a remit out of the system prompt can change what the
lens finds. The verdict template and the one-hour TTL on lens sessions are
settled from the same numbers.

## Record

- 2026-09-14: drafted as a spec in PR #261 and withdrawn in its review, because
  reordering the templates could not produce a cache read.
