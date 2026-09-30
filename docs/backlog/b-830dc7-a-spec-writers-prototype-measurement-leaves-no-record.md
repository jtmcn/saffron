---
id: b-830dc7
title: A spec writer's prototype measurement leaves no record a reviewer can read
status: open
tier: 3
filed: 2026-09-29
specs: []
prs: []
commits: []
cites: []
related: [b-865399]
---

## Problem

Found in the spec loop's run 22, 2026-09-29, at step 1b.

Step 1b raised "arrangement unmeasured" on 9 of 15 specs. Each spec's notes
say a prototype killed every wrong version. No output of that prototype
reached the spec PR, so the reviewer could not read it.

## Done looks like

The spec PR carries the `driver.py probe` output per wrong version. Check 3
reads it.

## Record

- 2026-09-29: filed from the spec loop's run 22.
