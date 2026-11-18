---
id: SA-0409
title: A batch stopped before its first scan ends exits 143 and leaves no batch row
type: bug
priority: 2
estimated_lines: 82
estimate_measured: true
touches:
  - saffron/cli.py
  - tests/test_sigterm.py
  - docs/HOST-HARDENING.md
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
  - README.md
  - pyproject.toml
  - uv.lock
  - .saffron/**
  - .claude/**
  - ontology/**
  - tests/ontology/**
  - docs/adr/**
  - docs/appendices/**
  - docs/backlog/**
  - docs/evidence/**
  - harness/**
  - records/**
  - hooks/**
  - images/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/batch.py
  - saffron/ledger.py
  - saffron/preflight.py
  - saffron/task.py
  - tests/conftest.py
  - tests/test_cli.py
  - tests/test_batch.py
budget_usd: 31
max_attempts: 3
max_turns: 135
risk: standard
acceptance:
  - claim: >-
      A `saffron batch` sent SIGTERM at each of three points, inside its
      build cache reclaim, inside its readiness check and inside its first
      queue scan, exits 143. Each is driven for a plain batch and for a
      `--stack` one, six batches in all. Each leaves exactly one batch row.
      That row is closed `INFRASTRUCTURE` with an `ended_at`. It carries the
      batch's own `--budget` and an `until_ts` from its `--until`, and reads
      a spend of `0.0`, never NULL.
    witness: tests/test_sigterm.py::test_a_batch_stopped_before_its_first_scan_ends_leaves_one_closed_row
    wrong_versions:
      - The readiness check is guarded and the first queue scan is not, so a signal inside the scan leaves no row.
      - The reclaim and the scan are guarded and the readiness check is not, so a signal inside readiness leaves no row.
      - The build cache reclaim stays outside the guard, so a signal inside it leaves no row.
      - The guard catches `Exception`, which `KeyboardInterrupt` is not, so no stop point leaves a row.
      - The interrupt is caught and dropped, so the batch closes its row and exits 2, not 143.
      - The plain batch's loop receives the interrupt and the `--stack` loop receives the failed readiness alone, so a stack batch exits 2.
      - "`_batch` writes its own row with `ledger.create_batch` and re-raises without closing it, so `ended_at` and the status stay NULL."
      - "`_batch` writes and closes its own row as `INCOMPLETE`, a stop reason the closed set holds but that names a task left in flight."
      - "`_batch` writes and closes its own row with a budget of `0.0`, not the batch's `--budget`."
      - "`_batch` writes and closes its own row with the budget and no `until_ts`."
      - "`_batch` writes and closes its own row and then still enters the batch loop, which writes a second one."
  - claim: >-
      A batch sent SIGTERM while its first task holds a live child still
      exits 143 and still leaves exactly one row, closed `INFRASTRUCTURE`.
    witness: tests/test_sigterm.py::test_a_batch_sent_sigterm_exits_143_with_its_log_flushed
    preserves: true
  - claim: >-
      A `--stack` batch whose budget is below the printed total is still
      refused with no batch row, and one admitted at the total still has one.
    witness: tests/test_cli.py::test_a_stack_batch_below_its_total_is_refused_before_any_batch_row
    preserves: true
  - claim: >-
      A batch whose readiness check fails still exits 2, leaves a row closed
      `INFRASTRUCTURE`, and prints the failed step.
    witness: tests/test_cli.py::test_an_unready_night_still_leaves_a_row_saying_it_was_attempted
    preserves: true
  - claim: >-
      A batch whose first queue scan raises still exits 2 and prints the
      scan's own text, never "readiness failed".
    witness: tests/test_cli.py::test_a_queue_that_cannot_be_resolved_says_so_on_the_batch_line
    preserves: true
---

## Context

Backlog item **b-d0fed8**, tier 2, cites `DESIGN.md` §4.2.1. It was found
by the Spec seat on `SA-0258` (#812). Its related items are **95**, which
closed the same gap for a scan that raises, and **b-5df2a7**, which made
SIGTERM unwind a batch. Every line below was read at `1d574d39`.

**How SIGTERM reaches a batch.** `main` runs `_batch` inside
`_guarding_sigterm` (`saffron/cli.py:410-413`). Its handler raises
`KeyboardInterrupt`, and a SIGTERM-caused one returns 143
(`saffron/cli.py:649-672`).

**Who writes the batch row.** `_batch` never calls `create_batch` or
`close_batch` itself (`saffron/cli.py:2408-2411`). `run_batch` creates the
row first (`saffron/batch.py:158`). It calls `readiness_check` inside its
`try` (`saffron/batch.py:178`, `saffron/batch.py:240`). Its `finally` closes
the row `INFRASTRUCTURE` when nothing else did, Ctrl-C included
(`saffron/batch.py:188-196`). `run_stack_batch` does the same
(`saffron/batch.py:988`, `saffron/batch.py:1006`, `saffron/batch.py:1087-1089`).
`close_batch` stores `batch_spend` as the spend (`saffron/ledger.py:1342-1349`).
`batch_spend` coalesces a batch with no attempts to `0.0`
(`saffron/ledger.py:1436-1438`).

**The window with no row.** `_batch` reclaims the build cache at
`saffron/cli.py:2436`. Its timeout is 600 seconds
(`saffron/cell/runtime.py:729`). It then runs `preflight.check_readiness`
(`saffron/cli.py:2455-2462`) and the first queue scan, inside a `try`
(`saffron/cli.py:2517-2529`). Only then does it call `run_batch` or
`run_stack_batch` (`saffron/cli.py:2682`, `saffron/cli.py:2705`). A
`KeyboardInterrupt` in any of the three passes no `except` that catches it.
`_reclaim_build_cache` catches `CellRuntimeError` alone
(`saffron/cli.py:2381-2385`). The scan's `except` catches `Exception`
(`saffron/cli.py:2526-2529`). So the signal unwinds to 143 before any row
exists.

**What item 95 built.** A scan that raises is held in `resolution_error`
(`saffron/cli.py:2529`). `_readiness_or_raise` re-raises it inside the
batch loop (`saffron/cli.py:2671-2676`), so the loop's own row closes
`INFRASTRUCTURE`. The `except` after the loop prints the scan's text when the
raise is that same object (`saffron/cli.py:2716-2722`).

## Problem

A batch sent SIGTERM inside its build cache reclaim, its readiness check or
its first queue scan must leave a row closed `INFRASTRUCTURE`. It exits 143
and spends nothing.

1. **Carry the interrupt into the loop.** A `KeyboardInterrupt` can rise in
   the build cache reclaim, the readiness check or the first queue scan. It
   reaches the batch loop and is raised there. The loop's own `create_batch` writes
   the row and its own `finally` closes it. The interrupt then leaves `_batch`
   unchanged, so `_guarding_sigterm` returns 143.
2. **Both loops.** A plain batch and a `--stack` one each get the row.
3. **Nothing else moves.** The early path skips the rest of the scan's
   setup. The stack refusal below the printed total
   (`saffron/cli.py:2570-2576`) is never reached on it, so it still writes no
   row. A readiness failure and a scan that raises keep their exit 2 and their
   lines.
4. **The doc.** `docs/HOST-HARDENING.md:209-210` says the row closes "once it
   has one". Add the sentence the notes give.

## Out of scope

- **A stop between those calls, or after the scan returns.** The
  statements between readiness and the scan bind defaults and the pinned
  base (`saffron/cli.py:2464-2516`). After the scan, `_batch` prints the
  plan, rewrites the queue page and builds the stack's closures
  (`saffron/cli.py:2530-2669`). A signal in either stretch still leaves no
  row. Guarding the second re-indents some 140 lines. No witness drives
  either, and the doc sentence names the three calls this spec guards.
- **A stop before the reclaim.** `runtime.unattended_refusal` reads the
  selected dialect and returns (`saffron/cli.py:2429-2432`). Its refusal
  writes no row, for backlog item 108 (`saffron/cli.py:2427-2428`).
- **A plain `Exception` from readiness.** `check_readiness` raising today
  reaches `main`'s catch-all (`saffron/cli.py:456-462`) with no row. That is
  not this item, and the guard catches `KeyboardInterrupt` alone.
- **A real Ctrl-C.** It raises the same `KeyboardInterrupt`, so it gets the
  same row and re-raises out of `main` as before. No witness drives it.
- **`DESIGN.md`.** §4.2.1's exit-code paragraph (`DESIGN.md:525`) says a
  batch row still open closes `INFRASTRUCTURE`. It is protected, and its
  sentence is edited by hand in this spec's own pull request.

## Notes for the agent

**Edit or new.** This edits `_batch`, but the guard's spelling is yours. So
criterion 1 declares a witness and no mutant, and `witness` will report
`skip` for it. Criteria 2 to 5 name tests that exist at your base and must
stay green.

**The shape that keeps `run_batch`'s callers unchanged.** Hold the
interrupt in a local beside `resolution_error`, and raise it first in
`_readiness_or_raise`. Move the build cache reclaim down into the same
guard, right above the readiness call. Its comment stays true there. When
the guard catches, the readiness check never returned, so bind `readiness`
to a failed `preflight.Readiness`. Nothing prints it, since the loop
re-raises before `_batch` reads it. Leave `saffron/batch.py` alone.

**The witness.** Add it to `tests/test_sigterm.py`, in process, as the
cell witnesses there are. Set `CLAUDE_CODE_OAUTH_TOKEN` with `monkeypatch`.
One helper sends
SIGTERM to the test's own process with `os.kill`, then sleeps, then fails
if the sleep returns. Loop over the three points and the two modes. Each pass
installs a passing `check_readiness` and a no-op
`runtime.reclaim_build_cache` with `monkeypatch.setattr`. It sets
`cli._resolve_queue` to the helper. Then it puts the helper in place of the
one point under test. Give each batch its own `--home`
under `tmp_path`, `--repo tmp_path`, `--budget 37` and `--until 23:59`.
Add `--stack --partial` for the stack mode. Assert `cli.main(argv) == 143`.
Then read `status`, `ended_at`, `spent_usd_est`, `budget_usd` and `until_ts`
from every row of `batches` under that home. Assert one row and the five
values. Put the point and the mode in each assertion's message.
Import `preflight` from `saffron` at module scope, as the batch script
string in that file already does. It exists at base.

**Witness red at base.** Measured at `1d574d39`: each of the six batches
already exits 143 and leaves no row. So it fails on the row count.

**The doc sentence.** In `docs/HOST-HARDENING.md:209-210`, after "closes
`INFRASTRUCTURE`.", add this.

```text
A stop inside the build cache reclaim,
the readiness check or the first queue scan has one too.
```

**Measured on a prototype, 2026-11-17.** The change above and the witness
were built at `1d574d39`. The witness failed with `saffron/cli.py`
reverted. Each wrong version under criterion 1 was applied as one edit to
`saffron/cli.py`, and each failed the witness on an assertion. The five
witnesses passed together. `ruff check`, `ruff format --check` and `ty
check` passed on both Python files. `python3 hooks/prose_limit.py --file`
read 0 new hits on each. A comment placed right under the 7-line readiness
comment made one 9-line block, which `prose` counted as a hit. By
`size_gate` the diff counted 325 changed tokens, 212 of them in the test.
With the policy's `tests/**` test paths declared, it counts 113.

**The `prose` gate** reads every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words. Keep each docstring within ten lines.

**Size.** The `bug` ceiling is 1300 changed tokens. `saffron/cli.py` is in
no `elevate_on` entry, so `size` reports and does not block.
