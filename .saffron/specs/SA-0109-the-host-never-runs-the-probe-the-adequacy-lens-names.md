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
budget_usd: 24
max_attempts: 3
max_turns: 120
acceptance:
  - claim: >-
      An anchored adequacy finding filed as a `concern`, whose probe leaves the
      repo's `tests` gate with no new failure against that gate's own run on the
      unprobed tree, reaches REBUT as a blocker. The task ends `REBUTTING` or
      later, never `READY_FOR_REVIEW`, and `rebuttal.json` names that finding.
    witness: tests/test_session.py::test_a_concern_whose_probe_survives_is_rebutted_as_a_blocker
    mutant:
      file: saffron/probe.py
      find: "if not new:"
      replace: "if new:"
  - claim: >-
      An anchored adequacy finding filed as a `blocker`, whose probe gives the
      `tests` gate a new failure, is dropped. It is neither a blocker nor a
      concern, so a review with no other finding ends `READY_FOR_REVIEW` and no
      REBUT turn runs. `findings.json` still carries the finding with its
      verdict, and REVIEW's line for the adequacy lens counts it as killed.
    witness: tests/test_session.py::test_a_blocker_whose_probe_is_killed_does_not_reach_rebut
    mutant:
      file: saffron/probe.py
      find: "new = subtract_baseline([mutated], [baseline])"
      replace: "new = []"
  - claim: >-
      A probe that cannot be applied leaves its finding at the severity the
      lens filed. `probes.json` in the task directory records the probe, the
      verdict `unproven`, and the reason the mutator gave, word for word.
    witness: tests/test_session.py::test_a_probe_that_does_not_apply_leaves_its_finding_as_filed_and_says_why
    mutant:
      file: saffron/probe.py
      find: 'return ProbeResult("unproven", refusal, baseline=record)'
      replace: 'return ProbeResult("unproven", "", baseline=record)'
  - claim: >-
      A probe whose file matches one of the repo's declared
      `integrity.test_paths` globs is recorded `unproven` and never applied: the
      mutator is not entered for it. The globs are the policy's, whatever they
      say. The witness declares a test path other than `tests/**`.
    witness: tests/test_session.py::test_a_probe_on_a_declared_test_path_is_never_applied
  - claim: >-
      REBUT's blocker list shows a blocker whose probe survived with that
      probe's file, `find` and `replace`, so the implementer is shown the edit
      the tests did not notice.
    witness: tests/test_rebut.py::test_a_blocker_whose_probe_survived_names_the_probe_to_the_implementer
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
   gates, never a tool (§2.1).
3. **What the verdict decides.**
   - `survived`: the finding becomes a `blocker`, whatever the lens filed.
   - `killed`: the finding is dropped from both counts but kept in
     `findings.json` with its verdict.
   - `unproven`: the finding stays as filed.

   `review_state` and everything after it read the decided findings, so the
   ledger rows, `findings.json`, the queue's concern count and REBUT's
   numbering all agree.
4. **What it records.** Write `probes.json` in the task directory: one entry
   per probe, with the probe and every `ProbeResult` field. The corpus
   driver's `_write_probes` is the precedent for the shape. REVIEW's line for
   the adequacy lens gains the survived, killed and unproven counts.

A probe on a file the policy's `integrity.test_paths` globs match is
`unproven` and is never applied. Match with `saffron.gates.core.scope.matches`
(`saffron/gates/core/scope.py:31`), the rule `revert` uses. `check_probe`'s own
`test_paths` argument compares path prefixes, and `saffron/probe.py` is
forbidden here, so the glob check happens before `check_probe` is called.

An infrastructure failure while probing is not the task's fault and not a
verdict on the lens. That covers the cell not coming up, the baseline
reporting `error`, and a failed undo raising. Every probe not yet answered is
then `unproven` with the reason, and the task continues on the findings as
filed.

## Out of scope

- Probing again after REBUT, or asking the lens for a fresh probe each round.
- Any lens prompt, including `review-adequacy.md`.
- The pull-request body's findings table (`saffron/report/pr_body.py`). A
  killed finding still renders there. File the follow-up if it matters.
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
  `saffron.probe` in a witness. Stub the runtime, `worktree.source_mutated`
  and the gate runner, the way `_stub_the_runtime`
  (`tests/test_session.py:672`) and `_drive` (`:966`) already do.
- `revert` re-runs every test you add with the source reverted and blocks any
  that pass. Import any name you add inside the test body, not at module scope.
  A module-scope import makes the reverted run a collection error, which
  `revert` reads as `skip`.
- Each witness is a plain `def`, never parametrised.
- Each witness must fail on one wrong implementation. For the survived
  witness, it is one that promotes every probed finding. For the killed
  witness, it is one that drops every probed finding. For the test-path
  witness, it is one that hard-codes `tests/`.
- A probe runs the whole suite, which takes about a minute in a cell. That
  costs wall clock, not model spend, and REVIEW is not gated on the spend
  ceiling (§5.5). Do not add a cap on the probe count. If you think one is
  needed, say so in your notes.
