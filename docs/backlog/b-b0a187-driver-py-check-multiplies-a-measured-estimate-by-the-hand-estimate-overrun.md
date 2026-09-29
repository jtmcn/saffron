---
id: b-b0a187
title: '`driver.py check` applies the hand-estimate overrun to a measured `estimated_lines` and blocks the spec'
status: open
tier: 2
filed: 2026-09-28
closed:
by_hand: true
specs: []
prs: []
commits: []
cites: []
related: [b-43a061, b-db95e1]
---

## Problem

Found in the spec loop's run 20, 2026-09-28.

`SA-0151`'s `estimated_lines: 478` came from a prototype measured with
`size_gate`: 1909 tokens, 64% of the `feature` ceiling (spec lines 479-482).
`check` priced it at 478 times 1.4, 89%, and blocked at `elevated`
(`.claude/skills/run-saffron-spec-loop/driver.py:2057-2058`). The operator ran
it as written. A spec has no way to say its estimate was measured.

## Done looks like

A spec can mark its `estimated_lines` as measured, and `check` prices a measured
estimate at 1.0. `check` prints which basis it used.

## Record

- 2026-09-28: filed from the spec loop's run 20.
- 2026-09-29: hit again in the spec loop's run 21. `check` priced `SA-0188` at
  92%. It landed at 2596 of 3000, then 2732 after review. The prose ratchet
  judges a rewritten docstring as new text, so review grew it.
