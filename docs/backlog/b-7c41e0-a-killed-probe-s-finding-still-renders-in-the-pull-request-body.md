---
id: b-7c41e0
title: A finding whose probe was killed still renders in the pull request body at the severity its lens filed
status: open
tier: 2
filed: 2026-09-18
specs: []
prs: []
commits: []
cites: [§5.5, §5.7]
related: [117]
---

## Problem

Found 2026-09-18, in the spec review of `SA-0109`.

Once `SA-0109` lands, a finding whose probe was `killed` is dropped from the
blocker and concern counts. The pull request body does not know that.
`_findings` (`saffron/report/pr_body.py:338-350`) renders it at its filed
severity, so a killed blocker reads as `blocker`. `_disagreements` (`:290`)
omits it, and `:563-566` can then say every finding reached the implementer.

`SA-0109` forbids `saffron/report/**`, so its cell cannot fix this.

## Done looks like

The body's findings table marks each finding's `probe_verdict`. A killed
finding is shown as dropped, and no sentence counts it as a blocker the
implementer answered.
