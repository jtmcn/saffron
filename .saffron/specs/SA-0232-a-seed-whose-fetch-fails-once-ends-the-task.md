---
id: SA-0232
title: A seed whose fetch from the mirror fails once ends the task, though a retry a minute later reads the same object
type: bug
priority: 1
estimated_lines: 133
estimate_measured: true
touches:
  - saffron/cell/worktree.py
  - tests/test_worktree.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
  - README.md
  - pyproject.toml
  - uv.lock
  - .saffron/**
  - .claude/**
  - ontology/**
  - tests/ontology/**
  - docs/**
  - images/**
  - harness/**
  - records/**
  - hooks/**
  - saffron/cli.py
  - saffron/task.py
  - saffron/batch.py
  - saffron/events.py
  - saffron/ledger.py
  - saffron/report/**
  - saffron/record/**
  - saffron/gates/**
  - saffron/agents/**
  - saffron/repos/**
  - saffron/phases/**
  - saffron/cell/session.py
  - saffron/cell/runtime.py
  - tests/test_session.py
  - tests/test_package.py
  - tests/test_runtime.py
budget_usd: 14
max_attempts: 3
max_turns: 100
acceptance:
  - claim: >-
      `prepare_worktree` retries a seed whose fetch from the mirror failed,
      once. It first prints that seed's stderr, then pauses at least 60
      seconds. The retry starts from the volume the failed seed left behind
      and checks out the base. The witness drives two fetch failures with
      different text. In one the mirror is absent for the first seed, and git
      2.54.0 prints "does not appear to be a git repository". In the other a
      loose object in the mirror is corrupt for the first seed, and it prints
      "is corrupt". A seed whose fetch succeeded and whose checkout then failed,
      on a base the mirror lacks, runs once. It never pauses, prints nothing,
      and raises `CellRuntimeError`.
    witness: tests/test_worktree.py::test_a_seed_whose_fetch_fails_once_is_retried_on_a_cleared_volume
    wrong_versions:
      - Every nonzero seed exit retried, so the base the mirror lacks is seeded twice.
      - The retry runs on the volume as the first seed left it, so `git remote add origin` fails on the remote that seed already added.
      - The retry gated on "Permission denied" in the stderr, so neither driven failure is retried.
      - The retry gated on "corrupt" in the stderr, so the absent mirror is not retried.
      - No pause before the retry.
      - A pause of 5 seconds.
      - A silent retry, so the first seed's stderr is printed nowhere.
  - claim: >-
      A seed whose fetch fails on both attempts raises `CellRuntimeError`
      whose message carries "seeding the worktree failed". It does so after
      exactly two seeds with one pause between them. The caller's leak
      ledger then names the state volume and no container.
    witness: tests/test_worktree.py::test_a_seed_whose_fetch_fails_twice_raises_after_two_attempts
    wrong_versions:
      - Three attempts, so a mirror that never answers is seeded three times.
      - A pause after the second failed seed as well, before the raise.
      - The container added to the leak ledger before the first seed, so a task whose seeds both failed reports a container nothing created.
  - claim: >-
      The seed's script still checks out exactly the base it is given. Two
      seeds at two bases differ in nothing but the base.
    witness: tests/test_worktree.py::test_prepare_worktree_checks_out_exactly_the_base_it_is_given
    preserves: true
---

## Context

Backlog item **b-f582ee**, tier 1, cites `DESIGN.md` §5.1. Found in the
spec loop's run 23 on `SA-0161`. Related item b-6ac0cd records two more
live cases, in run 28 and in batch 13.

**What the design asks.** §4.3's retry taxonomy says to retry idempotent
infrastructure races, and names the mirror fetch and worktree creation.
It says to fail fast on hangs and on genuine errors. Today the seed
retries nothing, and every failure ends the task at once.

**The seed today.** The function is defined at
`saffron/cell/worktree.py:41`. It creates the state volume, then seeds
the worktree volume in one ephemeral container, at
saffron/cell/worktree.py:86-105. That script runs under `sh -euc`. It
runs git's init, remote add, fetch and checkout steps, then removes the
remote and sets two config lines. The mirror is bind-mounted read-only.
On a nonzero exit it raises with "seeding the worktree failed: " and the
stderr, at saffron/cell/worktree.py:106-109. Nothing retries it. Only
after a seed succeeds does it add the container's name to the caller's
leak ledger and start the cell, at saffron/cell/worktree.py:114-126.

**Three callers, one function.** `cell_up`, defined at
`saffron/cell/session.py:971`, seeds the implementer's cell.
`critic_cell`, defined at `saffron/cell/session.py:1329`, seeds the gate
cell that re-runs the suite after IMPLEMENT, and the critic cell. In
PACKAGE, `_gate_cell` at `saffron/phases/package.py:525` seeds the
re-verification cells. Each caller creates the worktree volume before
the call. A retry inside the function reaches all three, and no caller
changes.

**What the live cases measured.** In run 23 `SA-0161` went green at
$14.63. Its gate cell's seed then failed with "unable to open loose
object ...: Permission denied" and "aborting due to possible repository
corruption on the remote side". The task ended `ORPHANED`, and the re-run
cost $20.30. Minutes later the same object read cleanly. Run 28's first
start of `SA-0203` failed the same way, and a retry a minute later
worked. In batch 13 a seed failed the same way and then printed "bad
pack header". A read of that object nine minutes later succeeded. The
cause is unknown. Each quoted message comes from `git upload-pack`
reading the mirror or from the pack it sent, so each came from the fetch.

**What git prints, measured** on the host's git 2.54.0 on 2026-10-07,
with the seed's own steps in a scratch directory. Fetching from an absent
mirror exits 128 with "does not appear to be a git repository". Fetching
from a mirror with one corrupt loose object exits 128 with "is corrupt".
Checking out a base the mirror lacks, after a good fetch, exits 128 with
"unable to read tree". Re-running `git remote add origin` in a directory
that already has the remote exits 3 with "remote origin already exists".
So the exit code alone cannot tell a failed fetch from a missing base.

## Problem

A seed that fails once ends the task, and the live failures pass on a
second read. When it happens after IMPLEMENT, the task loses a green
patch it paid for.

Retry it inside `prepare_worktree`:

- **What is retried.** A seed whose `git fetch` from the mirror failed is
  retried once, whatever git printed. The cause is unknown, and its text
  varied across the three live cases. A seed whose fetch succeeded is not
  retried. Its mirror read is done, and what failed after it is the base
  or the volume, which a second seed does not change. A base the mirror
  lacks then fails once rather than twice.
- **One retry.** Each live case passed on its next read. A mirror that
  fails twice is not transient in the sense this spec handles.
- **A pause first, of at least 60 seconds.** Every measured recovery came
  a minute or more after the refusal. An immediate retry is unmeasured.
- **A clean start.** The failed seed leaves `.git` and its `origin`
  remote on the volume. The retry starts as the first seed did, so its
  `git remote add origin` meets no remote.
- **A trace.** Print one line to stdout before the pause. It carries the
  failed seed's stderr. A batch's log is its only human-readable record,
  and b-6ac0cd needs every occurrence to find the cause.

## Out of scope

- **Resuming an `ORPHANED` task's green patch.** The item's second half
  asks for a command that packages it. That is an operator decision, and
  the item stays open for it.
- **The refusal's cause.** b-6ac0cd owns the measurement. This spec
  survives the refusal and does not explain it.
- **A seed that times out.** `runtime._call` returns exit code 124 on its
  wall bound (`saffron/cell/runtime.py:280-287`). That is not a failed
  fetch, and it is not retried.
- **Every caller.** `saffron/cell/session.py` and
  `saffron/phases/package.py` keep their calls as they are.
- **A layer's descendants.** b-60a399 keeps a failed seed from refusing
  them.

## Notes for the agent

**No mutant.** The retry, its pause and its print are new code, so no
mutant can pin their spelling. Criteria 1 and 2 declare a witness alone.
Criterion 3 passes today and must keep passing.

**Telling a failed fetch apart.** The exit code cannot, as measured
above. Stderr text is git's own wording. The measurement above used git
2.54.0, and the cell image runs 2.39.5, where the wording is unmeasured.
Mark the fetch step in the script itself, so the
seed reports which step failed. The witnesses run real git, so they
judge the outcome and not the mechanism.

**Clearing the volume.** Clear it inside the seed's own ephemeral
container, so the volume's name and the caller's leak ledger do not
change. A fresh volume holds `lost+found`, so leave that alone. Clearing
on every seed keeps the script the same on both attempts. Criterion 3's
test then still holds. Clear at the start of a seed and never after a
failure. §4.3 keeps a failed task's volume for the operator to read. A
seed that fails twice leaves the volume as its second attempt left it.

**The witnesses' substrate.** `_no_cell_runtime` in
`tests/test_worktree.py` already runs the seed's real script against a
host directory. `test_a_stacked_worktree_holds_the_parents_real_commits_and_only_the_childs_new_commit_is_exported`
builds a real bare mirror for it with `_seed_repo` and `git clone
--bare`. Wrap the faked `run_ephemeral` so the first seed meets a broken
mirror and the second a whole one. Rename the mirror away and back for
the absent case. Overwrite one loose object's bytes and restore them for
the corrupt case. Count only the runs whose script fetches, so a separate
clearing run would not change the count. Patch the pause, so the suite
pays nothing. Record the pause in the same log as the seeds, so its order
is asserted. Assert the printed text against the first seed's own
stderr, not git's wording, so the test holds on any git.

**Why not "Permission denied".** The live text is a loose object the
mirror cannot open. A test cannot reproduce it where the suite runs as
root, since root ignores mode bits (`tests/test_policy.py:109` skips for
that reason). The corrupt loose object is the nearest failure the suite
can drive anywhere.

**Write no parametrised test.** Criterion 1's witness is one `def` that
drives both fetch failures and the missing base in turn.

**The existing failed-seed test.**
`test_a_failed_seed_leaves_no_container_in_the_leak_ledger` fakes every
seed as exit 1 with "bad sha". If your mechanism reads that as a failed
fetch, the test pays the real pause. Patch the pause there too.

**The `prose` gate** counts every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words. Do not grow `prepare_worktree`'s docstring. It
is past ten lines already, and each added line is a new
`docstring-length` hit. Put the why in a comment of one or two lines.

**Size.** `saffron/cell/**` is in `elevate_on`, so `size` blocks at the
`bug` ceiling of 1300 tokens (`saffron/gates/core/size.py:26`). On
2026-10-07 a prototype of this change and both new witnesses ran on a
copy of the base. `size_gate` counted 533 tokens over 169 changed lines,
48 in the source and 121 in the test. At 4 tokens a line that is 133
lines. Every wrong version above failed its criterion's witness on the
prototype, and both new witnesses failed with the source reverted.
