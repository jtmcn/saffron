---
id: 137
title: Editing a spec whose pull request is open refuses every dependent, and the order forgets it
status: open
tier: 1
filed: 2026-09-16
by_hand: true
specs: []
prs: [280, 281]
commits: []
cites: [§4.2]
related: [118, 138]
---

## Problem

**Tier 1.** Found running the spec loop on 2026-09-16 (stack #285); cost two
pull requests and a round trip, no money.

After reading `SA-0088`'s review the operator retyped its spec `bug` → `feature`,
which is a legitimate thing to want mid-loop: the review is what produced the
evidence. But a spec's `spec_sha` is what the loop's order and the dependency
check key on, so editing `SA-0088` while #277 was open made the ledger's task
stop matching the spec on main. The next `snapshot --force` said:

```
held out of the order (1):
  SA-0088: the spec changed after the snapshot, and #277 is still open
refused, and not in the order (2):
  SA-0089: depends_on SA-0088 has no task at its current spec_sha, so nothing
           says it merged: it has not run, or not since it was last edited
  SA-0091: depends_on SA-0089 ...
```

Nothing warned at edit time. Both messages appear only on the *next* re-snapshot,
after the edit has merged — so the operator learns the chain is dead one PR too
late. Recovery was a second PR (#281) reverting the two lines, which restored the
exact sha the task ran at.

There is a second half. Once SA-0088 was held out, `--force` could not put it
back: its pull request is open, so `saffron queue`'s conflict set refuses it, and
its recorded outcome had already been dropped. `driver.py stack` then printed a
stack with #277 missing, which would have retargeted #282 off its parent onto
`main`. The loop's own step 3 was wrong, silently, because of an edit two steps
earlier.

`SKILL.md` step 1b does say "a spec edited here changes its `spec_sha`, so run
`snapshot --force` after the edit merges" — true for a spec that has not run. The
gap is the already-run case, which is the one an operator reaches after reading a
review.

## Done looks like

`snapshot` and `status` warning, before the force, when a spec with an open
pull request differs from the sha its task ran at — naming the dependents that
would be refused. Either that, or the dependency check accepting a parent whose
only difference from its task's sha is outside the frontmatter a cell reads. And
a `--force` that keeps a recorded outcome for a spec it holds out, so the stack
does not silently lose a layer.

## Record

**Filed 2026-09-16** from the spec loop's run of that day (stack #285).

**2026-09-16, a fix is open as PR #287.** `status` now names the dependents an edit refuses and the pull request it drops. It stays `open` until that merges.
