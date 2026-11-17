---
id: b-f06097
title: A wrong version's edit changes more than the version names, so another assert kills it and the version goes unasked
status: open
tier: 3
filed: 2026-11-11
closed:
specs: []
prs: []
commits: []
cites: [§5.5]
related: [b-12e717, b-7c88f8]
---

## Problem

Found reviewing #1158 (`SA-0371`) in the spec loop's run 63.

The spec declared the wrong version "The fresh cell is handed a fresh
`created` set." REVIEW expressed it as `created=set()` on the one
`critic_cell` call. That call runs for both cells, so the edit also changed
the first cell. The witness asserted identity on the first entry only, and
that assert killed the edit. REVIEW filed the version `killed`.

The Spec seat expressed the version itself: `created=created if _attempt == 0
else set()`. The witness passed under it. A review commit added the second
entry's identity assert.

So a `killed` outcome says a witness died, not that it died for the reason
the version names.

## Done looks like

A wrong version's edit changes only the case the version names. Or its
expression turn names the cases the edit leaves alone, and REVIEW checks that
the witness dies on the named case.

## Record

- 2026-11-11: filed from the spec loop's run 63, #1158.
- 2026-11-15: seen again in the spec loop's run 74, #1228 (`SA-0400`). REVIEW
  filed wrong version 14 `killed`. Its edit also sent refused pairs to the
  mutator, and the witness's sequence assert caught that. The Spec seat's own
  edit, a refusal made inside the cell, passed the declared witness.
- 2026-11-17: backtested in the spec loop's run 76 on `SA-0371` version 7
  and `SA-0400` version 14. Each REVIEW edit changed a call that more cases
  share than the version names. No arm the host can decide separates either
  edit from the seat's narrower one. Two arms are left. One is a prompt change,
  which needs a measured pass by hand. The other is a second model turn per
  version. Which arm to take is the operator's call.
