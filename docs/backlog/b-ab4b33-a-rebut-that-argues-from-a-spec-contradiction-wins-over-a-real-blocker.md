---
id: b-ab4b33
title: A REBUT that quotes one spec line against another wins, so a real blocker is withdrawn
status: done
tier: 1
filed: 2026-09-28
closed: 2026-09-29
specs: [SA-0188]
prs: [577]
commits: []
cites: [§5.6]
related: [120, b-7e69d0]
---

## Problem

Found in the spec loop's run 20, 2026-09-28, on #562 (`SA-0186`).

The correctness lens raised a blocker at `saffron/task.py:236`. The resolver
unstacked a child on any newest task outside the stackable states. The spec said
only a `MERGED` or `REJECTED` newest task does that. REBUT quoted another spec
line against it, and the lens withdrew (`rebuttal.json`: "every blocker
withdrawn by its own lens").

Both seats found the same defect. The operator decided the spec's reading, and
review commit `5479ddb6` fixed it. The blocker was right. The spec's own text was
ambiguous, and nothing escalates that.

## Done looks like

A rebuttal whose argument rests on spec text another spec line contradicts
sends the task to `SCOPE_REVIEW`. A test drives a withdrawn blocker whose
rebuttal quotes contradicting lines and reads that state.

## Record

- 2026-09-28: filed from the spec loop's run 20.
- 2026-09-29: done by `SA-0188` (#577) in the spec loop's run 21. The verdict
  schema now carries `contradicted`. The live REBUT on `SA-0188` accepted the
  schema with its optional fields. Its verdict was `withdrawn`, so no live
  `contradicted` answer ran in run 21. `SA-0192`'s REBUT ran from `main` without
  `SA-0188` and withdrew a real `preserves` blocker on an "outside my diff"
  argument. Item b-cd5fd2 holds that.
