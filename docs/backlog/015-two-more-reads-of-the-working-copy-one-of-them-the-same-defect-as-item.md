---
id: 15
title: Two more reads of the working copy, one of them the same defect as item 13
status: done
tier: null
closed: 2026-08-24
specs: []
prs: []
commits: [2d67d0d]
cites: [§4.2, §5.1]
related: [13, 16]
---

## Problem

Found while closing item 13, measured, not reasoned — and left open because
both sit in PACKAGE rather than in the cell.

**`cli.py` loads the policy for PACKAGE from `repo`.** `package()` then hands
it to `reverify`, which resolves `gate_executables` against gates exported from
`fetch_head` — item 13's asymmetry exactly, one phase later and against a
different sha. A working copy declaring a role `fetch_head` does not carry
makes the re-verification gate error, which raises as infrastructure at the
point the task is otherwise `READY_FOR_REVIEW`. It also feeds
`policy.integrity.test_paths` into the pull request body, so the body describes
the checkout's declaration rather than the one the packaged commit was verified
under. **Done looks like:** `package()` loading its policy from the export it
already makes at `fetch_head`, which means dropping the `policy` parameter
rather than threading a second one.

**The cell image is built from the working copy's `.saffron/Dockerfile`**
(`image.build_cell_image(repo)`) while the gates, the policy and the base tree
all come from `base_sha`. This one may be correct as it stands — the image is
the toolchain, not the judgment, and an operator testing a new Dockerfile wants
the branch's — but it is now the only member of the family that reads the
checkout, and nothing says which way it is meant to go. **Done looks like:**
§5.1 saying so either way.

## Record

**Status:** **done**, in `2d67d0d` (*fix(package): PACKAGE was verified under
the checkout's policy, not the base's*). `package.py:676` reads
`load_policy(gates_dir)`. **Item 16 is what this fix created** and stays open:
nothing records *which* policy PACKAGE verified under.

**Done, 2026-08-24.** `package()` exports `.saffron` at `fetch_head` and reads
its policy from it, unconditionally rather than inside the re-verification
branch — the body's `test_paths` is read on every path, so a policy loaded only
when the base moved would have been half a fix. The `policy` parameter is gone
and `cli` no longer reads `.saffron/policy.yaml` at all, which took the refusal
read with it: it existed to keep an invalid checkout policy from costing a run,
and the checkout's policy is now read nowhere on the cell path. One measured
consequence for onboarding: a repo whose default branch carries no
`.saffron/policy.yaml` cannot package, the same way it cannot start a cell.

**Done, 2026-08-24: deliberate, and §5.1 says so.** The image stays the
checkout's. The drift is real and now named rather than implied — this repo's
own Dockerfile `COPY`s `pyproject.toml` and `uv.lock` out of the build context,
so a branch that touches the lock bakes those dependencies into an image
running `base_sha`'s code. It is accepted because the image is the toolchain
and not the judgment. **The scheduler reopens it**: unattended there is no
checkout for the phrase to mean anything, and the answer there is a build
context exported from `base_sha` like every other input. That is v1+ work and
is not filed as an item here, because §4.2 has to exist before it can be
written.
