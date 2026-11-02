---
id: SA-0329
title: "A rebuilt outcome and `saffron regate` drop the `revert` exemption, so a sound diff comes back red"
type: bug
priority: 1
estimated_lines: 256
estimate_measured: true
touches:
  - saffron/phases/package.py
  - saffron/task.py
  - saffron/regate.py
  - tests/test_package.py
  - tests/test_task.py
  - tests/test_regate.py
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
  - docs/**
  - images/**
  - harness/**
  - records/**
  - hooks/**
  - saffron/cli.py
  - saffron/ledger.py
  - saffron/scheduler.py
  - saffron/gates/**
  - saffron/cell/**
  - saffron/record/**
  - tests/test_cli.py
  - tests/test_session.py
  - tests/test_revert.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 38
max_attempts: 3
max_turns: 210
risk: standard
acceptance:
  - claim: >-
      `package_phase.read_revert_exempt(task_dir)` answers `[]` for a task
      directory with no `revert-exempt.json`, and for no directory at all.
      It answers `[]` for a file older than the directory's `baseline.json`,
      damaged or not. It returns a current file's list unchanged, and the
      witness drives one that is unsorted and repeats a name. A current
      file is one as new as `baseline.json`, or one in a directory with no
      `baseline.json`. The witness drives a current `[]` too. It raises
      `package_phase.RevertExemptUnreadable`, naming the file's path, for each
      of these current files. They are invalid JSON, zero bytes, bytes that are
      not UTF-8, the JSON values `{}`, `"t.py::a"`, `null` and `3`, the lists
      `["t.py::a", 3]`, `[3, "t.py::a"]` and `[null]`, and a directory at that
      path. The witness asserts the path with `str(path) in str(exc)` on every
      raising member. That exception subclasses `package_phase.PackageError`.
      A host failure on a current file is not damage, so the reader leaves it
      uncaught. The witness drives an open raising `PermissionError`, an open
      raising a plain `OSError(errno.EIO, ...)`, and a handle whose read raises
      a plain `OSError(errno.EIO, ...)`. The reader raises that same object for
      each.
    witness: tests/test_package.py::test_the_exemption_reader_answers_for_each_state_of_the_task_directory
    wrong_versions:
      - A path that is not a regular file reads as no file, so a directory answers `[]`.
      - A failed parse answers `[]`, so invalid JSON reads as no exemption.
      - Only the JSON parse error is caught, so bytes that are not UTF-8 raise a bare decode error.
      - Only a parse error is caught, so a directory raises a bare `IsADirectoryError`.
      - A falsy value answers `[]` before any type check, so `{}` and `null` read as no exemption.
      - A value is passed through `list()` with no type check, so `"t.py::a"` becomes a list of characters.
      - The list is checked and its members are not, so `["t.py::a", 3]` returns.
      - Only the first member is checked, so `["t.py::a", 3]` returns.
      - Only the last member is checked, so `[3, "t.py::a"]` returns.
      - One string member is enough to pass, so `["t.py::a", 3]` returns.
      - The reader sorts what it returns, so the list differs from the one the file holds.
      - Blank text answers `[]`, so a zero-byte file reads as no exemption.
      - A file older than `baseline.json` is read, so another cell's list exempts this cell's tests.
      - A file older than `baseline.json` is parsed first, so another cell's damaged file raises.
      - A file as new as `baseline.json` reads as older, so a same-instant write loses its list.
      - A directory with no `baseline.json` answers `[]`, so a current file loses its list.
      - A current `[]` raises, as if an empty list were damage.
      - A missing task directory raises rather than answering `[]`.
      - The message for a file it cannot parse, or for a directory at that path, names the reason and not the file's path.
      - The message for a value that is not a list of strings names the reason and not the file's path.
      - Both messages name the file's base name, not its path.
      - Every `OSError` but a missing file raises the reader's exception, so a host failure exits 1.
      - "`PermissionError` joins the caught classes, so a denied open exits 1."
      - Only `PermissionError` is left to raise, so `EIO` from the open exits 1.
      - A failed open raises bare and a failed read raises the reader's exception, so `EIO` from the read exits 1.
      - A failed read raises bare and a failed open raises the reader's exception, so a denied open exits 1.
      - Every `OSError` answers `[]`, so a host failure reads as no exemption.
      - "`PermissionError` answers `[]`, so a denied open reads as no exemption."
      - A host failure is wrapped in a `PackageError`, so the raise is not the error the read raised.
      - The exception subclasses `ValueError`, so an uncaught one no longer reads as `PackageError`.
  - claim: >-
      `ready_task` sets `revert_exempt` on the outcome it rebuilds from
      `package_phase.read_revert_exempt(task_dir)`, called through that
      module attribute. The witness drives a directory with no file, with a
      current file and with a file older than `baseline.json`. It then
      replaces the reader and reads that replacement's answer on the outcome.
    witness: tests/test_task.py::test_a_rebuilt_outcome_carries_the_exemption_its_task_directory_holds
    mutant:
      file: saffron/task.py
      find: return ReadyTask(outcome=outcome, spec=spec, parent_branch=parent_branch)
      replace: 'outcome.revert_exempt = []; return ReadyTask(outcome=outcome, spec=spec, parent_branch=parent_branch)'
    wrong_versions:
      - The rebuilt outcome leaves `revert_exempt` at its empty default.
      - "`ready_task` parses the file itself behind its local freshness check, so a second copy of the reader exists."
      - The reader is handed `out_dir` rather than the task directory.
      - "`ready_task` imports the reader by name, so a replaced module attribute never reaches it."
  - claim: >-
      `ready_task` returns a `Refused` when the reader raises
      `RevertExemptUnreadable`. Its reason carries the exception's text, and so
      names the file's path. It neither raises nor rebuilds an outcome. The
      witness drives a current file holding invalid JSON, `{}` and
      `["t.py::a", 3]`, and a directory at that path. It also drives a
      damaged current file on a task whose `tree_base` differs from its
      `base_sha` and that no task pushed. There the mirror path stays absent.
      A replaced reader then raises the exception with its own text, and
      that text reaches the reason. A host failure is no refusal. A replaced
      reader raises `PermissionError`, then a plain `OSError(errno.EIO, ...)`,
      and `ready_task` raises that same object for each and returns no
      `Refused`.
    witness: tests/test_task.py::test_a_rebuilt_outcome_refuses_an_exemption_it_cannot_read
    wrong_versions:
      - The reader's exception escapes `ready_task`, so `saffron package` exits 2 rather than refusing.
      - The raise is caught and the outcome carries `[]`.
      - The reader runs only when the local freshness check passes, so a directory at that path answers no exemption.
      - The reason is a fixed sentence that names no file.
      - The reason is a fixed sentence that names the file's path and drops the exception's text.
      - The reader runs just above the rebuilt `CellOutcome`, after the fallback, so a refused task still writes the mirror.
      - "`ready_task` catches `OSError` beside the reader's exception, so a host failure is a `Refused` and exits 1."
      - "`ready_task` answers an `OSError` with `[]`, so a host failure reads as no exemption."
      - "`ready_task` catches `PermissionError` beside the reader's exception, so a denied open exits 1."
      - "`ready_task` lets `PermissionError` through and refuses every other `OSError`, so `EIO` exits 1."
  - claim: >-
      `run_regate` hands `package_phase.reverify` an `exempt` from
      `package_phase.read_revert_exempt(out_dir / <the task's spec id>)`,
      called through that module attribute. The witness drives a directory
      with no file, with a file and no `baseline.json`, and with a file older
      than `baseline.json`. It then replaces the reader and reads that
      replacement's answer on the call.
    witness: tests/test_regate.py::test_regate_passes_reverify_the_exemption_its_task_directory_holds
    mutant:
      file: saffron/regate.py
      find: comparison = package_phase.reverify(
      replace: 'comparison = (lambda **kw: package_phase.reverify(**{**kw, "exempt": ()}))('
    wrong_versions:
      - "`run_regate` passes no `exempt`, so a test PACKAGE exempted comes back red."
      - "`run_regate` parses the file itself, so a second copy of the reader exists."
      - The reader is handed the export directory under `regate/<task id>` rather than the task directory.
      - The reader is handed a directory named for the task id rather than the spec id.
      - An empty answer passes `exempt=None` rather than the empty list.
  - claim: >-
      `run_regate` prints a `regate:` line and returns 1 when the reader
      raises `RevertExemptUnreadable`. The line carries the exception's text,
      and so names the file's path. The witness drives a current file holding invalid JSON,
      `{}` and `["t.py::a", 3]`, and a directory at that path. A replaced
      reader then raises the exception with its own text, and that text
      reaches the line. A host failure is no decline. A replaced reader raises
      `PermissionError`, then a plain `OSError(errno.EIO, ...)`. For each,
      `cli.main` returns 2 and prints the error's text with no `regate:` line.
      No member builds an image, calls `reverify` or records a re-gate.
    witness: tests/test_regate.py::test_regate_declines_an_exemption_it_cannot_read
    wrong_versions:
      - The reader's exception escapes `run_regate`, so the command exits 2 rather than declining.
      - The raise is caught and the suite runs with no exemption.
      - The reader runs after the image build, so a decline still pays for one.
      - The decline line carries a fixed sentence that names no file.
      - The decline line carries a fixed sentence that names the file's path and drops the exception's text.
      - The decline records a re-gate row before it returns.
      - "`run_regate` catches `OSError` beside the reader's exception, so a host failure is a decline and exits 1."
      - "`run_regate` answers an `OSError` with an empty list, so the suite runs with no exemption and exits 0."
      - "`run_regate` catches `PermissionError` beside the reader's exception, so a denied open exits 1."
      - "`run_regate` lets `PermissionError` through and declines every other `OSError`, so `EIO` exits 1."
  - claim: >-
      A branch `run_regate` cannot fetch still exits 2 and names itself,
      so the new decline reaches only the exemption file.
    witness: tests/test_regate.py::test_regate_exits_two_on_infrastructure_and_records_nothing
    preserves: true
    mutant:
      file: saffron/regate.py
      find: raise package_phase.PackageError(
      replace: raise _Declined(
    wrong_versions:
      - The decline catches `PackageError`, so an unfetchable branch exits 1 as a decline.
  - claim: >-
      `package` still hands `reverify` the `revert_exempt` on the outcome it
      is given, so a rebuilt outcome's set reaches the head suite.
    witness: tests/test_package.py::test_package_re_verifies_with_the_cells_revert_exemption
    preserves: true
    mutant:
      file: saffron/phases/package.py
      find: exempt=outcome.revert_exempt,
      replace: exempt=(),
---

## Context

Backlog item **b-6b06e1**, under `DESIGN.md` §5.6 and §5.7. `SA-0273` exempts
from `revert` a test REBUT added that killed a surviving probe. `SA-0266` added
`saffron package`, and `SA-0284` added `saffron regate`. Neither reads the
exemption back. Every line below was read at `f596e814`.

**What the cell records.** `saffron/cell/session.py:3556-3559` writes the set to
`revert-exempt.json` in the task directory. That write sits under the branch at
`saffron/cell/session.py:3511`, so it happens only when a surviving blocker's probe ran again
after the rebuttal moved HEAD. The directory is `out_dir / spec.spec_id`
(`saffron/cell/session.py:2174`). `saffron/cell/session.py:3792` puts the same set on the live
`CellOutcome`.

**Who drops it.** `CellOutcome(...)` at `saffron/task.py:1308` sets no
`revert_exempt`, so the field keeps its empty default (`saffron/cell/session.py:467`).
`saffron/regate.py:162` calls `reverify` with no `exempt`, and the parameter
defaults to `()` (`saffron/phases/package.py:484`). `saffron/phases/package.py:836` passes the
outcome's set, and `saffron/phases/package.py:574` hands it to the head suite. So the set is
lost before `package` sees it on the one path, and at the call on the other.

**What the loss does.** A test the exemption covers can pass with its source
reverted. That is the property `DESIGN.md` §5.6 exempts. Without the set,
`revert` fails it on a sound diff. `saffron package` then ends the task
`MERGE_FAILED` (`saffron/phases/package.py:866`), and `saffron regate` reports a new failure PACKAGE did not see.

**One task directory per spec.** Nothing removes `revert-exempt.json` between
cells of one spec. `saffron/cell/session.py:3557` is the only line in `saffron/` that names
the file. A later cell that never reaches that write leaves the earlier cell's
file behind. `ready_task` already reads a file older than `baseline.json` as
another cell's (`saffron/task.py:1271-1273`). `saffron/cell/session.py:2360` writes
`baseline.json` for each cell that reaches its baseline suite. So this reader
takes the same rule.

## Problem

Three edits. Each rests on the one before.

1. **The reader.** Add `read_revert_exempt(task_dir: Path) -> list[str]` to
   `saffron/phases/package.py`, and an exception `RevertExemptUnreadable`
   subclassing `PackageError` beside `LeaseRejected` and `ParentGone`
   (`saffron/phases/package.py:71`, `saffron/phases/package.py:75`). Both callers import this module as `package_phase`
   already (`saffron/task.py:69`, `saffron/regate.py:19`). The reader alone
   decides the file's name, its freshness and its shape. A damaged current
   file raises that exception: invalid JSON, zero bytes, undecodable bytes, a
   value that is not a list of strings, or a directory at that path. An empty
   answer for it is the defect this spec closes, so the reader never gives one.
   Any other `OSError` on a current file is infrastructure, so the reader does
   not catch it. `saffron/task.py:1234` reads `patch.json` with no catch, and
   the same failure there raises bare today. Neither caller catches it either.
   The `try` opening at `saffron/cli.py:361` holds both commands
   (`saffron/cli.py:378`, `saffron/cli.py:387`), and its handler at
   `saffron/cli.py:407` exits 2.
2. **`ready_task`.** Call the reader through `package_phase`, and put its answer
   on the rebuilt `CellOutcome`. `RevertExemptUnreadable` becomes a `Refused`
   that carries the exception's text. `ready_task` has that shape for every other file it
   refuses (`saffron/task.py:1228`), and `saffron/cli.py:3027-3029` prints it as a `package:`
   line and exits 1. Call it before the `tree_base` fallback at `saffron/task.py:1287`,
   so the refusal writes nothing to the mirror. Do not put it behind the local
   freshness helper. That helper tests for a regular file, so a directory at
   that path would read as no exemption.
3. **`run_regate`.** Call the reader through `package_phase` inside the `try` at
   `saffron/regate.py:141`, over `out_dir / row["spec_id"]`.
   `RevertExemptUnreadable` prints a `regate:` line with the exception's text and returns 1, as `_Declined` does
   at `saffron/regate.py:155-157`. It has to leave that `try` before the image build at
   `saffron/regate.py:159`. Pass the answer to `reverify` as `exempt`. `run_regate`'s
   `out_dir` is the root the cell wrote under, since `saffron/cli.py:321` sets one
   root unless a command declares `--out`, and only `replay` does (`saffron/cli.py:130`).

## Out of scope

- `saffron/cell/session.py`, which writes the file and carries the live set. It
  sits under `elevate_on`, and nothing in it changes.
- `_finish_verify`'s call of `reverify` at `saffron/cli.py:1044`. It judges a
  finishing commit under `finish.finish_suite`'s own suite, and no task's cell
  stands behind it.
- A second cell's file read for an older task. `run_regate` takes any task id
  whose pull request is open, and the directory holds the newest cell's record.
  An older task with a later cell of its own spec reads that cell's answer. The
  directory carries no task id to tell them apart.
- A dangling symlink at the file's path. It reads as no file. No line in
  `saffron/` writes one.
- `saffron adopt`'s handling of a decline. `saffron/cli.py:2962` calls `run_regate`, and
  its existing branches report a decline and keep the task's state. A host
  failure raises through it as any raise of `run_regate` does
  (`tests/test_cli.py:3574`).

## Notes for the agent

**Which criteria carry a mutant.** The reader and the two refusals are new code.
Criteria 1, 3 and 5 declare a witness and no mutant, and `witness` reports `skip`
for each. Criteria 2 and 4 edit existing code, and each mutant sits on a line
that code already determines. Criteria 6 and 7 are `preserves`. Each names
a test at base, and the mutant proves that test still bites.

**Keep each witness able to fail.** Reach the reader and its exception through
the module, as `package_phase.read_revert_exempt` and
`package_phase.RevertExemptUnreadable`. `tests/test_package.py` imports the
module's names in one block at module scope. A new name in that block makes the
whole file a collection error with the source reverted. Import the module
object there under a second name, and leave that block alone.

**Pin mtimes.** Two writes in one test can share a timestamp, so set every
file's mtime with `os.utime`. `tests/test_task.py`'s `_rt_seed_records` takes
`when=`, and its `_rt_set_mtime` sets one file.

**Fixtures.** `tests/test_task.py`'s `_rt_ledger`, `_rt_task`, `_rt_write_patch`
and `_rt_seed_records` build a ready task. Record the spec text with
`ledger.record_spec_text`, so `_spec_for_task` needs no spec file.
`tests/test_regate.py`'s `_build_fixture`, `_seed_task`, `_gh_pr_view`,
`_install_probe_fakes` and `_fake_reverify` build a regate, and `_fake_reverify`
records every keyword it gets. The task directory under `--home <home>` is
`<home>/batches/v0/SA-0005`. A single fixture can serve every member of a test,
so build it once and rewrite the file between calls. `regates` holds a row only
after a judged run, so a decline leaves it empty.

**The fallback member.** Build criterion 3's fallback member on
`_rt_parent_chain` (`tests/test_task.py:3309`), called as at
`tests/test_task.py:3369`, and pass its checkout as `repo`. A real checkout makes
the mirror assertion live. `tests/test_task.py:3476` is a refusal on the same
fallback. With a fake repo, a read after the fallback still fails the witness, on
the `GitError` that escapes, and the mirror assertion never runs. Assert the
mirror path is absent before asserting the reason.

**The host-failure members.** In criterion 1, replace the open that the reader
reaches, for that path alone. Replace both `builtins.open` and `io.open`, since
`Path.open` calls the second. Do not use `chmod`, since the suite can run as root.
The read member's open returns a handle whose `read` raises. Hold each fault in
a name and assert with `is`, so a copy of the error fails. Criteria 3 and 5
replace the reader itself. Criterion 5's witness goes through `cli.main`, as
this file's other witnesses do. `tests/test_cli.py` is forbidden, so no witness
drives `saffron package` to exit 2 on this fault. Criterion 3 pins the raise, and
`tests/test_cli.py:3905` drives the handler on a raise from that command.

**What the host-failure members leave.** The set of `OSError`s is open. The
witnesses drive `PermissionError` and a plain `OSError`, and a catch naming
classes fails on the second. A failed `stat` behind the freshness check has no
witness, and a file at the task directory's own path has none. The reader leaves
both uncaught too.

**Two docstrings.** `run_regate`'s docstring at `saffron/regate.py:136-138` lists
a `PackageError` among the raises left to the caller. It must stop saying that of
`RevertExemptUnreadable`, and must name an `OSError` reading the file among those
raises. Every other `PackageError` still reaches the caller, as criterion 6 holds.
`ready_task`'s docstring at `saffron/task.py:1200-1202` lists a missing, stale or
unmatched file among its refusals, and only a git failure among its raises. It
must add a damaged file to the first and a host failure on this file to the second.

**Measured.** Every wrong version below each witness, and every mutant, ran on a
prototype of this spec, and each one failed its witness. That covers the ordering
versions too: criterion 1's older file parsed first and equal mtime, criterion
3's reader above the rebuilt `CellOutcome`, and criterion 5's reader after the
image build. Do not run them yourself. `size_gate` priced that prototype's whole
diff at 1023 changed tokens, tests counted, and 192 with the declared test paths
set aside. The first figure over four is `estimated_lines`. A real process on it,
with the file at mode `000`, exited 2 under both `saffron package` and
`saffron regate`, and printed `saffron: PermissionError:` with the path. Invalid
JSON exited 1 under both. `cli.main` with `EIO` from the open returned 2 under both.

**Existing tests.** `_fake_reverify` takes `**kwargs`, and
`test_ready_task_rebuilds_every_field_package_reads_from_the_cells_record`
writes no exemption file. No existing test needs a change.
