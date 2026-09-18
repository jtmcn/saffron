---
id: SA-0108
title: The projection is never compared with the checked walk, so Appendix T's decision rule has no instrument
type: feature
priority: 2
depends_on: [SA-0106, SA-0107]
touches:
  - saffron/chain_walk.py
  - saffron/cli.py
  - tests/test_chain_walk.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
  - pyproject.toml
  - uv.lock
  - .saffron/**
  - ontology/**
  - tests/ontology/**
  - docs/**
  - images/**
  - harness/**
  - saffron/report/**
  - saffron/phases/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/agents/**
  - saffron/projection.py
  - saffron/batch.py
  - saffron/ledger.py
  - saffron/scheduler.py
  - saffron/task.py
  - saffron/replay.py
  - saffron/events.py
budget_usd: 15
max_turns: 80
acceptance:
  - claim: >-
      The checked walk follows §4.1's foreign keys for each merged task and
      calls its chain whole when every stored file it names exists. It reads no
      event log and states no edge.
    witness: tests/test_chain_walk.py::test_the_checked_walk_calls_an_overwritten_chain_whole_and_a_missing_file_broken
  - claim: >-
      Every merged pull request Q4 drops while the checked walk calls its chain
      whole is printed. One whose stored file is missing is not printed, since
      the checked walk sees it too. A task the projection could not attribute to
      its own events is counted apart and never printed as a break.
    witness: tests/test_chain_walk.py::test_the_output_names_only_breaks_the_checked_walk_calls_whole
  - claim: >-
      `saffron batch` materializes once, after its loop returns, whatever stop
      reason the loop returned, and prints the result. A materialization that
      raises leaves the batch's exit code as the loop decided it.
    witness: tests/test_chain_walk.py::test_a_batch_materializes_once_and_a_raise_leaves_its_exit_code
---

## Context

`DESIGN.md` Appendix T (rev 24) and backlog item b-946f03 reopened the emitter.
The appendix names a decision rule. Q4 must drop at least one merged pull
request that the checked walk reports as whole. `SA-0107` builds the projection
Q4 runs over. This spec builds the other half of the comparison, prints the
result and runs it at the end of every batch. Read the appendix and
`saffron/projection.py` as `SA-0107` landed it before writing anything.

## Problem

Nothing compares the projection with anything. The checked walk the rule names
does not exist. The projection is not materialized by any command, so the rule
never runs over the merged history.

`saffron batch` calls `run_batch` (`saffron/cli.py:776`) and then branches on
its stop reason to choose an exit code (`saffron/cli.py:794-810`). The loop's
stop reasons are a closed set (`saffron/batch.py:36`). A materialization that
raises must not become one, and must not change the exit code.

## Out of scope

- **The projection itself.** `SA-0107` owns `saffron/projection.py`, and it is
  forbidden here. A defect found in it is reported, not fixed in this spec.
- **An on-demand command.** Every materialization covers the whole ledger. The
  first batch after this lands therefore runs the rule over the merged history.
- **Nothing here controls execution.** §1.4's bullet stands. No scheduling
  decision reads the projection or the comparison.
- **The recorded diff length.** A diff overwritten by one of the same length is
  not detected (`SA-0107`, *Out of scope*). The printed result says so once, so
  a zero is not read as stronger than it is.

## Notes for the agent

This spec creates `saffron/chain_walk.py` and its tests, and edits
`saffron/cli.py`. No criterion pins text the existing code determines, so each
declares a witness and no mutant, and `witness` will report `skip` for them.

**The comparator.** The checked walk follows the ledger's foreign keys
(`saffron/ledger.py:58-139`). It then checks that each stored file in the task's
batch-tree directory exists (`saffron/cell/session.py:1285`). It must not read
`events.jsonl` or compare hashes. Doing so would make it the projection, and the
comparison would say nothing.

**Compare like with like.** Run the walk over the same tasks the projection
kept. A task the projection left out as unattributable is counted apart and
never printed as a break. Take the reasons from what `SA-0107`'s
materialization returns, rather than deciding them again.

**Where things are.** `saffron/cli.py:152` resolves the batch tree from
`--home`. Pass that path, the ledger and an output path under `--home` into the
materialization. Never spell `~/.saffron` in `saffron/chain_walk.py`.

**Materialize from `saffron/cli.py`,** after `run_batch` returns and before any
exit-code branch. The third criterion's witness drives `INCOMPLETE` as well as
`DRAINED`, because only the exit-0 path would pass a `DRAINED`-only test.
`SA-0106` edits the same command's scan, so read what it landed first.
Materialization runs once per batch and not once per rescan.

**Build the second criterion's fixture with three merged tasks.** One is whole.
One has a later task of the same spec overwriting its diff. One has its diff
deleted. Only the second is printed. Add a fourth task that the projection
returned as unattributable, and assert that it is counted and not printed.
Put a non-ASCII character in every fixture diff, for the reason `SA-0107`'s
notes give.

**Import anything new inside the test body.** Module scope does not work. A
module-scope import of a name this change adds turns `revert`'s reverted run
into a collection error. `revert` reads that error as `skip`, and the
anti-theater gate then checks nothing.

Write each test against the unfixed code before trusting it.
