---
id: b-19f43a
title: The reviewed-diff phase line is spelled in two modules, so a change to one silently unbinds every record
status: open
tier: 3
filed: 2026-11-12
closed:
specs: [SA-0386]
prs: []
commits: []
cites: [§5.7]
related: [b-1b05be]
---

## Problem

Found reviewing #1172 (`SA-0378`) in the spec loop's run 65.

REVIEW writes `reviewed diff recorded, sha256 <hash>` in
`saffron/cell/session.py`. `qualify._binds_task` matches the same text,
written out again in `saffron/qualify.py`. Nothing shares the two.

If either side changes its wording, no record binds. Every in-cell concern
then falls back to the packaged head's check with a `note`, and no gate or
test outside the two witnesses notices.

`SA-0378` could not share them: its `forbidden` held `saffron/cell/**`.

## Done looks like

One constant names the line's detail text. `session.py` writes it and
`qualify.py` imports it.

## Record

- 2026-11-12: filed from the Standards seat's out-of-scope note on #1172.
