---
id: SA-0260
title: A mirror cloned from the local checkout hard-links its object files, so it shares their inodes
type: bug
priority: 1
estimated_lines: 51
estimate_measured: true
touches:
  - saffron/repos/mirror.py
  - tests/test_mirror.py
  - tests/test_consumes.py
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
  - saffron/preflight.py
  - saffron/replay.py
  - saffron/task.py
  - saffron/batch.py
  - saffron/ledger.py
  - saffron/cell/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/record/**
  - tests/test_cli.py
  - tests/test_worktree.py
  - tests/test_package.py
  - tests/test_preflight.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 23
max_attempts: 3
max_turns: 130
acceptance:
  - claim: >-
      `ensure_mirror` creates a mirror that shares no object file with the
      local checkout it clones. No regular file in the mirror's object store
      has the device and inode of a regular file in the checkout's object
      store, and the mirror borrows none of the checkout's objects through
      an alternates file. The witness drives the checkout's loose objects and its
      pack files, and the origin passed as a `Path` and as a `str`. Each
      mirror holds every ref and every commit the checkout holds, a ref that
      names no branch included. It still does, and still shares no
      file, after a second `ensure_mirror` call fetches a new commit into it.
    witness: tests/test_mirror.py::test_a_mirror_shares_no_object_file_with_the_checkout_it_is_cloned_from
    mutant:
      file: saffron/repos/mirror.py
      find: '"--no-local"'
      replace: '"--local"'
    wrong_versions:
      - The clone keeps git's local transport, so every object file in the mirror is a hard link to the checkout's.
      - The clone passes `--no-local` only when the origin arrives as a `str`, so a `Path` origin is still hard-linked.
      - The clone passes `--no-local` only when the origin arrives as a `Path`, so a `str` origin is still hard-linked.
      - The clone adds `--depth 1`, so the mirror lacks the checkout's older commits.
      - The mirror is a `--bare` clone, so it lacks the ref that names no branch.
      - The function repacks the operator's checkout before a local clone, which then links the new pack.
      - The clone passes `--shared` in place of the flag above, so the mirror copies no object file and reads the checkout's through `objects/info/alternates`, a path the seed's read-only mount cannot reach.
      - The mirror is built by `git init --bare` and a fetch from the checkout's path, so it has no `origin` remote and the second call's fetch raises.
---

## Context

Backlog item **b-6cd3c2**, measured in the spec loop's runs 31 and 32. Tier 1
in `docs/backlog/PRIORITY.md`. b-6ac0cd is the open measurement of the seed
refusals this item was found beside.

**How a mirror is made today.** `ensure_mirror` fetches into a mirror that
exists (`saffron/repos/mirror.py:69-73`). Otherwise it runs
`git clone --mirror <origin> <mirror_path>` (`saffron/repos/mirror.py:76`).
Every production caller passes the operator's checkout as the origin:
`saffron/cli.py:1498-1500`, `saffron/preflight.py:430`,
`saffron/preflight.py:500` and `saffron/replay.py:46`. `DESIGN.md` §5.1 says
the same: "`ensure_mirror` clones from the *local working copy*"
(`DESIGN.md:650`).

**What git does with that.** A clone whose source is a local path hard-links
the source's object files, unless told not to. Measured on 2026-10-10 in
`saffron/cell-base:python` (git 2.47.3). A plain mirror clone of a small
repository left 10 files under its `objects/` with a link count above 1. The
same clone with `--no-local` left none, and held its objects as one pack. A
later `git fetch` into it wrote one new loose object, also unshared. On the
host (git 2.54.0) the same plain clone of this repository's checkout took
0.13s, and with `--no-local` 0.67s.

**Why it matters.** A mirror is bind-mounted read-only into each seed
(`saffron/cell/worktree.py:87`), which fetches from it
(`saffron/cell/worktree.py:67-69`). b-6cd3c2's record has a rebuilt mirror
failing on the same two objects as the one it replaced, because the clone
linked the same inodes. Whether a shared inode causes those refusals is
b-6ac0cd's question, not this spec's. This spec only stops a new mirror
sharing them.

**A test that relies on loose objects in the mirror.**
`test_an_unreadable_consumed_entry_refuses_the_task_and_names_it` builds its
mirror with `ensure_mirror` (`tests/test_consumes.py:610`). It later unlinks
one blob's loose file from the mirror's `objects/`, after asserting the file
exists (`tests/test_consumes.py:689-692`). Once the mirror arrives as one
pack, that file does not exist and the assertion fails. Measured on a
prototype of this change: that is the only test in the default suite the
change breaks.

## Problem

Saffron builds each mirror out of the checkout's own object files. A mirror
made from scratch shares every one of their inodes, so it is never a copy of
the checkout. It is the same files under a second path.

## Out of scope

- A mirror that already exists and already shares inodes. Nothing detects or
  rebuilds one. Moving it aside, under `~/.saffron/mirrors/`, is the
  operator's hand step, and the next `ensure_mirror` clones it afresh.
- The cause of the "Permission denied" refusals on loose objects. b-6ac0cd
  carries that.
- The fetch branch of `ensure_mirror`. A fetch from a local path goes through
  git's pack transport and writes its own files, as measured above. The
  witness drives it anyway, so a rewrite of the clone cannot break it.
- An origin that is a remote URL. No production caller passes one, and git never links
  across a network transport. The witness drives local paths only.
- Every other caller of `ensure_mirror`, and the tests that stub it. None
  reads the mirror's object files.

## Notes for the agent

**The change is an edit.** Add `--no-local` to the clone's argument list in
`ensure_mirror`, with a one-line comment naming b-6cd3c2. Leave the fetch
branch and the error text as they are. The criterion declares a mutant on
that flag. Spell the flag once, as a string element of that list.

**The witness.** Add it at the end of `tests/test_mirror.py`. Use the file's
`origin` fixture and `git` helper, and its module-scope `ensure_mirror`
import, which exists at base.

1. In the checkout, run `git repack -q`, with no `-d`, so its objects include
   a pack. Then commit one new file, so it also holds loose objects written
   after the pack. Point `refs/saffron/probe` at `main^` with
   `git update-ref`.
2. Assert the checkout's `.git/objects` holds at least one `pack/*.pack` and
   at least one loose object file, matched by the glob `??/*`. Neither half
   of the claim is then vacuous.
3. Call `ensure_mirror` twice into two new paths, once with the checkout as
   a `Path` and once as `str` of it.
4. For each mirror, collect `(st_dev, st_ino)` of every regular file under
   its `objects/`, recursively. Assert that set is disjoint from the same
   set over the checkout's `.git/objects`. Collect both sets after each
   `ensure_mirror` call returns, never once before the calls. Assert the
   mirror has no `objects/info/alternates` file. Assert the mirror's
   `git for-each-ref --format='%(refname) %(objectname)'` output equals the
   checkout's, and so does the sorted output of `git rev-list --all`.
5. Commit one more new file in the checkout. Call `ensure_mirror` again on
   each mirror path with the checkout's `Path`, which takes the fetch branch.
   Repeat every assertion of step 4, with both sets collected afresh.

At base the first assertion of step 4 fails on the `Path` mirror. Measured on
host git 2.54.0, where both mirrors shared inodes with the checkout.

**The test it breaks.** In
`test_an_unreadable_consumed_entry_refuses_the_task_and_names_it`, make the
blob loose again before the lines that find and unlink it. For each
`*.pack` under the mirror's `objects/pack/`, read its bytes and delete every
file sharing its stem: the pack, its `.idx`, and its `.rev` where git wrote
one. Then pipe the bytes to `git -C <mirror> unpack-objects -q` with
`subprocess.run(..., input=..., check=True)`. Every object is then loose, and
the existing `loose.exists()` assertion holds. Keep every other assertion in
that test as it is. Measured on a prototype on host git 2.54.0, where the
test passed both before and after the change.

Commit after the witness passes. Uncommitted work dies with the cell.
