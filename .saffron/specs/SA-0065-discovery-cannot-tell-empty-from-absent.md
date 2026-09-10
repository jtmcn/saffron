---
id: SA-0065
title: discovery cannot tell an empty night from a directory that was never there
type: bug
priority: 1
depends_on: []
touches:
  - saffron/intake.py
  - tests/test_intake.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - ontology/**
  - docs/**
  - images/**
  - harness/**
  - saffron/gates/**
  - saffron/cell/**
  - saffron/phases/**
  - saffron/agents/**
  - saffron/scheduler.py
  - saffron/cli.py
  - saffron/batch.py
  - saffron/task.py
  - saffron/replay.py
budget_usd: 5
max_attempts: 3
max_turns: 40
risk: standard
acceptance:
  - claim: >-
      A scan directory that does not exist is refused rather than answered.
      `Path.glob` yields nothing for a missing path exactly as it does for an
      empty one, so an export that produced nothing — a wrong base commit, a
      repo that never had the directory, a path assembled with the wrong join —
      reached the scheduler as a quiet empty queue. A scan that never saw a
      directory must not read like a night with no work in it.
    witness: tests/test_intake.py::test_discovery_refuses_a_directory_that_is_not_there
  - claim: >-
      A path that exists and is not a directory is refused on the same footing.
      It is the same silent nothing arriving by a different route, and a caller
      handed a file where it meant a directory has made the same class of
      mistake as one handed nothing at all.
    witness: tests/test_intake.py::test_discovery_refuses_a_path_that_is_not_a_directory
  - claim: >-
      An existing but empty directory still answers, and answers nothing. That
      is a true statement about a repo with no specs, and it is the one case
      here that must keep reading as an ordinary night rather than a fault.
    witness: tests/test_intake.py::test_discover_specs_on_an_empty_directory_returns_nothing
    preserves: true
---

## Context

`docs/BACKLOG.md` item **26**, measured at `30bd85c`. `discover_specs` reaches
the filesystem through `directory.glob("*.md")`, and `Path.glob` is silent in
three different situations that mean three different things:

```
discover_specs(Path("/nope/nothing"))     -> ([], [])
discover_specs(Path("saffron/intake.py")) -> ([], [])
discover_specs(<an empty directory>)      -> ([], [])
```

Only the third is a night with no work in it. The other two are faults, and the
repo enforces this distinction everywhere else it appears: `error` is not
`fail`, and a gate that never ran must not read like one that ran and passed.

This is also the first spec a `saffron batch` has ever been asked to run, which
is why it is this one. The failure mode item 26 describes — *the first
unattended night ends having done nothing with no record saying why* — is the
failure mode the night running this spec exists to rule out.

## Problem

The distinction is missing at the seam rather than here. `SA-0017` resolves a
base commit and exports the spec directory out of a repo; `SA-0015` builds the
queue from whatever discovery returns. An export that silently produced nothing
arrives at the scheduler indistinguishable from a repo that genuinely has no
work, and the night ends `DRAINED` with nothing in the log that separates the
two. The one human-readable record of an unattended night is then a record of
the wrong thing.

The existing second acceptance criterion of `SA-0014` asks only that a
*malformed* spec not raise past discovery, so this is not a violation of what
the scan was asked for. It is a distinction nobody asked for and the queue
depends on.

## Out of scope

**The caller, and the exit code.** Item 26 argues that a missing directory is an
infrastructure fault worth exit `2`, and that argument is why refusing is right
— but the change here is to `discover_specs` alone. `saffron/scheduler.py` and
`saffron/cli.py` are both `forbidden`. Nothing regresses by leaving them:
`scheduler.py`'s `done/` scan already guards its own call with `is_dir()` before
reaching discovery, and `cli.py` carries a deliberate catch-all that maps an
unexpected exception to exit `2` with a message rather than a traceback. If the
exit code turns out wrong once this raises, that is a finding to file, not a
file to edit.

**Widening what discovery validates.** A directory that exists, is a directory,
and contains unreadable files or wrong permissions is not in scope. The three
cases above are the ones measured; inventing a fourth is how a small change
stops being one.

**The retired-directory scan.** `scheduler.py`'s `done/` read passes a path it
has already checked. Do not remove that check to lean on this one — a caller
that states its own precondition is not made wrong by a callee that also does.

## Notes for the agent

**This spec creates new code, so its criteria carry witnesses and no mutants.**
A mutant names exact text and applies only where it matches once, so for a guard
that does not exist yet the operator cannot know the spelling you will produce —
and dictating one would put the literal in prose you are reading, which is the
theater the `witness` gate exists to refuse. Criterion 3's witness is a test
that **already exists**; it is there to be preserved, not written.

**The third criterion is the load-bearing one.** Refusing a missing directory is
easy to get right in a way that also refuses an empty one, and an empty
directory is a legitimate answer this repo needs to keep. Read the existing test
before you change anything and make sure it still says what it says.

**On the error type.** `SpecError` already exists in this module and already
means "intake refused something". Use it rather than introducing a second
vocabulary for the same idea — `CONTEXT.md` is `forbidden` here precisely
because a task implementing against a term must not be the task that invents
one.
