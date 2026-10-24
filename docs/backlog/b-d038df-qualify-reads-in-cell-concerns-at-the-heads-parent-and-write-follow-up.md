---
id: b-d038df
title: "`qualify` reads in-cell concerns at the head's parent, and `write_follow_ups` reads a packaged head only when it needs one, and no witness holds either"
status: open
tier: 3
filed: 2026-10-23
specs: []
prs: [939]
commits: []
cites: [§4.2.1]
related: [b-8a0c9a]
---

## Problem

Found by the Spec seat on #939 (`SA-0303`), in the spec loop's run 46.

`saffron/qualify.py:301` reads a layer's in-cell concerns over its packaged
head's parent to its packaged head. Replacing `diff_base` with the recorded
`base` survived the witness. The fixture's recorded base for `TE-2` equals
its head's parent, so the two cannot differ.

`saffron/follow_up.py:333` reads the packaged head through `layer_fields`
only for a group that holds an in-cell concern. Replacing the condition with
`if True` survived `tests/test_follow_up.py` and the follow-up tests in
`tests/test_cli.py`.

## Done looks like

A qualify witness records a layer whose base is not its head's parent. A
follow-up witness counts `layer_fields` calls for a group with no in-cell
concern.

## Record

- 2026-10-23: filed from the spec loop's run 46.
