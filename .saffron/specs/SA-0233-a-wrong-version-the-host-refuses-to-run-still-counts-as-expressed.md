---
id: SA-0233
title: A wrong version the host refuses to run still counts as expressed on REVIEW's line
type: bug
priority: 1
depends_on: [SA-0231]
estimated_lines: 218
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
  - records/**
  - hooks/**
  - images/**
  - saffron/agents/**
  - saffron/record/**
  - saffron/view/**
  - saffron/gates/**
  - saffron/probe.py
  - saffron/phases/rebut.py
  - saffron/phases/package.py
  - saffron/report/**
  - saffron/intake.py
  - saffron/ledger.py
  - saffron/task.py
  - tests/test_probe_check.py
  - tests/test_package.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 20
max_attempts: 3
max_turns: 140
acceptance:
  - claim: >-
      In `wrong-versions.json`, a wrong version whose edit
      `probe.probe_refusal` refuses carries that function's reason, word for
      word, under the key `refusal`. The witness drives each reason the
      function can return. They are an edit on a declared test path, an edit
      whose path climbs out of the tree through `..`, an edit with an
      absolute path, and a source edit in a repo that declares no test
      paths. A version with no edit, a version its witness kills, and a
      version the mutator refuses inside the probe cell carry no `refusal`
      key. The host enters the mutator for the last two alone.
    witness: tests/test_session.py::test_a_wrong_version_the_host_refuses_to_run_carries_its_refusal
    wrong_versions:
      - Only a refusal naming a test path is recorded, so the two outside-the-tree reasons carry none.
      - Only a repo with declared test paths records a refusal, so the bare repo's source edit carries none.
      - The key holds `True` rather than the reason.
      - Every version that is not refused carries `refusal` set to null.
      - A version with no edit is recorded with `refusal` set to "this session named no edit".
      - A version the mutator refuses inside the probe cell is recorded with a `refusal`.
      - The refusal is written to `summary` alone, as at base.
  - claim: >-
      REVIEW's wrong-version line reads `wrong versions: <n> declared, <e>
      expressed, <r> refused`, then the `; no session answered: ` clause
      when an entry carries an error, as at base. `r` counts versions that
      carry `refusal`. `e` counts versions with an edit and no `refusal`, so
      a version the mutator refused inside the probe cell stays expressed. A
      version with no edit counts in neither. The line prints `0 refused`
      when none is. The witness pins the whole line for six arrangements:
      none, some and all versions refused, each with and without an
      unanswered entry. Its refused versions carry all three reasons.
    witness: tests/test_review.py::test_the_wrong_version_line_counts_refused_versions_apart_from_expressed_ones
    wrong_versions:
      - Expressed still counts every version with an edit, refused ones included.
      - Refused counts every version with an edit whose outcome is `unproven`, so the mutator's refusal counts too.
      - Refused counts versions whose summary names a test path, so the two other reasons count as expressed.
      - Refused counts versions with no edit as well.
      - The refused clause is left off when the count is zero.
      - The refused clause follows the unanswered clause.
  - claim: >-
      A spec whose every wrong version REVIEW expressed as an edit to a
      declared test path, the shape of `SA-0200`, reads `REVIEW: wrong
      versions: 2 declared, 0 expressed, 2 refused`. The host enters the
      mutator for none of them.
    witness: tests/test_session.py::test_a_spec_whose_wrong_versions_all_edit_tests_reads_none_of_them_expressed
    wrong_versions:
      - The session records each refusal and the line still counts every edit as expressed.
      - The line counts refusals from a key the session never writes.
      - The session never records a refusal, so the line reads `0 refused`.
---

## Context

Backlog item **b-34d743**, found in the spec loop's run 28. It cites
`DESIGN.md` §5.5. Every line number below was read at `958db033`. Your base
also carries `SA-0231`, which edits `saffron/cell/session.py` in REBUT's
budget code. So the session line numbers below are stale there. Find each
place by the text quoted beside it.

**What REVIEW records for a wrong version.** `run_wrong_versions` buys one
session per criterion that declares wrong versions
(`saffron/phases/review.py:595-701`). Each version's dict holds `version`,
`edit` and `reason` (`saffron/phases/review.py:559-580`). A criterion whose
session never answered keeps every version with a null `edit`
(`saffron/phases/review.py:544-556`).

**What the host runs.** `_apply_criterion_probes` takes every criterion
probe and every wrong version as pairs (`saffron/cell/session.py:1695`). Its
first loop sorts them (`saffron/cell/session.py:1736-1747`). A pair with no
edit is `unproven` with the summary "this session named no edit"
(`:1739-1741`). Otherwise it calls
`probe_check.probe_refusal(entry["edit"]["file"], test_paths)` (`:1743`). A
pair it refuses is `unproven`, with the refusal as its summary, and skipped
(`:1744-1746`). Only the rest reach the mutator and the witness
(`:1747`). `_unproven` writes `outcome` and `summary` and nothing else
(`:1732-1735`).

**The three refusals.** `probe_refusal` returns one of three reasons
(`saffron/probe.py:153-167`). A path that is absolute or climbs out of the
tree gives `<file> is not a relative path inside the tree` (`:160-162`). A
repo with no declared test paths gives `the repo declares no test paths, so
source cannot be told from test` (`:163-164`). A path a declared glob
matches gives `<path> is a test; a probe must target source` (`:165-166`).
The mutator's own refusals are a different thing. `worktree.source_mutated`
answers them inside the probe cell, after the host chose to run the edit
(`saffron/cell/worktree.py:573`). `witness_gate` then reports `skip`, which
`criterion_probe_outcome` records as `unproven`
(`saffron/phases/review.py:722-727`).

**The line.** REVIEW writes `wrong-versions.json` after every edit is
applied, then emits `review.describe_wrong_versions(wrong_versions)` as a
REVIEW line (`saffron/cell/session.py:2977-2985`). That function counts a
version as expressed when its `edit` is not null
(`saffron/phases/review.py:713-714`). It appends `; no session answered: `
and each errored entry's witness (`:715-717`). Nothing parses the line. It
is read by people, and `git grep "expressed"` finds no reader in `saffron/`
or `.claude/`.

**What `SA-0200` showed.** Its fix edited two test files. REVIEW printed
`wrong versions: 14 declared, 13 expressed`.
`~/.saffron/batches/v0/SA-0200/wrong-versions.json` holds 14 versions, all
`unproven`. The 13 with an edit name `tests/test_scheduler.py` or
`tests/test_queued_specs.py`, and each summary reads `... is a test; a
probe must target source` (read 2026-10-07).

## Problem

A version whose edit the host refuses to run is counted as expressed. On a
spec whose subject is a test, every version can be refused, and the line
still reads as though most of them were measured. `SA-0200`'s line read 13
of 14, and none was run. The delegate found that only by opening the file.
The record says why in each summary, but nothing marks a refusal apart from
any other `unproven`.

## Out of scope

- **Running a wrong version against a test file.** That needs a way to
  judge a witness by an edit to itself. It is a design question shared
  with b-3c17ab, and this spec only counts what the host declines to run.
- **Criterion probes.** They pass through the same loop, so a refused one
  gains `refusal` in `criterion-probes.json` as well. Its line,
  `describe_criterion_probes`, counts named and unnamed edits and claims
  nothing about running them. Leave it unchanged.
- **The mutator's refusals.** An edit `source_mutated` refuses was chosen
  for running. It stays expressed and carries no `refusal`.
- **The pull request body.** Its `Not covered` section reads only an
  entry's `error` (`saffron/report/pr_body.py:597-599`).
- **IMPLEMENT's and REBUT's code in `saffron/cell/session.py`.** `SA-0230`
  and `SA-0231` edit those regions. Change nothing outside the first loop
  of `_apply_criterion_probes`, except one sentence of its docstring that
  names the `refusal` it now writes.

## Notes for the agent

**All three criteria are new behaviour.** The key and the third count do
not exist at base, so no text pins honestly. Each criterion declares a
witness and no mutant. Expect `witness` to report `skip` for each.

**The record.** In `_apply_criterion_probes`'s first loop, a pair that
`probe_refusal` refuses also gets `entry["refusal"]` set to that reason.
Set the key on no other pair, and leave `summary` as it is.

**The line.** In `describe_wrong_versions`, count `refused` as the versions
whose `refusal` is present and not null. Count `expressed` as the versions
with an edit, less the refused ones. Print `wrong versions: <n> declared,
<e> expressed, <r> refused`, then the unanswered clause as today. Update
the docstring to say the clause counts what `probe.probe_refusal`
refused. The no-`tests`-gate and probe-cell-not-entered paths also run no
edit, carry no `refusal`, and stay counted as expressed.

**Criterion 1's witness.** Drive one criterion with six wrong versions
through `_drive`, with `_PROBE_POLICY` and the `tests` gate. Its answer, in
order, is no edit, then `spec/t.py`, `../outside.py` and `/abs/outside.py`.
Then come two edits to `src/x.py`. Stub the mutator so it refuses the
second of those, and script one `fail` result so the witness kills the
first. Assert the six `refusal` values in order, with `.get`. Then assert
the key is absent from the three versions that must not carry it. Assert
`cell.mutated` holds exactly the two `src/x.py` edits. Then drive a second
cell under a policy with no `integrity` section, one criterion with no edit
then a `src/x.py` edit. Assert the second carries `the repo declares no
test paths, so source cannot be told from test`, the first carries no
key, and the mutator was never entered.

**Criterion 2's witness.** Build entries by hand in `tests/test_review.py`
and call `review.describe_wrong_versions` on each. Use four kinds of
version:

- killed: an edit, and outcome `killed`
- unnamed: no edit
- refused: an edit and a `refusal`, the three reasons in turn
- stuck: an edit, outcome `unproven`, and no `refusal`

The lines below are what the change prints for these arrangements,
measured on a prototype:

| arrangement | line |
| --- | --- |
| none refused | `wrong versions: 3 declared, 2 expressed, 0 refused` |
| some refused | `wrong versions: 6 declared, 3 expressed, 2 refused` |
| all refused | `wrong versions: 3 declared, 0 expressed, 3 refused` |
| none, unanswered | `wrong versions: 4 declared, 2 expressed, 0 refused; no session answered: t.py::z` |
| some, unanswered | `wrong versions: 7 declared, 3 expressed, 2 refused; no session answered: t.py::z` |
| all, unanswered | `wrong versions: 4 declared, 0 expressed, 3 refused; no session answered: t.py::z` |

- none refused: one entry, killed, unnamed and killed
- some refused: an entry holding killed and refused, then one holding
  unnamed, refused, killed and stuck
- all refused: one entry of three refused versions
- unanswered: witness `t.py::z`, one unnamed version, and an error

**Criterion 3's witness.** One criterion, two wrong versions, both edits
to files under `spec/`, with `_PROBE_POLICY`. Take the REVIEW line from
`cell.watched` and assert it whole. Assert `cell.mutated == []` too.

**Two tests already assert the old line or the old record.**
- `tests/test_session.py::test_every_wrong_version_is_recorded_with_its_outcome_beside_the_criterion_probes`
  asserts `wrong-versions.json` whole (`tests/test_session.py:9014-9095`).
  Its version `a v2` is refused as a test. Its summary is at
  `tests/test_session.py:9035`. Add a `refusal` beside it holding the same
  text. Its line at `tests/test_session.py:9105` becomes this one.

  `REVIEW: wrong versions: 6 declared, 2 expressed, 1 refused; no session answered: t.py::d`
- `tests/test_review.py::test_each_criterion_with_wrong_versions_gets_one_session_that_turns_each_into_an_edit`
  asserts `wrong versions: 4 declared, 3 expressed` (`tests/test_review.py:1296`).
  It becomes `wrong versions: 4 declared, 3 expressed, 0 refused`.

Change nothing else in either test. Put the new witnesses at the end of
their files. `tests/test_session.py`'s helpers `_drive`, `_probe_turns`,
`_wrong_version_answer`, `_stub_probe_gates` and `_tests_result` already
fit.

Commit after each witness passes. Uncommitted work dies with the cell.
