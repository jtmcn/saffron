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
