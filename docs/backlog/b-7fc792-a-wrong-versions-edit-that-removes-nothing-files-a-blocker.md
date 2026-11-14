---
id: b-7fc792
title: A wrong version's edit that removes nothing survives, and REVIEW files it as an adequacy blocker
status: open
tier: 3
filed: 2026-11-14
closed:
specs: []
prs: []
commits: []
cites: [§5.4.1, §5.5]
related: [b-f06097, b-12e717]
---

## Problem

Found reviewing #1203 (`SA-0390`) in the spec loop's run 70.

The spec declared the wrong version "`risk` is left out, so it reads
`standard`." REVIEW's expression gave a reason that names deleting
`risk=outcome.effective_risk,` from `queue_line`. Its edit did something
else. The `replace` kept the whole `find` and appended an unused function
`_risk_placeholder_removed_marker`. The edit changed no behaviour, so the
witness passed. REVIEW filed the version `survived` as an adequacy blocker.

REBUT argued it, and the host kept it as recorded disagreement, since the
criterion is `preserves`. The Spec seat ran the real deletion. Three
witnesses killed it, criterion 8's own among them.

`source_mutated` refuses six edits that apply nothing
(`saffron/cell/worktree.py`, `source_mutated`). An edit that applies and
changes nothing is not among them.

## Done looks like

An edit whose `replace` holds its `find` unchanged, and adds only names no
other line reads, is refused as unproven rather than run. Its reason says
the edit removed nothing. A version that names a removal and removes nothing
never reaches a witness as a `survived` outcome.

## Record

- 2026-11-14: filed from the spec loop's run 70, #1203.
