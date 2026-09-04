---
id: SA-0051
title: a night has a loop and no command, and the scan that feeds it exists twice
type: feature
priority: 1
depends_on:
  - SA-0050
touches:
  - saffron/cli.py
  - tests/test_cli.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - saffron/batch.py
  - saffron/watch.py
  - saffron/events.py
  - saffron/cell/**
  - saffron/phases/**
  - saffron/report/**
  - saffron/gates/**
  - saffron/ledger.py
  - saffron/scheduler.py
  - saffron/preflight.py
  - saffron/reconcile.py
  - saffron/replay.py
budget_usd: 10
max_attempts: 3
max_turns: 80
risk: standard
acceptance:
  - claim: >-
      The command runs a night, taking the repo, a budget and a deadline, and
      its two defaults are the ones §4.2.1 fixes: the repo defaults to the
      working directory, matching the attended command beside it, and the
      budget defaults to 50, which is §7.1's own recommendation sized against
      the queue rather than against capacity.
    witness: tests/test_cli.py::test_saffron_batch_runs_a_night_with_the_defaults_4_2_1_fixes
  - claim: >-
      The deadline is given as a wall-clock time of day and resolves to its
      next occurrence, so a time earlier in the day than now means tomorrow
      rather than a window that has already closed. Driven with an injected
      now, and with a time in the past, which is the case an operator hits at
      22:00 every single night they ask for 06:30.
    witness: tests/test_cli.py::test_a_deadline_earlier_than_now_resolves_to_tomorrow
  - claim: >-
      Neither a concurrency flag nor a multi-repo flag exists. §4.2.1 refuses
      both by name — a flag for a knob with one position is the same defect in
      a command that item 18 found in a dataclass — so their absence is a
      witness rather than an omission, and adding one later is a decision
      someone has to make on purpose.
    witness: tests/test_cli.py::test_the_batch_command_offers_no_concurrency_or_multi_repo_flag
  - claim: >-
      Draining, running out of budget and hitting the deadline all exit 0.
      §4.2.1: a batch that drains with three failed tasks did its job, and the
      individual outcomes are the morning queue's business.
    witness: tests/test_cli.py::test_the_three_ordinary_stop_reasons_all_exit_zero
  - claim: >-
      The breaker firing exits 2, and so does a readiness failure that takes
      the whole night. Both say the infrastructure failed, which is what an
      unattended caller reads to decide whether tomorrow is worth attempting.
    witness: tests/test_cli.py::test_infrastructure_and_a_failed_readiness_both_exit_two
  - claim: >-
      Exit 1 is never returned, across every stop reason. §4.2.1 reserves it
      rather than reusing it: a batch is not a task, so letting 1 mean anything
      here would merge two vocabularies that answer different questions. A
      test walks all four stop reasons and asserts none produces it.
    witness: tests/test_cli.py::test_a_batch_never_exits_one_whatever_stopped_it
  - claim: >-
      The batch's scan asserts the premise a batch is entitled to and the
      attended scan is not: one batch runs at a time, so nothing is
      legitimately in flight when a night starts, and an in-flight row is a
      corpse a dead scan left behind. It is stamped orphaned before filtering
      and re-queues by the ordinary rule. The witness drives a task left
      implementing and finds it in the night's queue.
    witness: tests/test_cli.py::test_the_batch_scan_stamps_a_corpse_and_re_queues_it
  - claim: >-
      The attended scan still refuses to stamp anything. An operator runs it at
      will, mid-phase included, so a run in flight must survive being looked
      at — the existing behaviour, asserted here because the two scans now
      share one implementation and a shared default is exactly how one of them
      would quietly acquire the other's premise.
    witness: tests/test_cli.py::test_looking_at_the_queue_still_never_stamps_a_corpse
  - claim: >-
      The adapter this command hands the loop resolves what each candidate
      stacks on, so a child runs cut from its parent's branch head rather than
      from the pinned base. The loop cannot do this itself — building the cell
      input needs two helpers private to this module — and getting it wrong is
      silent: an unstacked child builds against code that is not there yet and
      fails gates it should have passed, which reads as the task's failure.
      Driven with a parent in a waiting state, asserting the child carries that
      parent's branch and sha.
    witness: tests/test_cli.py::test_the_adapter_stacks_a_child_on_its_parents_branch
  - claim: >-
      A second dependency is still not a stacking base. K=1 fixes the first
      entry as the sole candidate, and the adapter must not widen that just
      because it is new code doing an old job.
    witness: tests/test_cli.py::test_the_adapter_stacks_on_the_first_dependency_only
  - claim: >-
      One scan feeds both commands. It is resolved once, from the export at the
      pinned base rather than the working copy, and the attended command's
      printed output is unchanged — asserted against what it prints today, not
      merely that it still prints something.
    witness: tests/test_cli.py::test_both_commands_share_one_scan_and_the_printed_queue_is_unchanged
---

## Context

§4.2.1 gives the command and its exit codes exactly:

```
saffron batch --repo . --budget 50 --until 06:30
```

*"No `--repos`, because multi-repo is v2 (§9). No `--concurrency`, because a
flag for a knob with one position is the same defect in a CLI that item 18
found in a spec. `--repo` defaults to the working directory, matching
`saffron cell`. `--until` takes `HH:MM` and resolves to the next occurrence.
`--budget` defaults to 50."*

And on the codes: *"`0` for `DRAINED`, `BUDGET` and `UNTIL`, `2` for
`INFRASTRUCTURE` and for a preflight failure that takes the whole batch. Never
`1`. A batch that drains with three failed tasks did its job."*

`SA-0050` built `run_batch` and left it with no caller, deliberately. This is
the caller.

## Problem

- **`run_batch` has no caller.** The night exists as a function nobody invokes,
  which is item 18's pattern one last time and the reason this spec is not
  optional decoration on the one before it.
- **The scan is about to exist twice.** `_queue` resolves the mirror, exports
  `.saffron/` at the pinned base and calls `build_queue` through four private
  helpers. A batch needs the identical value. Copied, the two drift, and the
  night stops matching what the operator was shown before trusting it.
- **The two scans do not want the same premise, and the difference is one
  argument.** §4.2.1 requires the batch scan to stamp an in-flight row
  orphaned before filtering; `_queue`'s docstring says it must never do that,
  because an operator can run it mid-phase. Sharing the implementation without
  keeping that argument distinct converts a safety property into a bug.

## Out of scope

**Changing the loop.** `saffron/batch.py` is `forbidden`. If a witness here
seems to need `run_batch` to behave differently, that is a finding to report,
not a file to open.

**The morning queue's rendering.** `saffron/report/**` is `forbidden`. This
command runs the night; what the night looks like afterwards is §6's.

**Scheduling the night.** §4.4 names `launchd` specifically — *"not cron —
`launchd` handles wake and won't silently skip a sleeping Mac"* — and a plist
is a host artifact, not code. It ships by hand with the documentation.

**Multi-repo.** v2. The command takes one repo, and the flag §4.4 shows for
several is exactly the one §4.2.1 refuses to add yet.

## Notes for the agent

**The extraction is the point of ordering this last, and it is the risky
part.** By now `_queue` is the only copy of the scan and both callers exist, so
the right shape is visible rather than guessed. Pull out what both need — the
mirror, the pinned base, the export, the protected paths, the retirement
markers, the guarded `gh` — and let the two callers differ in the one argument
that must differ. Do not give that argument a default that makes the attended
behaviour the accident: name it at both call sites.

**The attended command's output is pinned by existing tests, and they are the
regression risk.** `tests/test_cli.py` is in `touches`, so they can be edited —
they must not be weakened. If the extraction changes a line of printed output,
the extraction is wrong; the printed queue is what an operator reads before
trusting a night.

**`check_readiness` returns a result, not a boolean, and the command's job is
to say which step failed.** It reports `ok`, and on failure the `step` and a
`detail`. A night that dies at readiness must print the step — an expired token
and a full disk are the same exit code and different mornings.

**The deadline is a time, not a duration, and the conversion is where this will
break.** Resolving `06:30` at 22:00 must give 06:30 tomorrow; resolving `23:00`
at 22:00 must give 23:00 today. Inject the current time rather than reading the
clock inside the resolver, or the test that matters — the one for a time
already past — is untestable without waiting for the afternoon.

**`run_batch`'s own signature is not yours to change.** It is `forbidden`, so
adapt at this end: whatever it takes, this command supplies.

**The adapter is the load-bearing half of this spec, not glue.** `SA-0050`
takes the cell runner as a required callable with no default, deliberately: the
loop cannot build a cell's input, because that needs this module's own ceilings
resolver and its stacking resolver, and a loop that built one itself would pass
no stacked-on parent at all. So the callable this command passes is what turns
a candidate into a cell, and it must call the stacking resolver exactly as
`_run_cell` already does — same K=1 rule, same `(sha, branch)` pair together or
neither, which is `SA-0026`'s whole point. Two witnesses above pin it, because
nothing downstream would notice: an unstacked child fails its own gates and
looks like a task that could not do its job.

**No new test may carry the `cell` marker.** `pyproject.toml` sets
`addopts = "-m 'not cell'"` and the `tests` gate passes the same argv to
`--collect-only`, so a cell-marked witness is never collected at head,
`criteria` reports `witness-not-collected`, and the attempt is spent on a test
that was correct. Nothing here needs a container: `run_batch` takes an injected
cell runner and `build_queue` an injected `gh`, and `tests/conftest.py` blocks
the cell runtime and `gh` at the subprocess boundary anyway.

**Do not add a flag this spec does not name.** Not `--dry-run`, not
`--concurrency`, not `--repos`, not a verbosity switch. Three of those are
refused by §4.2.1 by name and the fourth is the same argument. The third
witness asserts the absence of two of them, and it is a real criterion.
