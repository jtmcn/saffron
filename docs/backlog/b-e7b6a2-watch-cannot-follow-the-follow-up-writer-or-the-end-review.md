---
id: b-e7b6a2
title: "`saffron watch` cannot follow a stack batch's follow-up writer or its end review, because both print only"
status: open
tier: 2
filed: 2026-10-11
specs: []
prs: []
commits: []
cites: [§4.7]
related: [b-4e1b6d, b-2d09de]
---

## Problem

Left out of scope by `SA-0253` (#821), and named by its Spec seat in the
spec loop's run 34.

`SA-0253` gave a stack batch's spec review and spec writer an
`events.jsonl` each, so `saffron watch` follows them. The follow-up writer
(`_stack_follow_ups` in `saffron/cli.py`) and the end review's lenses
(`_stack_end_review`) still print to the batch's stdout alone. The end of a
stack night is therefore invisible to `watch`, as its spec sessions were
before #821.

## Done looks like

`saffron watch` with no spec id shows the end review's lenses and the
follow-up writer as they run, and each line names its session. A test
drives one of each and reads its events back through the follower.

## Record

- 2026-10-11: filed from the spec loop's run 34 (#821).
