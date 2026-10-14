---
id: b-a12047
title: PACKAGE leaves Not covered empty when the spec defers a check, so a prompt change reads as measured
status: open
tier: 2
filed: 2026-10-13
specs: [SA-0286]
prs: [867]
commits: []
cites: [§5.7]
related: [79]
---

## Problem

Found by the Standards seat on #867 in the spec loop's run 37.

`SA-0286` changed three lens prompts. Its Out of scope defers the corpus pass
that scores them to the operator, and item 79 closes on that pass. The pull
request template asks a prompt change for its measured pass, or says the
effect is unmeasured. PACKAGE renders only the spec's Problem into the body,
and its `## Not covered` held only the implementer's notes. Nothing in the
body said the change was unmeasured. The delegate added the line by hand.

## Done looks like

PACKAGE renders a spec's deferred checks under `## Not covered`. A diff that
reaches `saffron/agents/prompts/` with no measured pass gets a line that says
the prompt change is unmeasured.

## Record

- 2026-10-13: filed from the spec loop's run 37. #867's body was edited by
  hand.
