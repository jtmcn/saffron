---
id: 59
title: The overlap refusal walks one hop, so a stack deeper than two refuses its own grandchild
status: done
tier: 1
closed: 2026-09-04
specs: [SA-0052]
prs: [118]
commits: [37b2dc2]
cites: [§4.2.1]
related: []
---

## Problem

`saffron/scheduler.py`'s open-pull-request overlap refusal exempts the
candidate's own branch and one parent:

```python
parent_branch = _branch(candidate.spec.depends_on[0]) if candidate.spec.depends_on else None
for pr in open_prs:
    if pr.get("headRefName") in (own_branch, parent_branch):
        continue
```

`depends_on[0]` is the **immediate** parent. A stack is transitive.
`SA-0049` → `SA-0048` → `SA-0046` → `SA-0045`: the exemption covers `SA-0048`
and not `SA-0046`, whose pull request is open and whose changed files include
`saffron/ledger.py`. `SA-0049` touches `saffron/ledger.py`, so it is refused:

```
SA-0049: touches overlaps open pull request #116's changed files:
         saffron/ledger.py, tests/test_ledger.py
```

**The refusal is a false positive, and stacking is why.** A stacked child is
cut from its parent's branch head, so a linear stack's grandparent changes are
already in the child's own base *by construction*. There is nothing to
conflict with — that is the whole point of `SA-0022`, `SA-0025` and `SA-0026`.
The gate is refusing the case the stacking machinery exists to admit, which is
the shape §4.2.1 already had to correct once for the dependency gate.

**Invisible today, and that is the dangerous part.** `saffron cell` never
consults `build_queue` — only `saffron queue` does (`cli.py:531`) — so every
spec in this session's stack was driven successfully while the scan was
refusing one of them. The refusal costs nothing until a batch reads it, and
then it costs a task per night, silently, on exactly the deep queues stacking
was built for.

**Not** widening the refusal to ignore all overlaps: the gate is right about
two unrelated tasks touching one file, which is what it was built for. Only the
ancestor case is wrong, and only because the chain is walked one link deep.

## Done looks like

the exemption walking the chain rather than one link:
collect every ancestor's branch by following `depends_on[0]` transitively
through the discovered specs, and exempt all of them. The specs are already in
hand at that point — `build_queue` has the whole scanned set — so this needs no
new lookup. A test with a three-deep stack and an open grandparent pull request
is what fails today.

## Record

**Tier 1.** Measured 2026-09-04, on this repo's own queue, by the first stack
three deep.

**Status:** **done**, by `SA-0053`'s predecessor `SA-0052` (PR #118, merge
`37b2dc2`) — one attempt, $5.03, no blocking findings. The exemption now walks
`depends_on[0]` transitively through the discovered specs, carrying a visited
set seeded with the candidate's own id so a dependency cycle ends the walk
instead of hanging the scan. `build_queue`'s signature is unchanged and the two
live-witness tests were not touched: 239 added lines, 0 removed. Verified after
the merge — the queue that had refused `SA-0049` reports zero refusals.
