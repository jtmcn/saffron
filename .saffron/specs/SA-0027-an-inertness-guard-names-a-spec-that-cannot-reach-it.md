---
id: SA-0027
title: an inertness guard names the spec that will retire it, and nothing checks that spec's touches can reach the file
type: feature
priority: 2
touches:
  - saffron/scheduler.py
  - saffron/repos/mirror.py
  - saffron/cli.py
  - tests/test_scheduler.py
  - tests/test_mirror.py
  - tests/test_cli.py
  - docs/BACKLOG.md
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - saffron/cell/**
  - saffron/phases/**
  - saffron/gates/**
  - saffron/report/**
  - saffron/ledger.py
  - saffron/reconcile.py
budget_usd: 14
max_attempts: 4
max_turns: 120
risk: elevated
---

## Context
Saffron ships capabilities inert: `SA-0022`, `SA-0025` and `SA-0026` each built
one layer of stacking and turned nothing on, because a half-wired capability is
worse than both its presence and its absence. Inertness is asserted — a test
that the capability is off, a comment saying which spec will turn it on — and
the assertion names its own successor.

Nothing checks that the named successor can reach the assertion. A spec's
`touches` is the only thing it may change; the `scope` gate refuses the rest.
So a guard that says *"`SA-0026` will retire this"*, sitting in a file
`SA-0026`'s `touches` does not cover, hands that spec's agent a choice between
a false green and a `scope` refusal — and neither is the work.

§4.2.1's fifth refusal is this defect's sibling and was written from the same
kind of corpse: **a spec whose acceptance criteria name a path no `touches`
pattern matches** is unsatisfiable by construction (`SA-0005`, $5.34, dead at
turn 61). That refusal reads the spec's own text. This one reads the
repository's, which is the half `SA-0005`'s lesson could not cover.

## Problem
- **Measured twice in one run, and the agent behaved correctly both times.**
  `SA-0025` planted `tests/test_package.py::test_the_operators_reachable_packaging_path_is_unstacked`,
  asserting the literal string `parent_branch` never appears in
  `saffron/cli.py`. `SA-0026` is the spec that makes that false, and
  `tests/test_package.py` is not in its `touches`. Its agent spelled the
  keyword `{"parent" + "_branch": ...}`, said so in a comment, and recorded the
  box it was in under `BACKLOG.md` item 33. Both review lenses flagged the
  result; an operator deleted the guard by hand. Separately, the same spec
  could reach neither `saffron/cell/session.py`'s nor
  `saffron/phases/package.py`'s comments saying stacking was off — both
  `forbidden` to it, both corrected by hand at review.
- **The check is cheap and the failure is not.** A `git grep` against the
  mirror at `base_sha` costs no export, no working tree and no network. The
  failure it prevents costs a full cell, and its two outcomes are a test that
  is green for a reason unrelated to what it was written to detect, or a
  `scope` refusal on work the spec was correct to do.
- **Review caught all three, and review is not a control.** §2's line is that
  every control that matters lives outside the cell. A defect a lens happens
  to notice is not one.

## Acceptance criteria
- [ ] A marker convention exists and is stated where the code is: a comment or
      docstring carrying `saffron:retired-by <SPEC-ID>` declares that this file
      asserts something the named spec is expected to falsify
- [ ] `saffron/repos/mirror.py` reads those markers out of a mirror at a given
      sha without an export, a checkout or a working tree, returning the
      `(path, spec_id)` pairs it found — and a repository with no markers is
      an empty result, never an error
- [ ] `saffron/scheduler.py` gains a pure refusal, in the shape
      `protected_touch_refusal` already has: it takes the spec and the markers
      and returns the reason or `None`, and it names **which file** and **which
      pattern set** failed to reach it
- [ ] Reachability is decided with `scope.matches`, the same function `scope`,
      `integrity`, `size` and §4.2.1's fifth refusal all use — "declared" means
      one thing in every gate, never a second and more permissive rule
      invented here
- [ ] A marker inside the spec's own `forbidden` list refuses too, and says so
      differently: a spec that may not touch the file cannot retire the guard
      either, and the two are different mistakes for an operator to fix
- [ ] The refusal runs on **both** paths — gate 0 (`build_queue`) and
      `saffron cell` — the way `SA-0023`'s does. All three measured instances
      happened on the attended path, so a refusal that only reaches the batch
      guards nothing that has actually broken
- [ ] A marker naming a spec id that is not this candidate is not this
      candidate's problem, and a marker naming a spec id no file in the specs
      directory declares gets its own line rather than silence — `SA-0024`'s
      `done/` rule, applied to the same class of dangling reference
- [ ] `docs/BACKLOG.md` records the convention, its two measured instances, and
      what this refusal still cannot see
- [ ] Every new test runs with no network and no cell, against a real mirror
      built in a `tmp_path` — not a fake grep

## Out of scope
**Planting markers on anything that exists today.** After `SA-0026` merges
there is no live inertness guard in this repository: the one that existed was
deleted at review. This spec arms the check and documents the convention; the
first marker is planted by the next spec that ships something inert. A test's
own fixture is the only marker this spec creates.

**`DESIGN.md` and `CONTEXT.md`.** Both `forbidden`. §4.2.1's refusal count and
§3.1's spec-format description both move when this lands, and an operator
corrects them — the Notes below carry the sentences.

**Any check on comments that merely *cite* a spec.** `saffron/scheduler.py`
names `SA-0020` and `SA-0026` in half a dozen places as attribution, and none
of those is a claim about the future. The marker is opt-in for exactly this
reason: a heuristic over every `SA-NNNN` mention would refuse most of the
repository.

**Retiring the marker once the spec ships.** The guard's own removal deletes
the marker with it. Nothing needs to garbage-collect one, and a marker left
behind naming a merged spec is caught by the dangling-reference line above.

## Notes for the agent
**Commit after every coherent step, before you run anything by hand.** A recent
task on this repository made zero commits across 141 turns and lost all of it
at teardown, $14.61 for nothing. `export_patch` diffs commits; uncommitted work
is invisible to the record and dies with the cell.

**`protected_touch_refusal` is the shape, and it is not a coincidence.**
`SA-0023` faced the same question — a spec-level refusal needing a fact the
repository holds — and answered it by putting a pure function in `scheduler.py`
and the fact-gathering in the caller. `saffron/scheduler.py:287` and its two
call sites (`_refuse`, and `cli._run_cell`) are the whole pattern. Follow it
rather than inventing a second one; core invokes declared gates and reads
repository facts through `repos/`, never the other way round.

**`git grep` takes a tree-ish.** `git -C <mirror> grep <pattern> <sha>` reads
the bare mirror directly — no export, no worktree, no `git archive`. Its output
prefixes each path with the sha, which is not part of the path. Run the tool
and read what it actually prints; do not assume the format.

**A repository with no matches exits non-zero.** `git grep` returns 1 when it
finds nothing, which is not an error and must not become one. This is the
`error` ≠ `fail` line in miniature: a gathering step that reports "nothing
here" as a break would abort every task in a repository that has no markers,
which is every repository including this one on the day this ships.

**The documentation half is by hand, and here are the sentences.** Backlog item
30's rule. `DESIGN.md` is forbidden, so an operator corrects these afterwards:

- §4.2.1's *"The refusal gate refuses seven things"* — it refuses eight, and
  the eighth belongs beside the fifth, since they are the same defect read from
  two different sources.
- §3.1's description of what a spec file declares, which does not mention that
  the repository can declare something about a spec.

**A test that greps a string it planted in the same function proves nothing
about the mirror.** Build a real bare mirror, commit a file carrying a real
marker, and read it back through the function under test at a real sha.
