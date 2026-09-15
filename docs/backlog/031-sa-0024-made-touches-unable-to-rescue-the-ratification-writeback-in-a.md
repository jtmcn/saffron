---
id: 31
title: '`SA-0024` made `touches` unable to rescue the ratification writeback, in a repo whose spec directory is `protected`'
status: open
tier: 3
specs: [SA-0024]
prs: []
commits: []
cites: [§5.2]
related: []
---

## Problem

§5.2 requires the task's own spec path to be added to the ratified `touches`
when a scope proposal is recorded, *"or that first commit fails the `scope`
gate on every ratified task"* — the writeback commits to `.saffron/specs/…`,
which DIAGNOSE would never propose. `saffron/cell/session.py` implements it,
and its comment names the measurement.

`SA-0024` made the deny lists independent of `touches`, which is the whole
point of the change: widening `touches` must not clear a denied path. But
this repo's `.saffron/policy.yaml` lists `.saffron/**` under `protected`, so
the host-authored writeback commit is now exactly such a path. A ratified task
would report `[scope] .saffron/specs/SA-XXXX-….md protected` — a blocking
failure the agent cannot repair, because reverting it destroys the
ratification the operator just granted.

**Latent, not live.** Nothing in `saffron/` performs the writeback yet:
`SCOPE_REVIEW` writes `scope_proposal.json` and stops for a human, and
`base_sha` is the remote default-branch head, so a writeback merged by hand is
already behind the base a cell diffs against. The mechanism is designed,
documented and half-built, which is why this is an item rather than a note.

**Done looks like** the recorded spec path exempted from the deny lists in the
same place it joins `touches` — one exemption, host-added, never the model's —
with a test that a ratified task's first commit passes `scope` in a repo whose
spec directory is `protected`. Found by the review of `SA-0024`, not by a run.
