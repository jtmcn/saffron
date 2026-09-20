---
id: 131
title: No cell-marked test starts the gate-only cell the way production does
status: open
tier: 3
filed: 2026-09-15
by_hand: true
specs: []
prs: []
commits: []
cites: [§5.5]
related: [118, 127]
---

## Problem

Found by the spec review of `SA-0089`, 2026-09-15. `SA-0089` adds a third
production cell start: the gate-only cell that computes the table the REVIEW
lenses are shown, brought up with `worktree.prepare_worktree` on the task's own
internal network with the repo's declared gate env and nothing else. Its
witnesses drive `_drive_cell` against stubs — `_stub_the_runtime` stubs
`create_volume` to a no-op and starts no container — so every isolation
property the criterion names is asserted as an argument passed, never as a
property held. Appendix I is why that gap matters: v0.5 shipped a cell with
neither `network` nor `env`, every mechanism reported success, and each applied
to a different container. `CLAUDE.md` states the rule that followed: isolation
tests must start a cell the way production does and probe from inside it.

Item 127 makes this point about `SA-0087`'s critic cell. This is its sibling,
and the claim here is the stronger of the two: the critic cell carries
`CLAUDE_CODE_OAUTH_TOKEN` because its lenses need it, while the gate-only cell
is to carry no credential at all.

## Done looks like

a `cell`-marked test that brings the gate-only cell up through the same function
REVIEW calls and probes from inside it: its environment carries no
`CLAUDE_CODE_OAUTH_TOKEN` and no other credential, the proxy is the only host it
can reach, and the gate results it produces come from the image's own toolchain
rather than from anything the implementer's cell wrote.

## Record

**Filed 2026-09-15**, to land after `SA-0089` merges. By hand, because a cell
cannot run `cell`-marked tests: they need the cell runtime and its images on the
host.

**2026-09-16, the Gate-only cell ran live for the first time**, in `SA-0093`'s
second cell (spec loop run 5), and died at REVIEW: apple/container refuses an
uppercase network name, and the cell's was `saffron-gate-net-SA-0093`. Every
live REVIEW on this runtime had ended `ORPHANED` since #285. Fixed by hand in
#298, whose stub now refuses an uppercase network name the way the runtime
does. That is one measured rule copied into a stub, not this item's probe,
which is still open.
