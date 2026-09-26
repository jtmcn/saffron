---
id: SA-0178
title: Only REVIEW's adequacy findings can be probed, because the probe call picks its own targets
type: feature
priority: 1
depends_on: [SA-0159, SA-0138]
touches:
  - saffron/cell/session.py
  - tests/test_probe_findings.py
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
  - saffron/task.py
  - saffron/cli.py
  - saffron/batch.py
  - saffron/scheduler.py
  - saffron/intake.py
  - saffron/events.py
  - saffron/probe.py
  - saffron/end_review.py
  - saffron/ledger.py
  - saffron/qualify.py
  - saffron/record/**
  - saffron/repos/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/agents/**
  - saffron/cell/worktree.py
  - saffron/cell/runtime.py
  - saffron/cell/runtimes/**
  - tests/test_session.py
  - tests/test_probe_cell.py
  - tests/test_probe_check.py
  - tests/test_review.py
  - tests/test_findings.py
  - tests/test_end_review.py
  - tests/test_batch.py
  - tests/test_ledger.py
  - tests/test_ledger_fold_task.py
budget_usd: 18
max_attempts: 3
max_turns: 100
estimated_lines: 220
acceptance:
  - claim: >-
      `session.probe_findings(targets, *, spec, repo, mirror, gates_dir,
      thread_env, test_paths, base_results, gates, patch, created, note)`
      probes the findings in `targets`, whatever their lens and whether or
      not each is anchored. It asks each distinct `review.probe_key` once,
      the refused probes first, and asks the rest in one Gate-only cell. It
      decides every finding that carries a probe in place, by
      `review.apply_probe_verdict`, and returns one entry per distinct
      edit. `_probe_adequacy` keeps its signature and hands it
      `review.adequacy_probes(reviews)`. The witness drives `spec`,
      `standards` and `adequacy` targets, an unanchored target, two targets
      sharing one probe, a refused probe, and `survived`, `killed` and
      `unproven`. Through `_probe_adequacy` it drives an anchored `spec`
      finding with a probe, an anchored and an unanchored adequacy finding with a probe,
      and an adequacy finding with none.
    witness: tests/test_probe_findings.py::test_any_lenses_findings_are_probed_once_per_edit_and_decided_in_place
    mutant:
      file: saffron/phases/review.py
      find: if f.lens == "adequacy" and f.anchored and f.probe is not None
      replace: if f.probe is not None
  - claim: >-
      REVIEW still probes each anchored adequacy finding once per distinct
      edit, in one suite run.
    witness: tests/test_session.py::test_two_findings_naming_one_probe_are_decided_by_a_single_suite_run
    preserves: true
  - claim: >-
      REVIEW still enters no probe cell when no probe can be answered.
    witness: tests/test_session.py::test_a_probed_review_no_probe_cell_could_answer_enters_none
    preserves: true
---

## Context

Backlog item **b-792ab2**, step 4 of its Done. It cites `DESIGN.md` §4.1
and §5.5. ADR 7
(`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md`)
decides a stack batch. Section 2 of
`docs/superpowers/specs/2026-09-23-stack-batch-design.md`, "Qualification is
host code", is the design. ADR 3
(`docs/adr/0003-a-test-is-judged-by-an-edit-chosen-to-break-it.md`) decides
what a probe's verdict means.

**Step 4 is four specs.** This spec lets the host probe any findings, not
REVIEW's adequacy findings alone. `SA-0179` adds the `qualifications`
table and its write. `SA-0180` qualifies each layer's end-review findings
in `saffron/qualify.py`, and calls this spec's function for the ones that
carry a probe. `SA-0147` adds each layer's in-cell concerns and the join
lens's findings. The four were one spec, `SA-0147`, until its cell ended
`PLAN_REJECTED` on 2026-09-26. Its plan priced itself at 5800 changed
tokens, and `saffron/ledger.py` and `saffron/cell/session.py` are in
`elevate_on`, so `size` blocked it.

**What the tree base holds.** Both parents are merged at `eb7b7d37` and
retired to `done/`, where every line below was read.

**Probing today.** `session._probe_adequacy` probes REVIEW's anchored
adequacy findings (`saffron/cell/session.py:1291-1449`). Its twelve
parameters are keyword-only (`:1291-1305`). Its one use of `reviews` is
the line that picks its targets, `targets = review.adequacy_probes(reviews)`
(`:1320`). `adequacy_probes` keeps each finding whose lens is `adequacy`,
that is anchored and that carries a probe (`saffron/phases/review.py:555-565`).
From there the body reads `targets` alone. It asks each distinct
`review.probe_key` once (`saffron/cell/session.py:1328`). The probes
`probe.probe_refusal` refuses are decided first, and no cell is entered
for them (`:1357-1368`). It enters a Gate-only cell through `critic_cell`
with `network=None` and `env=dict(thread_env)` (`:1389-1403`). It runs the
baseline `tests` gate once and `probe.check_probe` per probe
(`:1410-1448`). `decide` calls `review.apply_probe_verdict` on every
finding that named the probe (`:1332-1335`), and adds one entry
(`:1336-1350`). `apply_probe_verdict` sets `probe_verdict`, makes a
`survived` finding a `blocker` and a `killed` one a `note`
(`saffron/phases/review.py:585-595`).

**Its callers.** REVIEW calls it with every keyword
(`saffron/cell/session.py:2590-2603`). `tests/test_probe_cell.py:117-132`
calls it by name in a cell. Two tests in `tests/test_session.py` find it on
the stack by name before refusing a cell (`:3546`, `:3936`). So it stays a
function of its own, with its signature.

## Problem

Rename `_probe_adequacy` to `probe_findings` in place, in
`saffron/cell/session.py`. Give it a first positional parameter `targets`,
a list of `Finding`, each carrying a probe. Keep the other parameters
keyword-only and drop `reviews`. Delete the line that picks the targets,
so the body reads the parameter.

Beside it, add a thin `_probe_adequacy` with the old signature. It returns
`probe_findings(review.adequacy_probes(reviews), ...)`, every other keyword
passed as given. Do not copy the body, since `size` blocks at 3000 tokens
here. REVIEW's call site stays as it is.

Update the renamed function's docstring. It probes the findings it is
given, and names no lens. Rewrite the comment on its assertion that
each target carries a probe (`saffron/cell/session.py:1327`). It names
`adequacy_probes`, which no longer picks the targets. Say instead that
every caller filters first.

## Out of scope

- **Qualifying an end review's findings.** `SA-0180` calls
  `probe_findings` from `saffron/qualify.py`, and `SA-0147` extends it.
- **Recording what the host decided.** `SA-0179` adds the table.
- **What a probe's verdict means.** `probe.check_probe` and
  `probe.added_tests` decide it, and neither changes here.
- **A target with no probe.** `review.distinct_probes` asserts each target
  carries one (`saffron/phases/review.py:574-582`), and the body does the
  same (`saffron/cell/session.py:1327`). Every caller filters first.

## Notes for the agent

**Criterion 1 is mostly new code, and its wrapper half is an edit.** No
text at the tree base names `probe_findings`. The wrapper still selects
through `review.adequacy_probes`, whose predicate exists at the tree base
(`saffron/phases/review.py:564`). So criterion 1 declares a mutant there.
It drops the lens and anchoring tests from that predicate, and the
witness's `_probe_adequacy` call kills it, since x1 is then mutated. Criteria 2 and 3 are `preserves` and name tests
that pass at the tree base. They hold the rename to REVIEW's behaviour.

**Reach the new name inside the test body.** Import `session` at module
scope, since it exists at the tree base. Call `session.probe_findings`
inside the test, so the reverted run fails with `AttributeError` rather
than failing to collect.

**The witness** runs no cell. With `monkeypatch`, it replaces three names.

- `saffron.cell.session.critic_cell` becomes a context manager that
  records its keywords and yields `"saffron-gate-probe"`.
- `saffron.gates.runner.run_gate` returns the next of a list of
  `GateResult`s, whatever it is asked.
- `saffron.cell.worktree.source_mutated` becomes a context manager that
  records the probe's `file` and yields `None`.

Every `tests` result the stub returns collects `t.py::test_old` and
`t.py::test_added`. The first, the probe cell's baseline, passes.
`base_results` is one `tests` result collecting `t.py::test_old` alone, so
`t.py::test_added` is the one test the diff adds. `test_paths` is
`["tests/**"]`, `gates` is `{"tests": <any path>}`, `patch` is a string,
and `thread_env` is a one-key dict.

The first call is `probe_findings` over five findings, in this order. Each
is on `src/x.py` line 1.

| claim | lens | severity | anchored | probe `file`, `find`, `replace` |
|---|---|---|---|---|
| s1 | `spec` | concern | yes | `src/a.py`, `a`, `A` |
| s2 | `standards` | concern | yes | s1's probe |
| s3 | `spec` | blocker | no | `src/b.py`, `b`, `B` |
| s4 | `adequacy` | concern | yes | `tests/test_x.py`, `t`, `T` |
| s5 | `standards` | note | yes | `src/c.py`, `c`, `C` |

The stub's results after the baseline are a pass, a failure of
`t.py::test_added`, and a pass. The witness asserts these.

- The mutated files are `src/a.py`, `src/b.py` and `src/c.py`, in order.
- The entries' probe files are `tests/test_x.py`, `src/a.py`, `src/b.py`
  and `src/c.py`. Their verdicts are `unproven`, `survived`, `killed` and
  `survived`.
- The `src/a.py` entry's findings name the lenses `spec` and `standards`.
- The five findings end `blocker`, `blocker`, `note`, `concern` and
  `blocker`, with the verdicts `survived`, `survived`, `killed`,
  `unproven` and `survived`.
- `critic_cell` was entered once, with `network` `None`, the patch, and
  `env` equal to `thread_env`.

The second call is `_probe_adequacy`, with two reviews. The `spec` review
holds x1, an anchored concern with a probe on `src/e.py`. The `adequacy` review holds
a1, anchored with a probe on `src/d.py`, then a2, unanchored with x1's
probe, then a3, anchored with no probe. The stub's results are a baseline
pass and a pass. The witness asserts that only `src/d.py` was mutated,
and that the one entry is `src/d.py`'s. The verdicts of x1, a1, a2 and a3
are `None`, `survived`, `None` and `None`.

These fail it, each measured.

- `probe_findings` that keeps only its `adequacy` targets
- `probe_findings` that keeps only its anchored targets
- `_probe_adequacy` that hands over every finding with a probe
- `_probe_adequacy` that hands over unanchored adequacy findings too
- `_probe_adequacy` that hands over every anchored finding with a
  probe, whatever its lens
- one question per finding rather than per distinct edit
- the declared mutant, applied to `review.adequacy_probes`

**How the list was measured.** A throwaway test ran on 2026-09-26 at
`eb7b7d37`. It built `probe_findings` and the wrapper from
`_probe_adequacy`'s own source by the edits the Problem names, and each
wrong version by one edit more. The mutant was applied to
`adequacy_probes`'s own source. The right build passed every assertion
above, and each wrong version failed it.

**What the witness leaves undriven.** The body past the target line is
REVIEW's, unchanged. Criteria 2 and 3 hold it, with the other probe tests
in `tests/test_session.py`. `tests/test_probe_cell.py` runs it in a cell.

**The `prose` gate** counts every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense, a hedge or
a sentence over 25 words. Keep each docstring within ten lines.

**Commit as each witness passes**, before the full suite runs.

**Size.** `saffron/cell/session.py` is in `elevate_on`, so `size` blocks at
the `feature` ceiling of 3000 tokens (`saffron/gates/core/size.py:26`). The
rename, the target line and the wrapper come to about 40 changed lines in
`session.py`. A prototype of the rename alone measured 56 tokens with
`size_gate`, on 2026-09-23. The witness ran to about 100 lines unformatted.
Formatted, it comes to about 140 lines at 3.4 tokens a line. That is about
630 tokens. Sibling cells landed at 1.4 to 1.6 times their authors'
estimates, so about 880 tokens, 29% of the ceiling.
