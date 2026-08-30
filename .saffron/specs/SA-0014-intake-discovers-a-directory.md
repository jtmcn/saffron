---
id: SA-0014
title: acceptance criteria truncate at the first line, and no discovery reads a directory of specs
type: feature
priority: 1
depends_on: []
touches:
  - saffron/intake.py
  - tests/test_intake.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - docs/**
  - saffron/cell/**
  - saffron/phases/**
  - saffron/report/**
budget_usd: 6
max_attempts: 4
max_turns: 60
risk: elevated
---

## Context
`DESIGN.md` §4.2.1 decided the first night's scheduler; `SA-0009` was its
read-only half and split again after it died `EXHAUSTED` at 990 changed lines
against a 600-line feature ceiling (`docs/BACKLOG.md` item 25). This spec is
the first of that resplit's four pieces — the parser fix and the directory
scan the other three build on. §10 calls `saffron/intake.py` *"spec
discovery, parse, validate"*; it does the last two.

`SA-0015` (ledger reads and the re-queue filter), `SA-0016` (the refusals)
and `SA-0017` (`saffron queue`'s CLI wiring) are the rest, each depending on
the one before it.

## Problem
- **`_CRITERION` is line-anchored under `re.MULTILINE`**, so a wrapped
  acceptance criterion keeps only its first line. Measured on `SA-0016`, the
  refusal gate's own spec: its third criterion parses as *"The two refusals
  needing GitHub take an injected runner in the"*, dropping
  `saffron/phases/package.py` and `tests/test_scheduler.py` from the two
  continuation lines that name them. A refusal gate built on this value is
  blind to the case it exists for, starting with its own spec (`SA-0016` is
  that gate).
- **Nothing reads a directory of specs.** `saffron/intake.py` parses one path
  at a time; the scheduler needs every spec in `.saffron/specs/` at once,
  with one malformed file unable to take down the scan.

## Acceptance criteria
- [ ] `saffron/intake.py` joins a wrapped acceptance criterion into one
      string, and a test asserts a multi-line criterion in the `SA-0005`
      shape yields the path token from its continuation line
- [ ] `saffron/intake.py` discovers specs in a directory, returning parsed
      specs and, separately, the paths that failed with their reason — a
      malformed spec must not raise past discovery
- [ ] Discovery orders specs by filename, so a tie in priority resolves the
      same way on every machine

## Out of scope
Nothing here reads the ledger, builds a queue, or touches the CLI —
`saffron/scheduler.py`, `saffron/ledger.py` and `saffron/cli.py` are
untouched and stay that way until `SA-0015`. Discovery takes a directory,
never a repo; resolving `base_sha` and exporting `.saffron/specs/` from it is
the caller's job (`SA-0017`), not this one's, which is what keeps every test
here offline without a fixture repo.

## Notes for the agent
**This is the corpse repair — `SA-0005` cost $5.34 and died at turn 61 for
want of it.** Built on today's `spec.acceptance_criteria`, a refusal gate
passes `SA-0016` clean, because the truncation drops the two continuation
lines its path tokens sit on. Fix the regex first; a test whose fixture is a
single-line criterion proves nothing about the bug this spec exists to fix.

Joining is not the whole job: the section ends only at `##`, so a `###`
subsection belongs to no criterion. A join that runs to the next `- [ ]`
swallows it — measured on `SA-0001`, whose last criterion then runs to 758
characters, 640 of them a table.

Commit after each coherent step. Uncommitted work dies with the cell.
