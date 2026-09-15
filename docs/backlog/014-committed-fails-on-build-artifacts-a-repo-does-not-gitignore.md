---
id: 14
title: '`committed` fails on build artifacts a repo does not gitignore'
status: open
tier: 3
specs: []
prs: []
commits: []
cites: [§2.1, §5.4]
related: [55]
---

## Problem

`dirty_paths` is read after the declared suite on both calls so that an artifact
a gate writes lands on baseline and head alike and `subtract_baseline` cancels it
(§5.4). The cancellation is by identity — `(gate, file, code, message)` — so it
only reaches artifacts whose **paths** match on both sides.

A head-only path has nothing to cancel against. The task adds `src/newmod.py`; the
head `tests` gate compiles it and leaves `src/__pycache__/newmod.cpython-312.pyc`,
which the baseline never had. `committed` fails, the repair turn says *changed but
not committed — fix these and commit*, the agent commits the artifact, and `scope`
then fails it as a path outside `touches`. The attempts burn out and the run ends
`EXHAUSTED` on a diff that was green. `.coverage.<host>.<pid>.<rand>` and
`.mypy_cache/<module>.meta.json` are the same shape.

Saffron's own `.gitignore` covers all three, which is why nothing here caught it;
an onboarded repo whose ignores are looser is not covered.

## Done looks like

the repo declaring its build output, since which paths are
artifacts is language knowledge §2.1 keeps out of core — `.gitignore` is already
that declaration and `git status --porcelain` already honours it, so onboarding
documentation stating the requirement may be the whole fix. If it is not, the
narrower mechanism is `committed` ignoring untracked paths that the baseline call
also produced *by directory* rather than by path — which is a second identity rule
sitting next to the subtraction's, and CLAUDE.md warns against making those match.

## Record

**That sentence is false, measured 2026-08-25 (#30). It covers one of three.**
`git check-ignore` against the shapes this item names: `__pycache__/*.pyc` is
ignored; `.coverage`, `.coverage.<host>.<pid>.<rand>` and
`.mypy_cache/<module>.meta.json` are **not**. The whole file is nine lines and
has no coverage entry and no mypy entry. Found by accident — a `coverage` run
during #33 left a `.coverage` that `git status` reported as untracked, which is
the opening move of the sequence above.

So the reason this has never fired here is not that the declaration is complete.
It is that no declared gate has yet written one of the two unignored artifacts —
**untested, and worth testing before this item is closed**, since if none of
`format`/`lint`/`types`/`tests` writes either file then this item is right by
accident and should say so for the right reason.

The consequence for the decision: this item argues the repo-declaration route is
free for Saffron and costly only at repo two. It is not free here, and under an
unattended night the failure is silent, arrives at the worst hour, and presents
as a task that could not pass its gates rather than as a misconfigured repo.
`session.py:674` carries a `ponytail:` comment resting on the same assumption.

Adding two lines to `.gitignore` closes this repo's instance and leaves the
question — whose declaration is this? — exactly where it was. Worth doing; not a
resolution.

**Decided 2026-09-04, and the item's own open measurement is now taken.**
`.gitignore` is the declaration. It already exists, `git status --porcelain`
already honours it, and stating that as an onboarding requirement is the whole
fix. **Tier 3.**

This item asked to be tested before it was closed: *"if none of
`format`/`lint`/`types`/`tests` writes either file then this item is right by
accident and should say so for the right reason."* Measured — all five declared
gates run against a clean tree, `git status --porcelain` diffed before and
after: **zero untracked artifacts.** `.mypy_cache` is moot, because the
typechecker is `ty` and it wrote no cache. `.coverage` came from a hand-run
during #33, not from a declared gate. So this repo is right by accident,
confirmed, and it stays right until a gate that writes an artifact is declared.

**The narrower fallback is explicitly not being built**: `committed` ignoring
untracked paths the baseline call also produced *by directory* would be a
second identity rule sitting beside the baseline subtraction's, and `CLAUDE.md`
warns in as many words against making those match. Item 55 (`dist/`) is the
same family and is one line of `.gitignore`.
