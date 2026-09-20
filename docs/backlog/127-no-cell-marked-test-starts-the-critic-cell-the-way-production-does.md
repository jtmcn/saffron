---
id: 127
title: No cell-marked test starts the critic cell the way production does
status: open
tier: 3
filed: 2026-09-15
by_hand: true
specs: []
prs: []
commits: []
cites: [§5.5]
related: [118, 131]
---

## Problem

Found by the spec review of `SA-0087`, 2026-09-15. `SA-0087` adds a second
production cell start: the critic cell, brought up with
`worktree.prepare_worktree` and `cell_env` on the task's network and proxy.
Its witnesses drive `_drive_cell` against stubs, so none of them starts a real
container. Appendix I is why that matters: v0.5 shipped a cell with neither
`network` nor `env`, every mechanism reported success, and each applied to a
different container. `CLAUDE.md` states the rule that followed: isolation
tests must start a cell the way production does and probe from inside it.

## Done looks like

a `cell`-marked test that brings the critic cell up through the same function
REVIEW calls and probes from inside it: the proxy is the only host it can
reach, its environment carries `CLAUDE_CODE_OAUTH_TOKEN` and no other
credential, and its rootfs is the image's, so a file written into the
implementer's cell is absent from it.

## Record

**Filed 2026-09-15**, to land after `SA-0087` merges. By hand, because a cell
cannot run `cell`-marked tests: they need the cell runtime and its images on
the host.
