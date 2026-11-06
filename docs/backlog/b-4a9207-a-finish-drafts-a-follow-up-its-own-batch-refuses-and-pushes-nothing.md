---
id: b-4a9207
title: "A finish drafts a follow-up its own batch refuses for citations, and its finishing layer stays red, so nothing pushes"
status: open
tier: 2
filed: 2026-11-02
specs: []
prs: []
commits: []
cites: [§5.7]
related: [b-e0044f, b-549012]
---

## Problem

Found in the spec loop's run 52.

Finish 64's end review raised one real concern on #1010, a comment that
undercounted the guards reading `pr_url`. It drafted `SA-0332` for it. The
finishing suite first failed that draft's prose. The batch then refused the
revised draft with `2 citation(s) do not resolve`. The finishing layer
`91ee614d` ended with `escalate: red suite, 1 new failure`, and the finish
pushed nothing. The log does not name the failing gate.

The fix was one line, which the delegate made by hand on #1010. The same shape
ended run 49's `SA-0324`, refused for two citations.

## Done looks like

A finding small enough for one line is fixed in the finishing layer, not
drafted. A drafted follow-up's citations are checked where the batch will
check them, before the batch is asked to run it. The escalation names the
gate that failed.

## Record

- 2026-11-02: filed from the spec loop's run 52.
- 2026-11-06: recurred in the spec loop's run 54. Finish 67's one real finding was a one-line docstring in `saffron/record/routed.py`. Its follow-up `SA-0338` failed to parse, then failed `prose`, and was pooled. The delegate fixed the line by hand on #1024. b-ffb930 holds the parse failure.
