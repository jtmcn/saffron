---
id: SA-0382
title: "`ready_task`'s rebuilt review of an `ORPHANED` task checks a pool cut last and by hand, not first through `review_state`"
type: bug
priority: 2
estimated_lines: 90
estimate_measured: true
touches:
  - saffron/task.py
  - tests/test_task.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - pyproject.toml
  - uv.lock
  - .saffron/**
  - .claude/**
  - ontology/**
  - tests/ontology/**
  - docs/**
  - harness/**
  - images/**
  - records/**
  - hooks/**
  - saffron/gates/**
  - saffron/cell/**
  - saffron/phases/**
  - saffron/ledger.py
  - saffron/record/**
  - saffron/scheduler.py
  - saffron/reconcile.py
  - saffron/report/**
  - saffron/view/**
  - saffron/batch.py
  - saffron/cli.py
  - README.md
  - CLAUDE.md
  - tests/test_batch.py
  - tests/test_cli.py
  - tests/test_session.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
  - tests/conftest.py
  - tests/fixtures/**
budget_usd: 24
max_attempts: 3
max_turns: 90
risk: standard
acceptance:
  - claim: >-
      `ready_task`'s rebuild of an `ORPHANED` task calls
      `review.review_state(reviews, cut=...)` with the pool-cut witness
      `_pool_cut_witness` derives from `criterion-probes.json` and
      `wrong-versions.json`, computed before that call rather than
      checked by hand afterward. So a fresh pool-cut entry reaches
      `review_state`'s own `cut` branch, checked ahead of its
      errored-lens branch and its blocker branch, the same order the
      live cell's own call at `saffron/cell/session.py:3591` gives it. A
      task whose cell recorded both a fresh pool-cut entry and an
      errored lens is refused with `review_state`'s cut-branch wording
      naming that entry's witness, not the errored lens's name. The same
      holds when the fresh entry sits beside an anchored blocker
      instead: the refusal names the cut witness, not `REBUT`.
    witness: tests/test_task.py::test_ready_task_refuses_an_orphaned_task_on_a_cut_pool_before_an_errored_lens_or_a_blocker
    wrong_versions:
      - "`ready_task` calls `review_state(reviews)` with no `cut`, so an errored lens refuses the task before the pool cut is ever read."
      - "A blocker is read and routed to REBUT before the pool cut is checked, so the refusal names REBUT instead of the cut witness."
      - "The pool cut is still checked by its own hand-written sentence after `review_state` returns, rather than being folded into `review_state`'s own `cut` branch, so its wording never matches the live cell's."
      - "The pool cut is read from only one of the two probe files, so a cut recorded in `wrong-versions.json` goes unseen when an errored lens or a blocker is also present."
---

## Context

`SA-0380` taught `ready_task` to rebuild an `ORPHANED` task whose cell
went green. Part of that rebuild re-derives, by hand, a fact the live
cell already gets from `review.review_state`'s own `cut` parameter.

**The live cell checks a pool cut first.** `_drive_cell` calls
`review.review_state(reviews, cut=review_pool.cut)`
(`saffron/cell/session.py:3591`). `review_state` itself checks `cut`
before anything else. When `cut is not None` it returns
`REVIEW_INCOMPLETE` with its own wording right away
(`saffron/phases/review.py:1084-1088`). That check runs before the
errored-lens check (`saffron/phases/review.py:1089-1093`) and before
the blocker check (`saffron/phases/review.py:1094-1098`). A cut always
wins there, over either of the other two.

**`ready_task` checks a pool cut last, and by hand.** Its rebuild calls
`review_state(reviews)` with no `cut` at all (`saffron/task.py:1466`).
That call alone can already return `REVIEW_INCOMPLETE` for an errored
lens, or `REBUTTING` for a blocker. Either one is returned and acted on
before the pool cut is ever read. Only once neither of those two
refusals fired does `ready_task` compute
`_pool_cut_witness(criterion_probes) or _pool_cut_witness(wrong_versions)`.
It then refuses on that by hand, using its own sentence instead
(`saffron/task.py:1478-1487`). That sentence reads differently from
`_review_pool_cut`'s own text, and differently from `review_state`'s
own cut-branch text. `_pool_cut_witness` itself
(`saffron/task.py:1196-1211`) already turns a probe entry back into the
witness name `review_state`'s `cut` parameter wants. `ready_task` calls
it too late to matter.

**The result.** A task whose cell both cut REVIEW's pool and errored a
lens is refused for the wrong reason: the errored lens, never the cut.
The same holds for a task whose cell both cut the pool and raised an
anchored blocker: refused as `REBUT` instead. The live cell, handed the
same facts, reported the cut.

## Problem

`ready_task`'s refusal for an `ORPHANED` task can name the wrong cause
when more than one thing went wrong in the same cell. It restates
`review_state`'s own precedence by hand, instead of handing
`review_state` the fact it already knows how to rank first.

## Notes for the agent

Compute `cut_witness` from `criterion_probes` and `wrong_versions` (both
already read above this point, at `saffron/task.py:1449-1463`) before
calling `review_state`. Pass it as `review_state(reviews,
cut=cut_witness)`. Keep the two refusals that read `review_outcome` and
`review_why` exactly as they are. They already route correctly once
`review_state` ranks the cut first. Remove the hand-written cut refusal
that followed them. It is now redundant: a fresh cut reaches the same
return by way of `review_state`'s own `cut` branch instead. Leave
`_pool_cut_witness` itself untouched: it is still the function that
turns a probe entry into the witness name, called earlier instead.

Existing witnesses for criterion 3 of `SA-0380`
(`test_ready_task_refuses_an_orphaned_task_whose_review_would_not_end_ready`,
`tests/test_task.py:3976`) assert only `"ORPHANED"` and the cut
witness's own text are in the refusal's reason. They do not assert the
exact sentence around them. So they still pass once the wording changes
to `review_state`'s own cut-branch text. Do not edit that test.

Build the new witness on the same `_rt_orphaned_task` and
`_rt_pool_cut_entry` helpers that test already uses
(`tests/test_task.py:3782-3857`). Drive one task whose `findings.json`
holds an errored lens, and whose `criterion-probes.json` holds one
fresh cut entry. Drive a second task whose `findings.json` holds an
anchored blocker, and whose `wrong-versions.json` holds that same
fresh cut entry. Assert each refusal's reason carries `review_state`'s
cut-branch text, naming the cut entry's witness. Assert it does not
carry the errored lens's name in the first case, or the text `REBUT`
in the second.
