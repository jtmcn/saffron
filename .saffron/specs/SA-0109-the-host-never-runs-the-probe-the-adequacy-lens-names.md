---
id: SA-0109
title: The host never runs the probe the adequacy lens names, so a confirmed vacuity ships as a concern
type: feature
priority: 1
depends_on: [SA-0102]
touches:
  - saffron/cell/session.py
  - saffron/phases/review.py
  - saffron/phases/rebut.py
  - saffron/agents/findings.py
  - tests/test_session.py
  - tests/test_review.py
  - tests/test_rebut.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
  - pyproject.toml
  - uv.lock
  - .saffron/**
  - ontology/**
  - tests/ontology/**
  - docs/**
  - images/**
  - harness/**
  - saffron/probe.py
  - saffron/ledger.py
  - saffron/task.py
  - saffron/batch.py
  - saffron/cli.py
  - saffron/report/**
  - saffron/gates/**
  - saffron/cell/worktree.py
  - saffron/cell/runtime.py
  - saffron/agents/prompts/**
  - tests/test_probe_check.py
  - tests/test_corpus.py
budget_usd: 26
max_attempts: 3
max_turns: 160
acceptance:
  - claim: >-
      An anchored adequacy finding filed as a `concern`, whose probe leaves the
      repo's `tests` gate with no new failure against that gate's result on the
      unprobed tree, reaches REBUT as a blocker. The task ends `REBUTTING` or
      later, never `READY_FOR_REVIEW`. When the same review also holds a
      correctness blocker with no probe, `rebuttal.json` names both, each
      under its own number.
    witness: tests/test_session.py::test_a_concern_whose_probe_survives_is_rebutted_as_a_blocker
    mutant:
      file: saffron/probe.py
      find: "if not new:"
      replace: "if new:"
  - claim: >-
      An anchored adequacy finding filed as a `blocker`, whose probe gives the
      `tests` gate a new failure, is demoted to a `note`. It is neither a
      blocker nor a concern, so a review with no other finding ends
      `READY_FOR_REVIEW` and no REBUT turn runs. `findings.json` carries the
      finding as a `note` with its `probe_verdict`, and the REVIEW line emitted
      after probing counts it as killed.
    witness: tests/test_session.py::test_a_blocker_whose_probe_is_killed_is_demoted_to_a_note
    mutant:
      file: saffron/probe.py
      find: "new = subtract_baseline([mutated], [baseline])"
      replace: "new = []"
  - claim: >-
      A probe that cannot be applied leaves its finding at the severity the
      lens filed. `probes.json` in the task directory records the probe as
      `unproven`, with the reason the mutator gave, word for word.
    witness: tests/test_session.py::test_a_probe_that_does_not_apply_leaves_its_finding_as_filed_and_says_why
    mutant:
      file: saffron/probe.py
      find: 'return ProbeResult("unproven", refusal, baseline=record)'
      replace: 'return ProbeResult("unproven", "", baseline=record)'
  - claim: >-
      `probes.json` records a probe as `unproven` when its file, once
      normalised, matches one of the repo's declared `integrity.test_paths`
      globs, and the mutator is never entered for it. The globs are the
      policy's, whatever they say. The witness declares a test path other than
      `tests/**`, and spells one probe's file with a leading `./`.
    witness: tests/test_session.py::test_a_probe_on_a_declared_test_path_is_recorded_unproven_and_never_applied
  - claim: >-
      REBUT's blocker list shows a blocker whose probe survived with that
      probe's file, `find` and `replace`, so the implementer is shown the edit
      the tests did not notice. A blocker whose probe was `unproven` is listed
      without its probe.
    witness: tests/test_rebut.py::test_a_blocker_whose_probe_survived_names_the_probe_to_the_implementer
  - claim: >-
      A probe whose undo raises `CellRuntimeError` does not end the task. That
      probe and every later one are recorded `unproven` in `probes.json` with
      the error as the reason, and the mutator is never entered for a later
      one. Verdicts given before the raise stand. The task reaches the state
      those verdicts, and the other findings as filed, give it.
    witness: tests/test_session.py::test_a_probe_that_raises_leaves_the_findings_as_filed
  - claim: >-
      A blocker from a lens that carries no probe still routes to REBUT
      exactly as it does today.
    witness: tests/test_session.py::test_a_rebuttal_that_claims_a_fix_and_commits_nothing_stops_at_rebutting
    preserves: true
---

## Context

Backlog item **117**, found running the spec loop over stack #251 on
2026-09-14. Tier 1 in `docs/backlog/PRIORITY.md`.

The adequacy lens must attach a `probe` to every finding. The schema is
`_ReportedWithProbe` (`saffron/phases/review.py:67`), and the anchored `Finding`
keeps the probe (`saffron/agents/findings.py:41`). No production code reads it.
REVIEW's result goes straight from `review.run_review`
(`saffron/cell/session.py:2087`) to `findings.json` (`:2135`), the ledger
(`:2143`) and `review.review_state` (`:2150`). A finding's route is decided by
the severity the lens gave it: `anchored_blockers` and `anchored_concerns`
(`saffron/phases/review.py:347`, `:357`).

The only thing that runs a probe is the lens corpus driver.
`_apply_probes` (`docs/evidence/scripts/2026-09-08-lens-corpus.py:203`) takes
the `tests` gate's baseline once in a fixture's cell. It then asks
`check_probe` about each distinct probe (`:149`), passing
`worktree.source_mutated` bound to that cell as the mutator. `check_probe` now lives in
`saffron/probe.py:148`, moved there by hand so that `saffron/` can import it.
It runs the whole suite under the probe (`:197`) and returns `survived`,
`killed` or `unproven`.

Five of stack #251's eight adequacy runs named a probe that survived at the
packaged head. Each one was a real defect that a human review round later fixed,
and each shipped as a `concern` or `note` (item 117's table).

## Problem

A probe the host could run in one suite invocation is shown to a person as a
claim. The lens's severity decides a question that running the probe would
answer, and nothing records the answer.

Build the step between REVIEW and REBUT that answers it:

1. **Where it runs.** Run it in a Gate-only cell: `critic_cell` with
   `network=None` and `env=dict(policy.thread_env)`, the way
   `_gate_cell_suite` builds its cell (`saffron/cell/session.py:1188`,
   `:1226-1238`). Enter it once the REVIEW critic cell is torn down. Never run
   it in the critic cell: running tests there is the hole `SA-0087` closed
   (`_gate_cell_suite`'s docstring, `:1201-1206`). The patch is
   `patch_to_review`, the one the lenses judged.
2. **What it runs.** Take every anchored adequacy finding that carries a probe,
   with duplicate edits applied once. Take the `tests` gate once, unprobed, in
   that cell as the baseline. Then ask `saffron.probe.check_probe` about each
   probe. Its mutator is `worktree.source_mutated` bound to the cell. Its
   tests are the repo's declared `tests` gate at `worktree.GATES_MOUNT`, run
   through `runner.run_gate` with a `CellExecutor`. Core invokes declared
   gates, never a tool (§2.1). This runs the whole suite, where item 117 asked
   for the spec's witnesses and the diff's added tests. `check_probe` runs
   the whole suite (`saffron/probe.py:197`) and is forbidden here. The whole
   suite is also what the corpus measures, so a lens's kill rate in a task
   and in the corpus mean the same thing.
3. **What the verdict decides.**
   - `survived`: the finding becomes a `blocker`, whatever the lens filed.
   - `killed`: the finding becomes a `note`, whatever the lens filed. It is
     not dropped. `check_probe` cannot tell a test doing its job from a probe
     that crashed the program at runtime (`saffron/probe.py:13-18`), so a
     person still sees the finding.
   - `unproven`: the finding stays as filed.

   The field is `probe_verdict`, never `verdict`. `CONTEXT.md` defines
   *Verdict* as the critic's own at REBUT, and the ledger's `verdict` column
   holds that one (`saffron/ledger.py:781`). `review_state` and everything
   after it read the decided findings, so the ledger rows, `findings.json`,
   the queue's concern count and REBUT's numbering all agree.
4. **What it records.** Write `probes.json` in the task directory: one entry
   per probe, with the probe and every `ProbeResult` field. Each entry also
   names the findings it decided, by lens, file and line. It carries the
   severity each lens filed, which no other record keeps. The
   corpus driver's `_write_probes` is the precedent for the shape, but its
   `verdict` key is `probe_verdict` here. `run_review`
   emits each lens's line inside the critic cell
   (`saffron/phases/review.py:319-327`). So emit one more REVIEW line after
   probing, with the survived, killed and unproven counts. Leave `_describe`
   where it is.

A probe on a test file is `unproven` and is never applied. The host first
normalises the model-authored path with `posixpath.normpath` and refuses an
absolute path or one that escapes the tree. It then matches the result against
the policy's `integrity.test_paths` globs with
`saffron.gates.core.scope.matches` (`saffron/gates/core/scope.py:31`), the
rule `revert` uses. `check_probe`'s own `test_paths` compares path prefixes,
and `saffron/probe.py` is forbidden here. So the host does this check before
calling `check_probe`, and passes it an empty `test_paths`.

When no anchored adequacy finding carries a probe, no probe cell is entered,
no `probes.json` is written and no line is emitted. The watch golden fixture
(`tests/fixtures/watch-golden.txt:13-16`) pins REVIEW's lines for a review
with no findings, and it is outside `touches`.

A repo that declares no `tests` gate gets no probe cell. Every probe is
`unproven` with that reason, as the corpus driver does
(`docs/evidence/scripts/2026-09-08-lens-corpus.py:244-252`).

An infrastructure failure while probing is not the task's fault and not a
verdict on the lens. That covers the cell not coming up, the baseline
reporting `error`, and a failed undo raising. Every probe not yet answered is
then `unproven` with the reason, and the task continues on the findings as
filed.

Line numbers in `session.py` were read at `0ed431e`. `SA-0102`, the parent,
edits that file, so expect them to differ. Find each site by name.

## Out of scope

- Probing again after REBUT, or asking the lens for a fresh probe each round.
- Any lens prompt, including `review-adequacy.md`.
- The pull-request body (`saffron/report/pr_body.py`), which renders a demoted
  finding as a `note` with no mark saying why. Backlog item b-7c41e0 owns it.
- The ledger schema. The findings row keeps its columns, and a killed finding's
  row is whatever `record_findings` writes for the decided finding.
- `DESIGN.md` §5.5.1 and `CONTEXT.md`'s *vacuity probe* entry, which says a
  probe is applied "never during a task". Both are protected, and backlog item
  b-f2a9d1 owns them.

## Notes for the agent

- This change is **new code**, so most criteria declare a witness and no
  mutant (§5.4.1). The three mutants pin `saffron/probe.py`, which already
  exists and which this spec forbids you to edit. They prove the witnesses reach
  the real `check_probe` rather than a copy of its rule. So never stub
  `saffron.probe` in a witness.
- Because their mutants' file is outside the diff, `revert` exempts the first
  three witnesses (`saffron/gates/core/revert.py:193-209`). Nothing but their
  shape proves they depend on the new session code. So each of the five
  new session witnesses drives a task through `_drive` (`tests/test_session.py:966`)
  and asserts on task-level output: `outcome.state`, `probes.json`,
  `findings.json`. None of them calls `check_probe` directly.
- `_drive`'s default policy declares no gates, and `_stub_the_runtime`
  (`:672`) stubs `runner.run_suite`, not `run_gate`. So these witnesses
  declare a `tests` gate and stub `run_gate` and `worktree.source_mutated`
  themselves. Put that in one shared helper, since `size` is blocking on this
  elevated diff and its ceiling is 600 lines, tests included. The helper's
  `run_gate` stub answers only calls into a `saffron-gate-` container and
  passes every other call through, as `_run_suite` routes
  (`tests/test_session.py:889-903`). IMPLEMENT's own gates reach `run_gate`
  too.
- Decide the findings before `ledger.record_findings` runs. REBUT looks each
  blocker up by object identity in `recorded` (`saffron/cell/session.py:2143`),
  so a finding copied after that write raises `KeyError` there.
- `revert` re-runs the other tests you add with the source reverted and
  blocks any that pass. Import any name you add inside the test body, not at
  module scope. A module-scope import makes the reverted run a collection
  error, which `revert` reads as `skip`.
- Each witness is a plain `def`, never parametrised.
- Each witness must fail on one wrong implementation. For the survived
  witness, it is one that promotes every probed finding, or one that loses
  or renumbers the correctness blocker beside it. For the killed witness, it
  is one that removes the finding instead of demoting it. For the test-path
  witness, it is one that hard-codes `tests/` or skips normalising. For the
  REBUT witness, it is one that shows every blocker's probe. For the raise
  witness, it is one that lets `CellRuntimeError` end the task, or one that
  catches it per probe and goes on probing. The raise witness therefore files
  two probes on different files and makes the first undo raise. A failed undo
  leaves the first edit in the tree, so a later probe runs over both edits.
- Under the criterion-1 mutant the task still reaches `REBUTTING`, because
  the correctness blocker is there. Only `rebuttal.json` holding two blockers
  kills that mutant, so assert on it.
- In production a probe runs the repo's whole suite, about a minute in a cell.
  The witnesses stub it, so they pay none of that. That
  costs wall clock, not model spend, and REVIEW is not gated on the spend
  ceiling (§5.5). Do not add a cap on the probe count. If you think one is
  needed, say so in your notes.
