---
id: SA-0371
title: A probe cell that stops files every later criterion probe and wrong version unproven, and REVIEW counts them as expressed
type: bug
priority: 2
estimated_lines: 113
estimate_measured: true
touches:
  - saffron/cell/session.py
  - saffron/phases/review.py
  - tests/test_session.py
  - tests/test_review.py
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
  - harness/**
  - images/**
  - records/**
  - hooks/**
  - saffron/cell/runtime.py
  - saffron/cell/runtimes/**
  - saffron/cell/worktree.py
  - saffron/cell/proxy.py
  - saffron/events.py
  - saffron/ledger.py
  - saffron/record/**
  - saffron/gates/**
  - saffron/probe.py
  - saffron/report/**
  - saffron/repos/**
  - saffron/task.py
  - saffron/cli.py
  - saffron/batch.py
  - saffron/view/**
  - tests/conftest.py
  - tests/test_probe_cell.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
  - tests/fixtures/**
budget_usd: 45
max_attempts: 4
max_turns: 160
risk: standard
acceptance:
  - claim: >-
      When `_apply_criterion_probes` cannot enter its gate-only cell, or the
      cell stops part-way with a `runtime.CellRuntimeError`, it enters a
      fresh gate-only cell once more, unless no pair is left to ask. It
      enters it only after the cell before it is torn down, through
      `critic_cell` with the same keywords and the same `created` set. The
      fresh cell asks every pair not yet answered, in order. Four stops are
      driven. The mutator raising as it applies a pair's edit asks that pair
      again in the fresh cell. So does the `tests` gate raising at a pair's
      witness ask, and so does a survivor's line read raising. A raise at a
      survivor's second ask files that survivor's finding once, with its
      witness-ask claim, and the fresh cell starts at the next pair. When
      that survivor is the last pair, no fresh cell is entered. A cell that
      cannot be entered at all has every pair asked in the fresh one. A
      pair the fresh cell answers carries no `unasked` key.
    witness: tests/test_session.py::test_a_probe_cell_that_stops_is_entered_once_more_for_every_pair_left
    wrong_versions:
      - The fresh cell starts after the pair that was running, so a pair whose witness ask stopped the cell is never asked.
      - The fresh cell starts from the first pair, so pairs already answered are asked twice.
      - The fresh cell is entered while the cell before it is still open.
      - A survivor whose line read stopped the cell keeps `error`, and the fresh cell starts at the next pair.
      - A survivor whose second ask stopped the cell is asked again, so its finding is filed twice.
      - A cell that cannot be entered gets no fresh cell.
      - The fresh cell is handed a fresh `created` set.
      - Only a stop from the mutator enters a fresh cell, and a stop from the `tests` gate does not.
      - A stop at the last pair's second ask enters a fresh cell.
  - claim: >-
      When the fresh cell also stops, or cannot be entered, no further cell
      is entered. A pair the fresh cell answered before its own stop keeps
      its outcome and carries no `unasked` key. Every pair still unasked
      then reads outcome `error`, never `unproven`. The pairs still unasked
      include the pair whose witness ask or line read was running when the
      fresh cell stopped. Its summary replaces the one the witness gate or
      the line read wrote. Each such pair's `unasked` key holds the text of
      the runtime error that ended the fresh cell. Its summary is `the probe
      cell stopped before this edit's answer was recorded: ` followed by
      that text after a stop. After a failed entry it is `the probe cell
      could not be entered: ` followed by that text. A survivor whose second
      ask stopped the fresh cell keeps `survived` and its one finding, with
      no `unasked` key. The witness drives a stop of the fresh cell at a
      witness ask, after it answered one pair, at a survivor's line read and
      at a survivor's second ask. It also drives a stop followed by a fresh
      cell that cannot be entered, and two cells that cannot be entered. In
      the same calls a pair with no edit and a refused pair still read
      `unproven` with no `unasked` key. Every pair in a repo whose head
      declares no `tests` gate reads `unproven` with no `unasked` key, and
      no cell is entered.
    witness: tests/test_session.py::test_a_second_stop_files_every_pair_left_as_an_error_naming_the_runtime_error
    wrong_versions:
      - A stop of the fresh cell enters a further cell.
      - The pairs left read `unproven` with the new summary.
      - The pairs left read `error` with the old summary, which names no runtime error.
      - The `unasked` key holds the first cell's error instead of the one that ended the fresh cell.
      - A fresh cell that cannot be entered gets the stopped summary instead of the unenterable one.
      - A pair with no edit, or a refused pair, is marked `unasked` too.
      - A repo with no `tests` gate reads `error`.
      - A survivor whose second ask stopped the fresh cell is marked `unasked`.
      - Every pair handed to the fresh cell is marked `unasked`, including those it answered before its own stop.
      - The pair running at the fresh cell's stop keeps the witness gate's own `error` summary and no `unasked` key.
  - claim: >-
      `review.describe_criterion_probes` and `review.describe_wrong_versions`
      each count the edits, across every entry, that carry an `unasked` key.
      With one or more, the line gains `; N never asked: ` and the `unasked`
      text of the first such edit. That tail follows the line's counts and
      precedes any `; no session answered: ` tail. An edit whose outcome is
      `error` and which carries no `unasked` key is not counted. The named
      and expressed counts are unchanged. With no such edit each line is
      exactly as at base. The witness drives both functions, each with and
      without an unanswered session.
    witness: tests/test_review.py::test_the_review_lines_count_the_edits_no_probe_cell_asked
    wrong_versions:
      - The tail counts every edit whose outcome is `error`.
      - Only the criterion-probe line gains the tail.
      - A line with no unasked edit still gains a tail reading zero.
      - The named count drops the unasked edits instead of adding a tail.
      - The tail follows the unanswered sessions' tail.
      - The tail names the last unasked edit's error instead of the first's.
---

## Context

Backlog item b-7c88f8, its second arm: an error in the probe cell reaches
the operator as an error distinct from `unproven`. The spec loop's run 62
hit it on 2026-11-11. `SA-0369`'s gate-only cell stopped at its 26th
criterion probe, a survivor, during the second ask. The 9 criterion probes
after it and all 37 wrong versions were filed `unproven` with a summary
that names no error. The task reached `READY_FOR_REVIEW`. Its REVIEW lines
read `criterion probes: 34 named over 4 criteria, 2 unnamed, 0 refused` and
`wrong versions: 37 declared, 37 expressed, 0 refused`. The pull request's
Spec seat then found 4 witness blockers among those same wrong versions.
The record is `criterion-probes.json` and `wrong-versions.json` under that
task's directory.

**One gate-only cell asks every pair.** `_apply_criterion_probes`
(`saffron/cell/session.py:2058`) files a pair with no edit as unproven,
with the summary "this session named no edit" (`saffron/cell/session.py:2103-2105`).
It files a refused pair as unproven with its refusal under `refusal`
(`saffron/cell/session.py:2106-2110`). A repo whose head declares no `tests`
gate files every pair unproven and enters no cell
(`saffron/cell/session.py:2115-2121`). The rest are asked in one cell entered through
`critic_cell` with `network=None` and the repo's gate env (`:2129-2143`).

**A cell that cannot be entered files every pair `unproven`.** The
`except` files them with `_PROBE_CELL_UNENTERABLE` and the error
(`saffron/cell/session.py:2144-2146`). That constant reads `the probe cell
could not be entered: ` (`:114`).

**A stop part-way files every later pair `unproven`.** `_mutate` and
`_run_tests` set `stopped` when the cell raises `runtime.CellRuntimeError`
(`saffron/cell/session.py:2153-2175`). The loop over pairs starts at
`:2177`. Three exits then file every later pair with `unknown_tree`, whose
text names no error (`:2090-2093`):

- A stop at the witness ask. The witness gate files the pair itself as an
  error first (`saffron/cell/session.py:2190-2194`).
- A raise reading a survivor's line, which files the pair as an error
  (`saffron/cell/session.py:2209-2213`).
- A raise at a survivor's second ask, which appends the finding with its
  witness-ask claim first (`saffron/cell/session.py:2227-2232`).

**Entering a fresh gate-only cell reuses the names.** `critic_cell`
pre-cleans its container, volumes and network by name before it creates them
(`saffron/cell/session.py:1576-1580`). With `network=None` the names are
`saffron-gate-*` (`:1559-1566`). An entry after the cell before it is torn
down reuses them. That is reasoned from the pre-clean, not measured: no cell
has yet been entered twice this way.

**The REVIEW lines count named edits, not asked ones.**
`describe_criterion_probes` counts a probe with an edit and no `refusal` as
named (`saffron/phases/review.py:638-659`, `:650`).
`describe_wrong_versions` counts a version with an edit and no `refusal` as
expressed (`:831-850`, `:842`). Each appends `; no session answered: ` and
the witnesses whose session errored. REVIEW calls `_apply_criterion_probes`
(`saffron/cell/session.py:3478`). It then writes each record and emits each
line (`saffron/cell/session.py:3498-3517`). Both lines read the entries the
call wrote in place.

**The task is not stopped, by decision.** `review_state` stops at
`REVIEW_INCOMPLETE` only on a cut pool or an errored lens
(`saffron/phases/review.py:1066-1075`). `run_task` packages only
`READY_FOR_REVIEW` or an `EXHAUSTED` task with a standing blocker
(`saffron/task.py:947-952`). Stopping here would discard a green cell's pull
request over an infrastructure fault. Principle 36 prefers one re-run
charged to nobody over a consumer reading a truncated set (Appendix H).

## Problem

- **A stopped probe cell disowns nothing.** Every pair after the stop reads
  `unproven`, as a session that named no edit does. Its summary names no
  error.
- **One fault costs every later claim.** Nothing tries again, so one exec
  failure leaves every later criterion unguarded by the host's own edits.
- **The REVIEW lines read an unasked edit as named or expressed.** An
  operator reads `37 expressed` and cannot tell that none was asked.

## Out of scope

**`probe_findings`** (`saffron/cell/session.py:1863`). It serves REVIEW's
vacuity probes through `_probe_adequacy` (`:2023`). REBUT's probes call it too
(`saffron/cell/session.py:3657`). Its `unproven(remaining, ...)` paths (`:1976`, `:1983`, `:2001-2018`)
are unchanged. REBUT's check that reads `_PROBE_CELL_UNENTERABLE` reads
only that function's entries (`:3698-3704`). The new summaries do not
reach it.

**The criterion-probe session's own error.** A session that errored is an
entry with an `error` field (`saffron/phases/review.py:656-658`). Its probes
stay as they are.

**`review_state`, the task's state, and the pull request's Not covered
section** (`saffron/report/pr_body.py:690-698`).

**A line for a retry that succeeded.** A fresh cell that answers every
pair emits nothing new. Only the record and the REVIEW lines change when
pairs stay unasked.

**The pull request.** `DESIGN.md` §5.4.1 says a criterion with no usable
answer is named on "the REVIEW line and the pull request". This spec names
unasked edits on the REVIEW lines only. The pull request's Not covered
section is left for a later item.

**A restore that raises.** `_mutate` sets `stopped` for a raise on the
mutator's exit too. Criterion 1 drives the raise on entry alone, through the
same handler.

## Notes for the agent

**This change is new behaviour.** No criterion has a mutant on the ref. Each
witness reads a fresh cell's entry, an `unasked` key or a tail the base
never produces. Expect `witness` to report `skip` for all three.

**One shape that fits.** Move the loop over pairs into a nested function
that takes a container and the pairs to ask. On a stop it returns the index
of the first pair left to ask and the runtime error's text. It returns
`None` when every pair was answered. The witness-ask stop and the line-read
stop return the running pair's index. The second-ask stop appends the
finding, as at base, and returns the next index. Call it inside a loop of
two cell entries. Close each entry's `ExitStack` before the next entry. If
the pairs left are empty, return without entering. Then write `outcome`,
`summary` and `unasked` onto each pair still left, over whatever the cell
wrote for it. Remove
`unknown_tree`. Name the new summary prefix as a module constant beside
`_PROBE_CELL_UNENTERABLE`.

**The second-ask stop is not asked again.** The decision is that the pair
running when the cell stopped is asked again. A survivor at its second ask
has its witness answer and its finding already filed. Asking it again would
file the finding twice. A fresh cell that cannot reach it would also drop
the blocker. So it keeps today's finding, and the fresh cell starts at the
next pair.

**Why the stopped summary says the answer was recorded.** Take a survivor
whose line read stopped the cell. Its witness answered `survived`, but no
finding was filed for it. "Asked" would be false for it, and "recorded" holds for every
pair left. The key stays `unasked`, so criterion 3 counts that survivor with
the rest.

**Docstrings.** `_apply_criterion_probes`'s docstring stays within ten lines
and says the cell is entered once more, and names the `unasked` key. Add one line to the
REVIEW lines' docstrings, or give the shared tail its own helper with one.

**Existing tests that change.**

- `test_a_survivor_whose_whole_suite_cannot_answer_keeps_todays_blocker`
  (`tests/test_session.py:14634`) asserts the fifth criterion is filed
  `unproven` with `unknown_tree` (`:14745-14755`). Under this change a
  fresh gate-only cell asks it. Append one `tests` result to its scripted
  answers for that ask. Add `["t.py::e"]` to its subsets and `e` to its
  mutated list, and assert the outcome that result gives. Correct its
  docstring's sentence about the fifth criterion. Rename no test, since
  `census` compares test names.
- `_stub_probe_gates` answers both cells. They share the `saffron-gate-`
  name.

**The witnesses.**

- Criteria 1 and 2 call `session._apply_criterion_probes` directly. Stub
  `session.critic_cell` with a context manager that records its keywords
  and an ordered log. It yields `gate-1` for the first entry and `gate-2`
  for the next, or raises a scripted `runtime.CellRuntimeError` on entry.
  Stub `saffron.gates.runner.run_gate` to log the container and subset and
  answer from a scripted list, raising an exception item. Stub
  `saffron.cell.worktree.source_mutated` and `read_at_head` by container,
  so a raise can target one cell. Build `gate_comparison` from
  `SuiteComparison` and `SuiteRun` with a passing `tests` result that
  collected every witness. Pass `_ANCHORING_DIFF` as the diff.
- A killed witness ask answers `fail`. A survivor answers `pass`, then its
  second ask's subset is empty.
- Criterion 1 also drives a stop at the last pair's second ask, and asserts
  one cell entry. Criterion 2's stop at a witness ask comes after the fresh
  cell answered one pair, and asserts that pair has no `unasked` key.
- Compare the log's entries and exits as one ordered list. Compare the two
  keyword sets for equality and `created` by identity.
- Criterion 3 builds entries by hand. Give a later unasked edit a different
  text from the first, so a tail naming the last fails.

Import every name the change adds inside a test body. A module-scope import
of one makes the reverted test a collection error, which `revert` reads as
`skip`.

**Measured on a prototype.** A diff built to this spec at base measured 453
changed tokens on `size_gate` outside `tests/**`, and 1726 under it. The
`bug` ceiling is 1300. All three witnesses failed with the source reverted.
Each wrong version listed under the three criteria ran against its witness,
and each failed it. `tests/test_session.py` and `tests/test_review.py` pass
whole on the prototype.

**`error` is not `fail`.** An unasked pair is the infrastructure's fault and
charged to nobody. It files no finding and changes no state.

Commit after each coherent step. Uncommitted work dies with the cell.
