---
id: b-4a9207
title: "A finish drafts a follow-up its own batch refuses for citations, and its finishing layer stays red, so nothing pushes"
status: partial
tier: 2
filed: 2026-11-02
specs: [SA-0377, SA-0381]
prs: [1171]
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
- 2026-11-09: recurred in the spec loop's run 56. Finish 73 ran `main`'s engine, which lacks this stack's #1099 fix for the writer's own validation. Its follow-up drafts failed to parse three times. `SA-0357` and `SA-0358` were refused for overlapping #1099. The finishing layer went red with one unnamed failure and pushed nothing.
- 2026-11-10: the spec loop's runs 57 and 58 ran finish 74, 75 and 76 after
  their stacks merged. The skill runs a finish before the merge. Each finish
  pooled concerns the review commits had fixed, and could not read its
  deleted heads. This is the delegate's error, not a recurrence of this item.
- 2026-11-10: recurred in the spec loop's run 60. Finish 78's two concerns
  were one-line docstrings. `SA-0366`'s draft failed `prose` on a
  contraction. `SA-0367`'s witness passed at its base, since review commit
  `80f41af0` had fixed its line. The finish pushed #1138 with both drafts and
  ended `INFRASTRUCTURE`. The delegate fixed `SA-0366`'s line in run 60's
  step 5 pull request and closed #1138.
- 2026-11-11: recurred in the spec loop's run 62. Finish 80 graded the
  in-cell critic's two concerns at PACKAGE's head. REBUT had fixed one before
  PACKAGE, and review commit `12e8c6a6` the other. One was pooled. The other
  became `SA-0370`, refused for 11 citations. The finishing layer edited
  `SA-0369`'s spec, went red on `prose` and `census`, and pushed nothing.
- 2026-11-11: a correction to the line above, from the spec loop's run 63.
  REBUT changed the code behind both concerns before PACKAGE. Review commit
  `12e8c6a6` fixed neither. b-1b05be's Record line has the two cited lines.
- 2026-11-11: recurred in finish 81. It drafted `SA-0375` from `SA-0371`'s
  contract concern, which the spec had named out of scope. The draft failed
  `prose` and the records check, so the finding was pooled.
- 2026-11-11: finish 82 drafted `SA-0379` from `SA-0372`'s symlink concern.
  The follow-up ran, reached `READY_FOR_REVIEW` and opened #1167.
- 2026-11-12: #1171 shipped `SA-0377` in the spec loop's run 65. A follow-up's
  citations are checked before the batch runs it, and the escalation names its gates.
  Fixing a one-line finding in the finishing layer stays open.
- 2026-11-12: finish 83 pooled all three follow-up groups with "declares a
  depends_on entry". The origin spec `SA-0378` declares `depends_on`, and each draft
  copied it, twice per group.
- 2026-11-12: correction to the line above, found writing `SA-0381`. The drafts
  did not copy their origin's `depends_on`. All six declared `[SA-0378]`, the top
  layer each writer sat on, and one origin (`SA-0375`) declares none. 55 findings
  in 16 of 67 finishes were pooled this way.
