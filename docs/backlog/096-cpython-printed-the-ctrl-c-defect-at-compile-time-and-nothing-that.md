---
id: 96
title: CPython printed the Ctrl-C defect at compile time, and nothing that runs here can hear it
status: open
tier: 3
specs: [SA-0057]
prs: [136]
commits: [ddffdde]
cites: [§5.4]
related: []
---

## Problem

**Tier 3 — the defect is fixed; this is the guard against its return.** Filed from
`.saffron/rejections.md`'s first reading, where it was the one bucket-1 destination
named nowhere else.

`ddffdde` (a review-fix on `SA-0057`, PR #136): `restore_mutant`'s failure branch
returned from inside a `finally`, which discards whatever was in flight — a
`KeyboardInterrupt` from `run_tests` came back as an ordinary `GateResult`, so an
operator's Ctrl-C during a mutated test run went nowhere, in a core gate. The
commit recorded that CPython had already named it: the only file under `saffron/`
emitting `SyntaxWarning: 'return' in a 'finally' block`.

**Measured 2026-09-10**, against `saffron/gates/core/witness.py` at `ddffdde^`:

| Checker | Result |
|---|---|
| ruff 0.16.3 — `B012`, `SIM107`, `PLE0116`, `RUF072`, with `--preview` | `All checks passed!` |
| CPython 3.14.7, `-W error::SyntaxWarning`, `compile()` | `SyntaxError: 'return' in a 'finally' block`, line 110 |
| CPython 3.13.15, same | compiles clean |
| CPython 3.12.14, same | compiles clean |

The current tree (`saffron/`, `images/`, `harness/`) passes the 3.14 check, so
turning it on needs no fix-up first.

**And the cell runs 3.12.** `saffron/cell:saffron` reports `Python 3.12.14`, its
`/opt/venv/bin/python` resolving to `/usr/local/bin/python3.12`:
`images/cell-base.python.Dockerfile` is `FROM python:3.12-slim-bookworm`, and
`pyproject.toml` says `requires-python = ">=3.12"` with no `.python-version`. The
warning is PEP 765's, new in 3.14. On the host, `uv run python` is uv's managed
CPython 3.14.7 — nothing pins it lower — while bare `python3` is pyenv's 3.12.12.
So `make check` runs on 3.14 and the cell on 3.12: the suite runs on two
interpreters, and nothing records which.

**So the obvious fix is the trap.** A compile gate declared in
`.saffron/policy.yaml` runs in the cell, compiles this defect clean, and reports
`pass` — green on the one defect it exists for, which is Appendix H's headline
finding in a new shape. A prek hook inherits the same hole wherever its
interpreter is not 3.14.

## Done looks like

one of these, chosen, with the choice written down:

- **The gate asserts its interpreter**, reporting `error` below 3.14 — not `pass`,
  and not `skip`, because a check that cannot run has said nothing (§5.4). On
  today's image that errors every task, so it lands with the next option or not
  at all.
- **The cell moves to 3.14.** One `FROM` line and a `requires-python` bump, and the
  gate becomes an ordinary one. Costs rebuilding both images, plus whatever the
  suite does differently on 3.14 — unmeasured here.
- **An ast-grep rule in `structure`**: a `return` inside a `finally`, or a `break`
  or `continue` that would leave one — PEP 765's own definition. Interpreter-free,
  and `structure` already ships each rule with the mutant that proves it fires.
  Costs a rule this repo writes and maintains instead of one CPython does.

Whichever lands is run against the pre-fix `witness.py` before it is trusted: a
new guard proves itself on the unfixed code, and here the unfixed code is on
record.
