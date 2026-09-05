---
id: SA-0055
title: readiness and the scan each fetch the same mirror, so a night pays twice for one pinned base
type: refactor
priority: 3
touches:
  - saffron/cli.py
  - tests/test_cli.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - ontology/**
  - docs/**
  - saffron/batch.py
  - saffron/preflight.py
  - saffron/watch.py
  - saffron/events.py
  - saffron/cell/**
  - saffron/phases/**
  - saffron/report/**
  - saffron/gates/**
  - saffron/ledger.py
  - saffron/scheduler.py
  - saffron/reconcile.py
  - saffron/replay.py
budget_usd: 8
max_attempts: 3
max_turns: 70
risk: standard
acceptance:
  - claim: >-
      Resolving a queue can be handed a base that is already pinned — the
      mirror, the real remote and the default-branch head — and when it is, it
      does not derive them again. Asserted by counting: the three underlying
      operations run zero times inside the resolution, rather than by
      asserting that the returned fields happen to match.
    witness: tests/test_cli.py::test_a_resolution_given_a_pinned_base_does_not_derive_one
  - claim: >-
      Handed nothing, it derives the base itself exactly as it does today.
      This is the attended command's path and the reason the argument is
      optional rather than required: `saffron queue` runs no readiness check
      and has no pinned base to give. The default is the full derivation, not
      a stub that returns something empty.
    witness: tests/test_cli.py::test_a_resolution_given_no_pinned_base_still_derives_its_own
  - claim: >-
      One night fetches the mirror once. Counted across the whole `saffron
      batch` command, end to end: `ensure_mirror`, `real_remote` and
      `fetch_default_branch` each run exactly once, where each ran twice
      before. This is the defect itself and the only witness that measures it.
    witness: tests/test_cli.py::test_a_night_pins_its_base_once
  - claim: >-
      Readiness still runs before the scan. The order is not an accident and
      must not be traded away for the sharing: a scan that raises before the
      batch row exists leaves a night with no record it was attempted, which
      is what §4.4's step 1 before step 4 prevents. The pinned base travels
      downward from readiness to the scan, never upward.
    witness: tests/test_cli.py::test_readiness_still_runs_before_the_scan_it_now_feeds
  - claim: >-
      A readiness failure still means no scan at all — not a scan given a
      half-built base. When readiness stops the night, the three operations
      have run once, for readiness, and the resolution never happens.
    witness: tests/test_cli.py::test_a_failed_readiness_still_scans_nothing
  - claim: >-
      `saffron queue` prints exactly what it printed before, asserted against
      the output rather than against the fact that output happened. It is the
      caller that gains nothing from this change and must lose nothing to it.
    witness: tests/test_cli.py::test_the_printed_queue_is_unchanged_by_sharing_the_base
  - claim: >-
      `saffron batch` prints exactly what it printed before — the plan header,
      the reconcile summary, the refusals and the scan gaps. The night's log
      is its only human-readable record, so a refactor that quietly drops a
      line from it is not a refactor.
    witness: tests/test_cli.py::test_the_printed_night_is_unchanged_by_sharing_the_base
---

## Context

`saffron batch` establishes a repo's pinned base twice per night.

`preflight.check_readiness` calls `ensure_mirror`, `real_remote` and
`fetch_default_branch`, in that order, and returns the `mirror`, `url` and
`base_sha` it found — three fields that exist on `Readiness` for exactly this
reason. `_resolve_queue` then calls the same three functions and throws that
answer away.

§4.2.1's argument for hoisting preflight was that a batch does this work **once
per run** rather than once per task. It now does it twice per run.

## Problem

- **The second fetch is paid on every night, for nothing.** Two mirror fetches
  seconds apart, the second a no-op that still forks `git` and waits on the
  network. Harmless at K=1 against one repo, which is why this is not urgent;
  it doubles the cost of *starting* a night at multi-repo, which is where §9
  is going.
- **Two derivations of one fact can disagree.** They are seconds apart and
  read the same remote, so today they do not. Nothing says they cannot: a
  default branch that moves between the two calls gives readiness one
  `base_sha` and the scan another, and the night then runs against a base its
  own readiness never checked.
- **The answer is already being returned and discarded.** `Readiness` carries
  `mirror`, `url` and `base_sha`, and the only caller that receives them
  ignores all three.

## The shape

`_resolve_queue` takes a pinned base as an **optional** argument. Given one, it
uses it; given none, it derives its own exactly as now.

Optional is the decision here, and it is not the same shape as `SA-0050`'s
readiness default, which was a permissive stub that made a real gate vacuous.
The default here is the **full derivation** — the work it does today, unchanged
— and it exists because `saffron queue` genuinely has no pinned base to offer:
it runs no readiness check, deliberately, because an operator looking at the
queue should not need a live token. A required argument would force that
command to invent one.

Carry the three values together, not as three adjacent parameters. They are one
fact about one repo — the tree this night is pinned to — and `check_readiness`
is in this repo's history for the opposite reason: four adjacent positional
`Path`s, one of which is emptied, where transposing two type-checked cleanly
and deleted the ledger.

## Out of scope

**Changing `preflight.py`.** It is `forbidden`. `Readiness` already carries the
three fields; nothing there needs to change for this to work.

**Changing the order.** Readiness runs first and the scan second. That order was
established by review — a scan that raises before `run_batch` opens the batch
row produces a night with no record it was attempted — and this spec makes the
first step feed the second, never the reverse.

**Making `saffron queue` do a readiness check.** It runs without a token on
purpose. This spec must not make an attended queue inspection require one.

**Sharing anything else.** The export, the reconcile, the slug and the scan
itself stay exactly where they are and run exactly once each, as today. Only
the pinned base is shared, because it is the only thing computed twice.

**Caching between nights.** Nothing persists across invocations. The sharing is
within one command's own call, and a second `saffron batch` five minutes later
fetches again, correctly.

## Why this is worth doing now rather than later

It is small, it is contained to one module, and it is a defect the batch review
round *introduced*: hoisting readiness above the scan is what turned one
derivation into two. Fixing it through the machine that produced it is also the
cheapest real test of that machine — a night that runs one spec is the first
measurement of the budget gate, the breaker and packaging under a batch, none
of which the empty-queue run on 2026-09-05 touched
(`docs/evidence/2026-09-05-first-batch-drained.md`).
