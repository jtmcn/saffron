---
id: b-d3f977
title: "A stale gh-stack rebase state from an old run blocks gh stack link, and driver.py stack reports only exit 7"
status: open
tier: 3
filed: 2026-10-25
specs: []
prs: []
commits: []
cites: []
related: []
---

## Problem

Found in the spec loop's run 48.

`driver.py stack --execute` failed with "Run `gh stack rebase --continue`
or `gh stack rebase --abort`". The cause was `.git/gh-stack-rebase-state`,
left by run 19 on 2026-09-27. An abort would have reset 13 old branches to
September shas. The delegate moved the file aside, and the link then
succeeded.

## Done looks like

`driver.py stack` names a leftover rebase state and its age before it
calls `gh stack link`.

## Record

- 2026-10-25: filed from the spec loop's run 48.
