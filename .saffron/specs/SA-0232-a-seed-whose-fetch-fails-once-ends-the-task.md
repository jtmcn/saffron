---
id: SA-0232
title: A seed whose fetch from the mirror fails once ends the task, though a retry a minute later reads the same object
type: bug
priority: 1
estimated_lines: 170
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
      once, but not on a timeout. It first prints that seed's stderr, then
      pauses at least 60 seconds. The retry runs on the same volume, cleared
      of everything but `lost+found`, and checks out the base. The witness drives three
      fetch failures with different text. The mirror is absent for the first
      seed. One loose object is missing from the mirror for the first seed.
      A `git` first on PATH fails the first fetch with a fresh random token.
      Three other seeds each run once, never pause, print nothing and raise
      `CellRuntimeError`. One checks out a base the mirror lacks. One names
      a branch git refuses, "saffron/a..b". One is a run the runtime reports
      as timed out, exit 124.
    witness: tests/test_worktree.py::test_a_seed_whose_fetch_fails_once_is_retried_on_a_cleared_volume
    wrong_versions:
      - Every nonzero seed exit retried, so the base the mirror lacks is seeded twice.
      - The retry runs on the volume as the first seed left it, so `git remote add origin` fails on the remote that seed already added.
      - The retry gated on "Permission denied" in the stderr, so neither driven failure is retried.
      - The retry gated on "corrupt" in the stderr, so the absent mirror is not retried.
      - No pause before the retry.
      - A pause of 5 seconds.
      - A silent retry, so the first seed's stderr is printed nowhere.
      - The fetch left unmarked and every failure retried unless its stderr names the base's sha.
      - The fetch left unmarked and every failure retried unless its stderr contains "tree".
      - The fetch left unmarked and every exit 128 retried unless its stderr names the base's sha or contains "tree".
      - The fetch left unmarked and a failure retried when its stderr contains "corrupt" or "does not appear to be a git repository".
      - A timed-out seed retried as well as a failed fetch.
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
from a mirror missing one loose object exits 128. It prints "aborting due
to possible repository corruption on the remote side" and "bad pack
header", the live cases' own text. Checking out a base the mirror lacks,
after a good fetch, exits 128 with "unable to read tree". Checking out
onto the branch name "saffron/a..b" exits 128 with "is not a valid branch
name". Re-running `git remote add origin` in a directory
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
- **Retrying a seed that times out.** `runtime._call` returns exit code
  124 on its wall bound (`saffron/cell/runtime.py:280-287`). That is not a
  failed fetch. A retry would cost another 600 seconds. Whether the
  timed-out container stops is unmeasured.
- **DESIGN.md's seed steps.** §5.1 lists the seed as `git init`, remote
  add, fetch, checkout and remote remove, at DESIGN.md:653. The operator
  adds the retry to that sentence by hand in this spec's pull request.
- **Every caller.** `saffron/cell/session.py` and
  `saffron/phases/package.py` keep their calls as they are.
- **A layer's descendants.** b-60a399 keeps a failed seed from refusing
  them.

## Notes for the agent

**No mutant.** The retry, its pause and its print are new code, so no
mutant can pin their spelling. Criteria 1 and 2 declare a witness alone.
Criterion 3 passes today and must keep passing.

**Telling a failed fetch apart.** The exit code cannot, as measured
above. Stderr text is git's own wording, and it varies by version. Mark
the fetch step in the script itself, so the seed reports which step
failed. The witnesses run real git, so they judge the outcome. A stderr
test tuned to the driven text fails them. The random token defeats any
list of fetch messages. The refused branch name defeats a list of
checkout messages that names a tree or a sha.

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
the absent case. Rename one loose object away and back for the missing
case. `git clone --bare` from a local path hard-links its loose objects to
the origin, and they are mode 0444. A rename moves only the mirror's link,
so it needs no `chmod` and leaves the origin whole. For the token case,
write a `git` script that fails `fetch` with a fresh `uuid4` hex and runs
the real git otherwise. Put it first on PATH for the first seed alone.
Match `fetch` anywhere in the argv, so `git -c ... fetch` is caught too.
Exec the real git by an absolute path resolved before PATH is prepended,
or the script calls itself. Give the script a second mode that fails
`checkout` with a fresh `uuid4` hex, at the fetch mode's exit code. Drive
it as one more seed that runs once. Then no list of git's own
stderr text tells the two sides apart. Rules keyed on checkout text, such
as retrying unless stderr holds `tree` or `branch`, are unmeasured until
that seed is in.
Fake `run_ephemeral` outright for the timeout case. Count only the runs whose script fetches, so a separate
clearing run would not change the count. Patch the pause, so the suite
pays nothing. Record the pause in the same log as the seeds, so its order
is asserted. Assert the printed text against the first seed's own
stderr, not git's wording, so the test holds on any git.

**Why not "Permission denied".** The live text is a loose object the
mirror cannot open. A test cannot reproduce it where the suite runs as
root, since root ignores mode bits (`tests/test_policy.py:109` skips for
that reason). The cell image runs its tests as root. The missing loose
object gives the live cases' other two messages anywhere.

**Measured in the cell image.** On 2026-10-07 both prototype witnesses
ran in `saffron/cell:saffron`, built on `saffron/cell-base:python`. That
image reports git 2.47.3 and uid 0. The output was `2 passed in 1.09s`.

**Write no parametrised test.** Criterion 1's witness is one `def` that
drives the three fetch failures and the three single seeds in turn.

**Where the trace reaches.** The printed line reaches the batch log and
the terminal. It does not reach `events.jsonl` or `saffron watch`.
Routing it through `emit` would change the function's signature and edit
callers this spec forbids. That routing is a follow-up for b-6ac0cd.

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
copy of the base. `size_gate` counted 680 tokens over 214 changed lines,
48 in the source and 166 in the test. At 4 tokens a line that is 170
lines. Every wrong version above failed its criterion's witness on the
prototype, and both new witnesses failed with the source reverted. A
witness without the branch and token seeds let two of the unmarked
versions pass: the exit-128 one and the "corrupt" one.
