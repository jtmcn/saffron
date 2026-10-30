---
id: b-25b7ba
title: Two renderers spell a new failure as text, and they disagree on a failure at line 0
status: open
tier: 3
filed: 2026-10-30
specs: []
prs: []
commits: []
cites: [§5.4]
related: [b-e0044f]
---

## Problem

Raised on #996 by its Standards seat, outside `SA-0327`'s `touches`. Finish
61's end review raised it again, and its follow-up was pooled (b-27bacc).

`saffron/finish.py`'s `_render_new_failure` turns a `NewFailure` into
`[gate] file:line code: message`. `saffron/phases/implement.py`'s
`repair_prompt` spells the same text by hand. The two differ on one input. A
failure at line 0 renders `?` in `repair_prompt`, which tests `line or '?'`.
`_render_new_failure` tests `is not None`, so it renders `0`.

`SA-0327` forbade `saffron/phases/**`, so its cell could not share one.

## Done looks like

One function renders a new failure, and both callers import it. A witness
drives a failure at line 0 through each caller.

## Record

- 2026-10-30: filed from the spec loop's run 50.
