---
id: SA-0016
title: an unsatisfiable spec is discovered only after it burns its budget
type: feature
priority: 1
depends_on:
  - SA-0015
touches:
  - saffron/scheduler.py
  - tests/test_scheduler.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - docs/**
  - saffron/cell/**
  - saffron/phases/**
  - saffron/report/**
budget_usd: 14
max_attempts: 4
max_turns: 100
risk: elevated
---

## Context
Third of `SA-0009`'s four-way resplit (`SA-0014`'s Context has the full
history — 990 lines, `EXHAUSTED`, `docs/BACKLOG.md` item 25). `SA-0015` built
`build_queue`'s done/re-queue filter and its ordering, refusing only
unparseable specs. This spec adds the other four of `DESIGN.md` §4.2.1's six
refusals to the same function — the ones that need a candidate's `touches`,
its acceptance criteria, or GitHub's state — including the one with a corpse
behind it.

## Problem
`saffron/scheduler.py` has no refusal for: an open pull request from another
task already targeting a spec; a `touches` overlap with an open PR's changed
files; acceptance criteria naming a path outside `touches`; or a non-empty
`depends_on`. Each is cheap to check without a cell and expensive to
discover inside one — `SA-0005` burned $5.34 and died at turn 61 finding the
third of these the hard way.

## Acceptance criteria
- [ ] Four more refusals join `build_queue`'s output, each with a test
      producing exactly that refusal: an open pull request from another
      task, a `touches` overlap with an open pull request's files,
      acceptance criteria naming a path outside `touches`, and a non-empty
      `depends_on`
- [ ] A criterion "names a path" when it contains a repo-relative path
      token; the token is matched against `touches` with `scope.matches`, a
      bare filename is **not** matched against a `touches` entry that
      differs by directory, and the whole check is skipped when `touches` is
      empty
- [ ] The two refusals needing GitHub take an injected runner in the
      `GhRunner` shape `saffron/phases/package.py` already uses, and every
      test in `tests/test_scheduler.py` runs with no network and no cell
- [ ] A smoke test reproduces this repository's own measured queue (Notes)
      against a temporary copy of `.saffron/specs/`

## Out of scope
Nothing here calls `saffron cell`, writes to the ledger, or is reachable
from the command line — `saffron queue`'s CLI wiring is `SA-0017`.
`saffron/phases/**`, `saffron/cell/**` and `saffron/report/**` are forbidden.

## Notes for the agent
**This is the refusal with a corpse behind it, and it is the one most likely
to be built blind.** Two ways to get it wrong, both measured on the real
spec:

- Built on a truncated `spec.acceptance_criteria`, it **passes `SA-0005`
  clean** — `SA-0014` already fixed the truncation, but a test whose fixture
  is a single-line criterion would prove nothing about this bug either.
- `scope.matches("intake.py", "saffron/intake.py")` is `False`. A gate that
  quietly resolves bare filenames against `touches` by suffix is a
  *different, more permissive* rule than the one `scope` enforces, and the
  two must not drift.

**What `saffron queue` should print on this repository, measured 2026-08-26
against `~/.saffron/ledger.db`:** `SA-0001` and `SA-0008` queued, everything
else filtered out with a `READY_FOR_REVIEW` task at the same `spec_sha`, and
nothing refused. In particular the `depends_on` refusal will not fire on
`SA-0006` or `SA-0007` — `SA-0015`'s filter removes them first, because both
have a task at exactly their current sha. Use this as a smoke check, not as
proof the refusals work; the refusals need their own fixtures.

The injected-runner shape already exists: `GhRunner` in
`saffron/phases/package.py`, read for its signature only — that file is
forbidden.

**A test that constructs the value it then asserts on proves nothing about
the caller.** That is the defect that shipped `SA-0005` green (item 18) and
the one the critic caught in `SA-0007`. Exercise these refusals through
`build_queue`, not by handing a fake candidate straight to a refusal
function.

Commit after each coherent step. Uncommitted work dies with the cell.
