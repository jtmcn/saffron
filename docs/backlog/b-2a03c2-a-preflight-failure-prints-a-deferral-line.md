---
id: b-2a03c2
title: "A stack batch whose preflight fails still prints that its end review is deferred and its reserve held"
status: open
tier: 3
filed: 2026-10-27
specs: []
prs: []
commits: []
cites: []
related: []
---

## Problem

Found in the spec loop's run 49.

Batch 57 failed preflight on a host listener. It ran no task, yet it printed
"end review: deferred, reserve held, run saffron finish 57". Nothing was held
and there was nothing to finish.

## Done looks like

A batch that ran no layer prints no deferral line and writes no
`deferred.json`.

## Record

- 2026-10-27: filed from the spec loop's run 49.
