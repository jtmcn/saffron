---
id: b-18fa39
title: "A failed test reaches a writer and the log as its node id alone, so a follow-up draft is redrafted blind and pooled"
status: done
closed: 2026-11-23
tier: 2
filed: 2026-11-22
specs: [SA-0426]
prs: [1308]
commits: []
cites: [§5.4]
related: [b-4a9207, b-703e64]
---

## Problem

Found in the spec loop's run 83, finish 103.

The finish judged a follow-up draft, then also numbered `SA-0426`, and the finishing suite failed
`test_the_backlog_records_hold`. The writer got the failure back and
redrafted twice, and the finish then pooled all four findings. Neither the
writer nor the log saw why the test failed.

The `tests` gate calls pytest with `-q` under captured output. pytest fits
each `FAILED` line to an 80-column terminal. A node id that long leaves no
room for the ` - ` message, so pytest drops it. With `COLUMNS=400` the
same line ends `SA-0426 cites this item and is not listed` (measured).

The gate's `message` is also part of a failure's identity
(`saffron/gates/contract.py`'s `identity`). Assertion text there would stop a
baseline failure from cancelling its match at head whenever the text holds a
path or a value that varies. So the text needs a field of its own, outside
the identity.

## Done looks like

A gate failure carries an optional detail that `identity` never reads. The
`tests` gate fills it with pytest's own one-line reason. `render` prints it,
so the follow-up writer, a repair turn and the finish's log each read why a
test failed.

## Record

- 2026-11-22: filed from finish 103 in the spec loop's run 83. The draft
  cited b-d9ed45 in its `## Context`, and the item did not list it back.
- 2026-11-23: done by `SA-0426` (#1308), batch 105. A failure carries its reason in `detail`, outside its identity.
