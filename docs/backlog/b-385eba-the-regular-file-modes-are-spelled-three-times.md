---
id: b-385eba
title: The regular-file git modes are spelled in three modules, and the view imports one module's private name
status: open
tier: 3
filed: 2026-10-08
specs: [SA-0225]
prs: [746]
commits: []
cites: [§6.2]
related: []
---

## Problem

Found by the in-cell conventions lens and the Standards seat on #746, in the
spec loop's run 31.

`saffron/repos/mirror.py` defines `_REGULAR_MODES`. `saffron/cell/worktree.py`
spells `("100644", "100755")` again inline. SA-0225 first restated the set in
`saffron/view/server.py`. Its spec forbade `saffron/repos/**`, so the review
commit imports the private `_REGULAR_MODES` instead.

## Done looks like

One public constant, imported by all three modules.

## Record

- 2026-10-08: filed from the spec loop's run 31.
