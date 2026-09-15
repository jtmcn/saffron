---
id: 32
title: The dependency gate asked whether a parent shipped and answered from a record of cell runs
status: done
tier: null
closed: 2026-08-31
specs: [SA-0020, SA-0022]
prs: []
commits: []
cites: [§4.2]
related: []
---

## Problem

**Status:** **done**, 2026-08-31, by hand on the host — `_retired_ids` at
`saffron/scheduler.py:464`, read at `:757`. The account is in this item's own
body below; this line exists so a scan of the file's status markers sees it.

**Done, 2026-08-31**, by hand on the host — `_retired_ids` in
`saffron/scheduler.py`, admitting a `depends_on` whose parent sits in
`.saffron/specs/done/`.

`SA-0020` narrowed the dependency refusal to admit a parent recorded `MERGED`,
which is right for a parent a cell ran. **Only a cell writes a task.** So a
spec a human implemented looks exactly like a spec nobody has run, and its
dependents stayed refused however plainly the parent's code sat in `main`. The
gate asked "is the parent's work in the default branch" and answered from a
record of cell runs; in a repo where humans and cells both commit, those are
two questions.

Measured the same day it shipped: `SA-0020` was implemented by hand, so
`SA-0022` was refused with *"no task in the ledger says it merged"* — true,
and not what the operator needed to know. The queue was empty and its one
refusal was wrong about the only work left.

Retirement to `specs/done/` already meant exactly the missing fact — that
directory's README opens *"Specs whose work is in `main`"* — and stating it
there costs nothing and writes no false row into the audit trail, which is the
one thing the ledger may not contain. Ids are read from frontmatter rather
than filenames, and a retired spec that no longer parses is not credited: the
refusal stands, the only direction that cannot admit a child whose parent is
absent.

**What this does not do:** stacking (§4.2, `SA-0022`). A retired parent is
admitted for the same reason a merged one is — the child is cut from the
default branch and the parent's commits are already in it. A parent that is
merely `READY_FOR_REVIEW` is still refused, which is §4.2's own rule minus the
half v0.5 cannot honour.
