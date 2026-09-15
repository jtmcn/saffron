---
id: 45
title: An `EXHAUSTED` run that made commits pushes no branch, so its work survives only as a patch
status: done
tier: 1
closed: 2026-09-12
specs: [SA-0028, SA-0031, SA-0069]
prs: [214]
commits: []
cites: [§5.7]
related: []
---

## Problem

`SA-0028` closed the door where an implement turn dies on its ceiling with
*nothing* committed. This is the door beside it: commits exist, gates are red,
the budget or the attempts are gone, and PACKAGE never runs — so nothing is
pushed and there is no pull request.

Measured on `SA-0031`: six commits, 39 new gate failures, `$19.17` spent, and a
ledger row reading `branch saffron/SA-0031, pushed_sha NULL, pr_url NULL`. The
only survivor is `teardown`'s `patch.diff`. It is real work — it applies
cleanly to `saffron/SA-0030` and leaves 15 failures, so it was roughly 85%
finished — and nothing in the system will ever look at it again.

The cost is not the disk space. It is that the operator's only route back to
$19.17 of work is to know the batch tree exists, find the patch, and apply it by
hand — none of which any output tells them.

Done looks like pushing the branch on any terminal state that made commits,
recording `pushed_sha`, and saying so on the way out. A pull request is a
separate question — red gates should not open one — but a branch nobody can
reach is not a decision, it is a leak. The split design
(`docs/superpowers/specs/2026-09-01-splitting-a-too-wide-spec-design.md`) needs
this independently: its mid-flight split hands child 1 the parent's branch, and
there is no branch to hand.

## Record

**Two things for by hand, found reviewing `SA-0069`, 2026-09-11:**
- **§5.7 says `pushed_sha` "is written once, by PACKAGE".** `SA-0069` makes that
  false, and `DESIGN.md` is `protected`. Amend it when that spec lands.
- **§5.7 step 2 promises more than the green path delivers.** It says a push
  fails if the branch was moved underneath it, for example "you pushing a fixup
  by hand". But PACKAGE's lease is `remote_sha(url, branch)`, read at push time,
  so it guards against a race, not against a branch someone else owns. A
  re-packaged spec replaces a branch that holds an operator's review fixes.
  `SA-0069` guards its own push against this by checking the remote head
  against the spec's recorded pushes. The green path wants the same check.

**Status:** **done** — `SA-0069`, PR #214, merged 2026-09-12. Its review added
the `scope` check before the push and a refusal while another task of the spec
awaits review. The by-hand notes below are not covered by it.
