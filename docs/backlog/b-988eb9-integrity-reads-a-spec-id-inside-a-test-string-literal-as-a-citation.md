---
id: b-988eb9
title: The integrity gate reads a spec id inside a test's string literal as a citation, so a fixture must split the literal
status: open
tier: 3
filed: 2026-11-17
closed:
specs: []
prs: []
commits: []
cites: [§5.4]
related: [b-249808]
---

## Problem

Found by both review seats on #1241 (`SA-0405`), in the spec loop's run 76.

`SA-0405`'s spec gives a fixture string, `x stayed green with SA-1's wrong
version y`. `integrity`'s `unknown-spec-id` check reads `SA-1` there as a
citation of a spec that does not exist (`saffron/gates/core/integrity.py`,
`_cited_ids`). The cell split the literal around `SA-1` to pass the gate.
The same id opening a literal, as in `"SA-1's wrong version here"`, passes.

The split hides fixture data from the gate, and nothing marks it as
sanctioned. The operator kept it for #1241.

## Done looks like

A spec id that a test's string literal holds as fixture data passes the
`unknown-spec-id` check unsplit. A real citation in a comment or docstring
still fails it.

## Record

- 2026-11-17: filed from the spec loop's run 76, from #1241's review.
