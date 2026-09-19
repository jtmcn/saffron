---
id: b-7c41e0
title: A finding demoted by a killed probe renders in the pull request body as a plain note
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

Once `SA-0109` lands, a finding whose probe was `killed` is demoted to a
`note`, whatever its lens filed. The pull request body does not know why.
`_findings` (`saffron/report/pr_body.py:338-350`) renders it as a `note` like
any other. A reader cannot tell it from a note the lens filed.

`SA-0109` forbids `saffron/report/**`, so its cell cannot fix this.

## Done looks like

The body's findings table marks each finding's `probe_verdict`, and a demoted
finding shows the severity its lens filed beside the one it now has.
