---
id: b-01c53d
title: "The end review's writer drafts a whole spec for a two-line comment fix, and withheld it after three revisions"
status: open
tier: 3
filed: 2026-10-25
specs: []
prs: []
commits: []
cites: [§5.7]
related: [b-781ea4]
---

## Problem

Found in the spec loop's run 48.

`saffron finish 55` found one comment in `saffron/task.py` that said a
marked raise skips the breaker. The writer drafted `SA-0317` for it, with
four wrong versions and a new witness. It escalated after three revisions
and ended `SPEC_WITHHELD`. The finish spent about $14.66, twice what
finishes 53 and 54 spent. The delegate fixed the comment by hand in the
loop's closing PR.

## Done looks like

A finding that changes only a comment goes to the finishing layer as an
edit, not to the writer as a follow-up spec.

## Record

- 2026-10-25: filed from the spec loop's run 48.
- 2026-10-27: in `saffron finish 58` the writer declined to draft a spec for a one-line docstring finding, and the finish pooled it as type `test`. The review commit on #979 had already fixed the line.
