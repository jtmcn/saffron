---
id: b-dcf1ec
title: "A preflight hit read with no socket list is labelled \"no known process\", though lsof ran"
status: open
tier: 3
filed: 2026-10-10
specs: []
prs: [796]
commits: []
cites: [§5.1]
related: []
---

## Problem

Found by the Spec seat on #796 in the spec loop's run 33.

`sockets` defaults to an empty tuple (`saffron/preflight.py:234`). A caller
that passes `ports=None` would get every hit labelled with no known
process, although lsof ran and named one. No caller in the tree does this
today.

## Done looks like

- A hit with no socket list says that no list was read, or the parameter
  has no default.

## Record

- 2026-10-10: filed from the spec loop's run 33.
