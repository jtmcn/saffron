---
id: b-8d654b
title: The finishing commit writes through a symlink a cell committed under .saffron/specs/
status: done
tier: 2
filed: 2026-10-01
closed: 2026-10-09
specs: [SA-0151, SA-0239]
prs: [628, 786]
commits: []
cites: [§2]
related: [b-3d2aa1]
---

## Problem

Found by #628's Spec seat, 2026-10-01. Unverified end to end.

`commit_finish` writes and renames inside a checkout of the top layer's tree,
which a cell authored. `Path.write_text` and `rename` follow a symlink
committed at `.saffron/specs/<name>.md`, or at `.saffron/specs` itself. On a
target repo whose policy does not protect `.saffron/**`, that is a host write
outside the worktree.

## Done looks like

`commit_finish` refuses any symlink component of a path it writes or
renames, checked with `lstat` before the write, and a test drives one.

## Record

- 2026-10-01: filed from #628's review seats. `SA-0167`'s gate suite is one home for the fix.
- 2026-10-09: done by `SA-0239` (#786) in the spec loop's run 32. The finish
  refuses to write through a symlinked path component. A file where a
  directory belongs still raises uncaught, which b-8c17dc tracks.
