---
id: SA-0119
title: Two rules decide where a vacuity probe is applied, and an empty `test_paths` reads as nothing being a test
type: bug
priority: 2
touches:
  - saffron/probe.py
  - saffron/cell/session.py
  - docs/evidence/scripts/2026-09-08-lens-corpus.py
  - tests/test_probe_check.py
  - tests/test_session.py
  - tests/test_corpus.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
  - pyproject.toml
  - uv.lock
  - .saffron/**
  - ontology/**
  - tests/ontology/**
  - images/**
  - harness/**
  - harness/recovery.py
  - docs/backlog/**
  - docs/appendices/**
  - docs/adr/**
  - docs/evidence/fixtures/**
  - docs/evidence/passes/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/agents/**
  - saffron/cell/worktree.py
  - saffron/cell/runtime.py
  - saffron/repos/**
  - saffron/ledger.py
  - saffron/task.py
  - tests/test_worktree.py
  - tests/test_package.py
  - tests/test_revert.py
  - tests/test_proxy.py
budget_usd: 20
max_attempts: 3
max_turns: 130
risk: elevated
acceptance:
  - claim: >-
      `check_probe` refuses a probe by the rule `revert` uses. That rule is
      `scope.matches` over the `test_paths` globs it is given, against the
      normalised path. Under a `**` glob it refuses three spellings of one
      file beneath it: plain, with a leading `./`, and through a `..` segment.
      None of them enters the mutator. Under a single-star glob it applies a
      probe on a file one directory deeper, which `fnmatch` would refuse.
      Given no test
      paths, it refuses every probe on a path inside the tree without entering
      the mutator. The reason is "the repo declares no test paths, so source
      cannot be told from test". A bare `tests` refuses nothing beneath it, as
      it refuses nothing there for `revert`.
    witness: tests/test_probe_check.py::test_check_probe_refuses_by_reverts_glob_rule_and_on_no_test_paths
    mutant:
      file: saffron/probe.py
      find: "normalised = posixpath.normpath(file)"
      replace: "normalised = file"
  - claim: >-
      The host asks for no Gate-only cell when no probe in a review could be
      answered in one. Every probe is then `unproven` with its reason, and the
      task still ends `READY_FOR_REVIEW`. The witness drives three reviews of
      two probes each. One repo declares no `tests` gate. One declares no test
      paths. In the third, `check_probe`'s rule refuses both probes, one on a
      declared test path and one outside the tree.
    witness: tests/test_session.py::test_a_probed_review_no_probe_cell_could_answer_enters_none
    mutant:
      file: saffron/cell/session.py
      find: 'if "tests" not in gates:'
      replace: "if False:"
  - claim: >-
      The lens-corpus driver's `TEST_PATHS` equals the globs this repo
      declares as `integrity.test_paths`.
    witness: tests/test_corpus.py::test_the_driver_passes_check_probe_this_repos_declared_globs
  - claim: >-
      A probe on source, in a repo that declares test paths and a `tests`
      gate, is still applied in the Gate-only cell, and its `probe_verdict`
      still decides the finding.
    witness: tests/test_session.py::test_a_concern_whose_probe_survives_is_rebutted_as_a_blocker
    preserves: true
---

## Context

Backlog item **b-461729**, with item **b-a70ec1** folded in. Both were found
by the spec loop's Spec seat reviewing #375 (`SA-0109`) on 2026-09-19.

Two rules decide whether a vacuity probe is on a test file.

- The host refuses one before any Gate-only cell. `_declared_test_path`
  (`saffron/cell/session.py:1243-1252`) normalises the path and matches it
  with `scope.matches` against the policy's `integrity.test_paths`. The loop
  at `:1328-1340` records each match `unproven`.
- The host then passes `test_paths=()` to `check_probe`
  (`saffron/cell/session.py:1398`). So the refusal through `_under` at
  `saffron/probe.py:173` never fires in a task. `_under`
  (`saffron/probe.py:140-145`) is a segment prefix, so a bare `tests` covers
  every file beneath it.
- `scope.matches` (`saffron/gates/core/scope.py:31-36`) is a glob. A bare
  `tests` matches the path `tests` and nothing beneath it.

The `revert` gate calls `matches` over the same list
(`saffron/gates/core/revert.py:165`). It also refuses to run on an empty list
(`:153-162`). Its summary there reads "the repo declares no test paths, so
source cannot be told from test". The policy's `test_paths` defaults to `[]`
(`saffron/repos/policy.py:61`). The probe path has no such refusal. With nothing declared, every file reads as source, and a
probe that deletes an assertion survives and promotes its finding to a
blocker.

The lens-corpus driver declares `TEST_PATHS = ("tests/",)`
(`docs/evidence/scripts/2026-09-08-lens-corpus.py:119`) and passes it to
`check_probe` (`:268-273`). Its docstring at `:120-123` explains that the
prefix differs from the policy's globs.

Item b-a70ec1: the branch at `saffron/cell/session.py:1343` records every
remaining probe `unproven` when the repo declares no `tests` gate. No witness
drives it. Replacing its condition with `False` survives the default suite,
per the item. The next step reached enters `critic_cell` at
`saffron/cell/session.py:1365-1376`, and `gates["tests"]` at `:1382` is read
inside it. The mutant also survived four test files at
base here: `tests/test_session.py`, `tests/test_probe_check.py`,
`tests/test_corpus.py` and `tests/test_review.py`.

## Problem

Make one rule decide where a probe applies, and refuse an empty `test_paths`
rather than read it as "nothing is a test".

1. **One refusal, in `saffron/probe.py`.** Write one function there that
   answers why a probe on a given file is refused, or that it is not. It
   refuses, in this order: a path `_repo_relative` returns `None` for, then
   an empty `test_paths`, then a path `scope.matches` matches against any
   declared glob. The empty case's reason is `revert`'s summary, word for
   word. `_under` goes.
2. **`check_probe` asks it.** It replaces the two refusals at
   `saffron/probe.py:169-180`, before `mutate`, with the baseline record
   still attached. `test_paths` keeps no default
   (`tests/test_probe_check.py:309-314` pins that).
3. **The host asks it before any cell.** `_declared_test_path` goes. The
   loop at `saffron/cell/session.py:1328-1340` asks the new function about
   each distinct probe and records each refusal `unproven` with its reason.
   The `tests` gate branch at `:1343` comes after it, unchanged. The call at
   `:1398` passes the `test_paths` the function received (`:1262`), which the
   caller fills from `policy.integrity.test_paths` (`:2379`).
4. **The driver moves to globs.** `TEST_PATHS` becomes this repo's declared
   globs, and its docstring says that `check_probe` matches globs now.

## Out of scope

- Item b-e403c1, the `probes.json` entry shape written twice. It edits the
  same three source files and waits on this spec.
- Item b-ce93aa, the cell-marked test of the probe cell's environment.
- Item b-98dc4d, checking logic this repo keeps under `tests/`.
- A repo whose policy declares a bare `tests`. That is a misdeclared glob for
  `revert` and for the probe alike, and this spec makes them agree.
- `DESIGN.md` §5.5.1 (`:1071`) and `CONTEXT.md`'s *vacuity probe* entry
  (`:355`). Each says every probe off a test path reaches a cell, and neither
  names the empty `test_paths` refusal. Both are protected, so backlog item
  b-5fa523 corrects them by hand.

## Notes for the agent

**Which criteria pin existing text.** Criteria 1 and 2 edit existing code
and declare mutants on lines that stay. Criterion 1's mutant is in
`_repo_relative` (`saffron/probe.py:127-137`), which the new function keeps
as its normaliser. Criterion 2's mutant is item b-a70ec1's own branch.
Criterion 3 pins a new value, so it declares a witness and no mutant, and
`witness` reports `skip` for it. Criterion 4 is `preserves`. It fails if the
host keeps handing `check_probe` an empty `test_paths`, because the empty
refusal then answers every probe in the cell. That was measured on a
prototype of this change.

**Why criterion 2 drives three reviews in one witness.** The no-`tests`-gate
review alone passes at base, because that branch already exists. `revert`
blocks a new test that passes with the source reverted. The other two
reviews fail at base, since the host asks for a cell there. So the witness
fails reverted, and the mutant still kills it through the first review. Each
of the three was measured against this checkout's base on 2026-09-21.

**Name the new function with care.** The line `with mutate(probe) as refusal:`
(`saffron/probe.py:190`) binds `refusal` as a local of `check_probe`. A
module function of that name is then unbound in `check_probe`, and a
prototype raised `UnboundLocalError` there.

**Keep a test-path reason that names the file and says "test".**
`tests/test_probe_check.py:292` asserts `"test" in got.reason`, and
`tests/test_session.py:2882` asserts `"spec/a.py" in entry["reason"]`.

**Move `tests/test_probe_check.py` to globs.** Its `TEST_PATHS`
(`tests/test_probe_check.py:110`) is a prefix.
So are the two literal arguments at `tests/test_probe_check.py:67` and
`tests/test_probe_check.py:84`. As globs they match nothing beneath the
directory. Three tests then fail. They are
`test_a_verdict_reached_without_a_suite_records_no_count`
(`tests/test_probe_check.py:79-88`),
`test_a_probe_aimed_at_a_test_file_is_refused_before_it_is_applied`
(`tests/test_probe_check.py:274`) and
`test_a_probe_refused_before_mutation_still_records_the_baseline_in_hand`
(`tests/test_probe_check.py:428`). Change the three values to the glob and
rename no test.

**The host witness.** Put it in `tests/test_session.py` and drive each review
through `_drive` (`:966`), each into its own subdirectory of `tmp_path`, as
`:5856` does. Reuse `_stub_probe_gates` (`:2677`), `_PROBE_POLICY` (`:2707`)
and `_adequacy_finding` (`:2710`). Spy on `session.critic_cell` by caller, as
`test_a_probe_cell_that_never_comes_up_leaves_the_findings_as_filed` does
with `_refuse` (`:3021-3025`). Record each call from `_probe_adequacy` and
raise `runtime.CellRuntimeError`, then assert none was recorded. Also assert that
`cell.mutated` stays empty and each entry's reason. The no-`tests`-gate repo
declares a `lint` gate and `integrity.test_paths`, so the `tests` role is
what it lacks.

**The driver witness.** Compare `TEST_PATHS` with
`load_policy(REPO)[0].integrity.test_paths`, loading the driver with
`_load_driver` (`tests/test_corpus.py:432`). One is a tuple and the other a
list, so compare them as lists.

**Three sentences name the prefix rule this removes.** Rewrite each: the
docstring at `tests/test_session.py:2862-2865`, the "raw prefix test" in
`_repo_relative`'s docstring (`saffron/probe.py:130-133`), and the comment on
`saffron/cell/session.py:1398`.

**Import anything new inside the test body.** A module-scope import of a new
name turns `revert`'s reverted run into a collection error. `revert` reads that
as `skip`.

**Each witness is a plain `def`, never parametrised.** Loop inside it.

**The wrong implementations each witness must fail.** Each of these failed
its witness on the prototype.

- Criterion 1: keeping `_under` beside the glob, matching the raw path
  unnormalised, and `fnmatch` in place of `scope.matches`.
  `saffron/report/pr_body.py:395` uses `fnmatch` over `test_paths`. Measured
  at base: under `tests/*.py`, `scope.matches` rejects `tests/sub/x.py` and
  `fnmatch` accepts it.
- Criterion 2: a host-side glob check that sends a path outside the tree to
  the cell. Also an empty list refused only inside the cell, which is the
  base's behaviour and failed the reverted run.
- Criterion 4: the host still passing an empty `test_paths` to
  `check_probe`.

**`size` blocks at 300 changed lines here.** `saffron/cell/**` is in
`.saffron/policy.yaml`'s `elevate_on`. A prototype of this change measured 209
changed lines across the six files in `touches`. Keep each rewritten comment
to one or two lines.

**Stay out of four files `SA-0118` edits.** They are `saffron/cell/worktree.py`,
`tests/test_worktree.py`, `tests/test_package.py` and `harness/recovery.py`.
All four are in `forbidden`.

Commit after each coherent step. Uncommitted work dies with the cell.
