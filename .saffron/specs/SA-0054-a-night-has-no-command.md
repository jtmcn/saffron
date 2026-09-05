---
id: SA-0054
title: the loop and the scan both exist, and nothing an operator can type reaches either
type: feature
priority: 1
depends_on:
  - SA-0051
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
budget_usd: 12
max_attempts: 3
max_turns: 90
risk: standard
acceptance:
  - claim: >-
      The command runs a night against one repo, resolving its queue through
      the function the previous spec extracted and handing it to the loop. Its
      two defaults are the ones §4.2.1 fixes: the repo defaults to the working
      directory, matching the attended command beside it, and the budget
      defaults to 50, sized against the queue rather than against capacity.
    witness: tests/test_cli.py::test_saffron_batch_runs_a_night_with_the_defaults_4_2_1_fixes
  - claim: >-
      Its scan asserts the premise a batch is entitled to and the attended one
      is not: one batch runs at a time, so an in-flight row is a corpse and is
      stamped before filtering. The argument is passed here; the behaviour was
      proven in the extraction.
    witness: tests/test_cli.py::test_the_batch_scan_asks_for_the_stamping_the_attended_one_refuses
  - claim: >-
      The deadline is given as a time of day and resolves to its next
      occurrence, so a time earlier in the day than now means tomorrow rather
      than a window that closed hours ago. Driven with an injected now and a
      time already past, which is the case an operator hits every night they
      ask for the morning.
    witness: tests/test_cli.py::test_a_deadline_earlier_than_now_resolves_to_tomorrow
  - claim: >-
      Neither a concurrency flag nor a multi-repo flag exists. §4.2.1 refuses
      both by name — a flag for a knob with one position is the same defect in
      a command that item 18 found in a dataclass — so their absence is a
      witness rather than an omission, and adding one is a decision someone
      makes on purpose.
    witness: tests/test_cli.py::test_the_batch_command_offers_no_concurrency_or_multi_repo_flag
  - claim: >-
      Draining, running out of budget and reaching the deadline all exit 0. A
      batch that drains with three failed tasks did its job; the individual
      outcomes are the morning queue's business.
    witness: tests/test_cli.py::test_the_three_ordinary_stop_reasons_all_exit_zero
  - claim: >-
      The breaker firing exits 2, and so does a readiness failure that takes
      the whole night. Both say the infrastructure failed, which is what an
      unattended caller reads to decide whether tomorrow is worth attempting.
    witness: tests/test_cli.py::test_infrastructure_and_a_failed_readiness_both_exit_two
  - claim: >-
      Exit 1 is never returned, whatever stopped the night. §4.2.1 reserves it
      rather than reusing it: a batch is not a task, and letting 1 mean
      something here would merge two vocabularies that answer different
      questions. The witness walks all four stop reasons.
    witness: tests/test_cli.py::test_a_batch_never_exits_one_whatever_stopped_it
  - claim: >-
      A real readiness check is passed, bound to this run's own paths and
      token. The loop's default is to proceed, which is the right default for
      a loop that cannot know a repo's paths and the wrong one for a night: an
      expired token at 22:00 buys a night of clean-looking nothing, and the
      probe that catches it is only reached if a caller supplies it.
    witness: tests/test_cli.py::test_the_night_is_given_a_real_readiness_check_not_the_loops_default
  - claim: >-
      A night that dies at readiness says which step failed. An expired token
      and a full disk are the same exit code and different mornings, and the
      result carries the step precisely so a caller need not guess.
    witness: tests/test_cli.py::test_a_readiness_failure_names_the_step_that_failed
  - claim: >-
      The adapter this command hands the loop resolves what each candidate
      stacks on, so a child runs cut from its parent's branch head rather than
      the pinned base. The loop cannot do this itself — building a cell's
      input needs two helpers private to this module — and getting it wrong is
      silent: an unstacked child builds against code that is not there yet and
      fails gates it should have passed, which reads as the task's own
      failure.
    witness: tests/test_cli.py::test_the_adapter_stacks_a_child_on_its_parents_branch
  - claim: >-
      A second dependency is still not a stacking base. K=1 fixes the first
      entry as the sole candidate, and the adapter must not widen that just
      because it is new code doing an old job.
    witness: tests/test_cli.py::test_the_adapter_stacks_on_the_first_dependency_only
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

`SA-0050` built the loop and left it with no caller. `SA-0051` extracted the
scan and gave it a second caller that does not exist yet. This is that caller,
and it is the last spec in the plan: when it merges, backlog item 58 closes and
§9's v1 criterion — an unattended night — is reachable for the first time.

## Problem

- **Nothing an operator can type reaches either mechanism.** The loop and the
  scan are functions nobody invokes, which is item 18's pattern twice over.
- **The loop's readiness default is to proceed.** That is defensible where it
  sits — a loop cannot know a repo's paths or hold its token — and it is not
  defensible for a night. Only a caller can supply the probe that catches the
  landmine Appendix J measured.
- **The loop cannot build a cell.** It takes the runner as a required callable
  precisely because assembling one needs this module's ceilings and stacking
  resolvers. Until something supplies that adapter, the loop has nothing to
  run.

## Out of scope

**Changing the loop or the scan.** `saffron/batch.py` is `forbidden` and the
extraction is `SA-0051`'s. If a witness here seems to need either to behave
differently, that is a finding to report, not a file to open.

**The morning queue's rendering.** `saffron/report/**` is `forbidden`.

**Scheduling the night.** §4.4 names `launchd` — *"not cron — `launchd`
handles wake and won't silently skip a sleeping Mac"* — and a plist is a host
artifact, not code. It ships by hand with the documentation.

**Multi-repo.** v2. The command takes one repo, and the flag §4.4 shows for
several is exactly the one §4.2.1 refuses to add yet.

## Notes for the agent

**The adapter is the load-bearing half of this spec, not glue.** `SA-0050`
takes its runner as a required callable with no default, deliberately: the loop
cannot build a cell's input, because that needs this module's ceilings resolver
and its stacking resolver. So the callable this command passes is what turns a
candidate into a cell, and it must resolve stacking exactly as the attended
path already does — same K=1 rule, and the sha and the branch together or
neither, which is `SA-0026`'s whole point. Two witnesses pin it because nothing
downstream would notice: an unstacked child fails its own gates and looks like
a task that could not do its job.

**Read `_run_cell` for the adapter's shape, and reuse rather than reimplement.**
It already turns a spec plus the run's paths into a cell's input. The
difference is where the spec comes from — a candidate the scan resolved rather
than a path an operator typed — and the ceilings, which a batch takes from the
spec because no flag overrode them.

**The deadline is a time, not a duration, and the conversion is where this
will break.** Resolving `06:30` at 22:00 gives 06:30 tomorrow; resolving
`23:00` at 22:00 gives 23:00 today. Inject the current time rather than reading
the clock inside the resolver, or the test that matters — the one for a time
already past — is untestable without waiting for the afternoon.

**Pass a real readiness check, and do not reach for the loop's default.**
`preflight.check_readiness` takes the repo, the mirror path, a scratch
directory, the home directory and the token; bind those to this run and hand
the loop a callable with no arguments. `saffron/preflight.py` is `forbidden`,
which forbids editing it, not calling it.

**Do not add a flag this spec does not name.** Not a dry run, not a
concurrency knob, not a repos list, not a verbosity switch. Three of those
§4.2.1 refuses by name and the fourth is the same argument. The fourth witness
asserts the absence of two of them, and it is a real criterion.

**No new test may carry the `cell` marker.** `pyproject.toml` sets
`addopts = "-m 'not cell'"` and the `tests` gate passes the same argv to
`--collect-only`, so a cell-marked witness is never collected at head,
`criteria` reports `witness-not-collected`, and the attempt is spent on a test
that was correct. The loop takes an injected runner, the scan an injected `gh`,
and `tests/conftest.py` blocks the cell runtime and `gh` at the subprocess
boundary — nothing here needs a container.

**This spec is the second half of one the checkpoint refused.** The first
`SA-0051` carried the extraction, this command, its exit codes and the adapter,
and its plan estimated 650 changed lines against a 600-line ceiling. Keep the
halves apart: the scan is resolved by calling what `SA-0051` extracted, never
by re-deriving it here.
