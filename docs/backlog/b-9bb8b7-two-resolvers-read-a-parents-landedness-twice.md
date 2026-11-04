---
id: b-9bb8b7
title: Two resolvers read a parent's landedness by two copies of one rule
status: open
tier: 3
filed: 2026-11-04
specs: []
prs: []
commits: []
cites: []
related: [b-f603c9]
---

## Problem

Found by both review seats on #1016, in the spec loop's run 53.

`_parent_landed` in `saffron/task.py` repeats `_resolve_multi_parent`'s three
landed readings: a `MERGED` row, a retirement at `base_sha`, and a push in
`base_sha`. Each exports `.saffron` at `base_sha` again. `SA-0330` told the
cell not to align the two paths, so the copy stands.

## Done looks like

One helper reads landedness for both resolvers. The spec that moves it
replaces `SA-0330`'s criterion 3 mutant, whose `find` is the inline
`if dep in retired_ids:`.

## Record

- 2026-11-04: filed from the spec loop's run 53.
