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
  acceptance criterion keeps only its first line. Measured on `SA-0005`: none
  of its seven parsed criteria contains a path token, because `saffron/cli.py`
  and `saffron/phases/package.py` — the paths that made it unsatisfiable —
  sit on continuation lines. A refusal gate built on this value is blind to
  the case it exists for (`SA-0016` is that gate).
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
**This is the corpse repair, and it is the whole reason `SA-0005` cost $5.34
and died at turn 61**: built on today's `spec.acceptance_criteria`, a refusal
gate passes `SA-0005` clean, because the truncation drops the lines the paths
are on. Fix the regex first; a test whose fixture is a single-line criterion
proves nothing about the bug this spec exists to fix.

Commit after each coherent step. Uncommitted work dies with the cell.
