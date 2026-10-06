---
id: b-d269f4
title: "The view server exits 1 on a startup failure and shows float noise"
status: open
tier: 3
filed: 2026-10-06
specs: []
prs: [708]
commits: []
cites: [§6.2]
related: [b-a1d649, b-cf50dc, b-b51c9c]
---

## Problem

Found 2026-10-06 by the final review of the run record view, and left
after the review commits on #708.

- A gate status outside the four known ones raises `KeyError` in `build`.
  A port in use raises `OSError`, and a ledger without a newer column raises
  `IndexError`. Each exits 1 with a traceback, where the CLI's contract
  gives infrastructure failures exit 2.
- Spend renders with float noise, such as `51.952599899999996` on `/`.
- The batch page drops V2's cost and pull request, and shows no window, stop
  reason or spend for the batch itself.
- No page says when its graph was built, though failure lines are read live.
- A finding the ledger marks unanchored renders as an anchored one.
- `build` parses the shapes file six times, and two `_sh_in` helpers nearly
  duplicate each other.
- `do_POST` with a negative `Content-Length` blocks its thread until the
  client closes.

## Done looks like

Each startup failure exits 2 with one line. Money renders rounded. The batch
page shows the batch's own facts and its tasks' cost and pull request. Each
page names its build time. An unanchored finding is marked. The shapes file
is read once per build. A negative length answers 405 without a read.
