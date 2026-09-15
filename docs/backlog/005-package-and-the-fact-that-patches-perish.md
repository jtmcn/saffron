---
id: 5
title: PACKAGE, and the fact that patches perish
status: done
tier: null
closed: 2026-08-22
specs: [SA-0003]
prs: [5]
commits: [cc986bf]
cites: [§2, §4.1, §4.4, §5.7, §6]
related: [11, 16]
---

## Problem

**Status:** **done** — PACKAGE shipped as sub-project A (`cc986bf` onward,
`saffron/phases/package.py`), and `DESIGN.md` §5.7 is its specification. Patches
no longer perish: a green run rebases onto the remote default branch, re-runs the
full suite when the base moved, pushes a branch and opens a draft pull request.
Item 11 is this build's own follow-up list and item 16 is what its policy fix
left.

There is no PR, no push, no index. A green run leaves `patch.diff` and
`patch.json` in the batch tree and nothing tells you they are there — finding one
requires knowing the layout by heart.

Worse, they decay: `SA-0003`'s patch no longer applies, because three hours of
commits moved `session.py` underneath it. A verified-green change has a shelf
life measured against the branch it was cut from.

**Done looks like:** §5.7's PACKAGE — rebase onto current `main`, re-run the full
suite on the merged result, push with `--force-with-lease` pinned to the checked
SHA, open the PR with the body §5.7 describes — and §6's index. Until then a
patch older than its base is a patch nobody can use.

**Done, 2026-08-22** (PR #5). All of it, and the re-run is conditional: if the
fetched default-branch head still equals `base_sha` the packaged tree is
byte-identical to the one the suite already ran on, so re-verification is
*provably* redundant and the body says it was skipped and why. Otherwise the
suite re-runs in a gate-only cell — never host-side, because the applied tree
carries `.saffron/gates/*` exactly as the patch left them (§2). The base having
moved also invalidates the old baseline, so that cell runs the suite twice and
subtracts, which is §4.4 steps 2-3 applied to one commit.

Three things the build measured rather than reasoned, all now in §5.7. A
conflicting `git apply --3way` exits 1 **and still writes the file**, markers
staged — "apply failed" and "nothing happened" are different states. A degraded
apply exits **0**: preimage blob absent, context matching, and git falls back to
direct application, so conflict detection silently becomes a context match. And
`git commit` in a `--mirror` clone with no identity does not abort — it
auto-detects from the OS and attributes machine-written commits to the operator,
so `commit_squash` passes `-c user.email=saffron@localhost` on the command line.

`repos.origin` now holds the real remote; since v0 it held the mirror's *source*,
a local path, so nothing downstream knew where a pull request would go (§4.1).
