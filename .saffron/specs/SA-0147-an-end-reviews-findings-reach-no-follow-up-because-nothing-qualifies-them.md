---
id: SA-0147
title: The join lens's findings and each layer's own REVIEW concerns reach no follow-up, because qualification reads only the layers' end reviews
type: feature
priority: 1
depends_on: [SA-0180]
touches:
  - saffron/qualify.py
  - tests/test_qualify.py
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
  - saffron/record/**
  - saffron/repos/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/agents/**
  - saffron/cell/**
  - tests/test_session.py
  - tests/test_probe_cell.py
  - tests/test_probe_check.py
  - tests/test_review.py
  - tests/test_findings.py
  - tests/test_end_review.py
  - tests/test_batch.py
  - tests/test_ledger.py
  - tests/test_ledger_fold_task.py
  - tests/test_probe_findings.py
  - tests/test_ledger_qualifications.py
budget_usd: 18
max_attempts: 3
max_turns: 100
estimated_lines: 275
pending_symbols:
  - saffron/qualify.py::qualify
  - saffron/qualify.py::groups
  - saffron/qualify.py::pool
acceptance:
  - claim: >-
      `qualify` adds each layer's in-cell concerns to its inputs, after its
      end-review findings, in the order recorded. An in-cell concern is a
      finding of a lens in `review.LENSES`, of severity `concern`. An
      anchored in-cell `adequacy` concern goes to the pool as
      `unverified`, since its REVIEW probe did not survive. Any other
      in-cell concern is decided as an end-review finding is, under its
      own layer, and a layer the end review did not reach keeps its
      in-cell concerns as its only inputs. The witness drives an in-cell
      correctness concern that qualifies, an in-cell adequacy concern, an
      in-cell adequacy note and correctness blocker, a task that also
      holds the join's and the end review's recorded copies, and an
      unreached layer with an in-cell concern.
    witness: tests/test_qualify.py::test_a_layers_own_review_concerns_follow_its_end_review_findings
  - claim: >-
      With a `join` and at least one layer, `qualify.qualify(ledger,
      layers, join, ...)` walks the join lens's findings first, then each
      layer. A join finding is anchored against `<bottom head>^..<top
      head>`, reading cited lines at the top head, and belongs to the top
      layer. It is decided by the same rule as a layer's end-review
      finding. A `RuntimeError` from a probe call, the join's or a
      layer's, sends each finding of that call to the pool as
      `unverified`, with a reason that carries the message, and the walk
      goes on. A join finding and a top-layer finding on one file share
      one group. The witness drives a join finding that qualifies on a
      file the top layer also qualifies, one left
      unanchored because its file changed only below the bottom layer, one
      whose probe call raises, and a second call of the helper in which the
      top layer's probe call raises as well.
    witness: tests/test_qualify.py::test_the_join_is_walked_first_over_the_stack_and_belongs_to_the_top_layer
  - claim: >-
      The join's anchored findings with a probe go to one
      `session.probe_findings` call of their own, made before any layer's.
      Its `CellSpec` has as `base_sha` the full sha of `<bottom head>^`,
      and no `stacked_on`. Its `spec_id` and `branch` are the top layer's,
      and its patch is the join's diff. `base_results` is
      `ledger.baseline_results` of the bottom layer's task's run. `repo`,
      `mirror`, `gates_dir`, `thread_env`, `test_paths`, `gates`, `created`
      and `note` pass through as given. The witness drives a two-layer
      stack whose layers' runs differ in their baselines.
    witness: tests/test_qualify.py::test_the_joins_probes_run_on_the_stack_counted_from_the_bottom_run
  - claim: >-
      The join's findings become `qualification` facts under the top
      layer's task, numbered from 1, before that layer's end-review
      findings and its in-cell concerns. The bottom layer's facts are
      numbered as before.
    witness: tests/test_qualify.py::test_the_joins_qualifications_come_first_under_the_top_layer
---

## Context

Backlog item **b-792ab2**, step 4 of its Done. It cites `DESIGN.md` §4.1
and §5.5. ADR 7
(`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md`)
decides a stack batch. Section 2 of
`docs/superpowers/specs/2026-09-23-stack-batch-design.md`, "Qualification is
host code", is the design. ADR 3
(`docs/adr/0003-a-test-is-judged-by-an-edit-chosen-to-break-it.md`) decides
what a probe's verdict means. Only a failure of a test the diff adds kills
a probe (`:58-59`).

A stack batch runs the queued specs into one pull request stack. Each task
that reaches `READY_FOR_REVIEW` is a **layer**. Once the last queued task
settles, one **end review** reads the stack. The Spec and Standards
end-review lenses read each layer, and the join lens reads the stack. ADR 7
says the host decides which findings qualify, and a qualified finding feeds
a follow-up spec. Its entry for principle 15 says a finding feeds one only
once the host anchors it and runs any probe it carries. Its entry for
principle 28 says one rule serves every producer, and a finding with no
probe still reaches a follow-up.

**Step 4 is four specs, and this is the last.** `SA-0178` lets the host
probe any findings, with `session.probe_findings`. `SA-0179` adds the
`qualifications` table and `Ledger.record_qualification`. `SA-0180`
qualifies each layer's end-review findings. This spec adds each layer's
in-cell REVIEW concerns and the join lens's findings to the walk. The four were one spec, this one, until its cell ended
`PLAN_REJECTED` on 2026-09-26. Its plan priced itself at 5800 changed
tokens, and `size` blocked it at `elevated`.

`SA-0161` writes a follow-up spec from each group `qualify` returns, and
`SA-0165` wires that writer into `saffron batch --stack`.

**What the tree base holds.** This spec's tree base is `SA-0180`'s head.
Only `depends_on[0]` stacks (`saffron/task.py:165-166`, `:213`), and the
chain `SA-0178`, `SA-0179`, `SA-0180` is below it. Every other spec named
here is merged at `eb7b7d37`, where every line number below was read. The
chain's names are cited by symbol.

- `SA-0180` adds `saffron/qualify.py`. `qualify(ledger, layers, join, *,
  mirror, repo, gates_dir, thread_env, test_paths, gates, created, note)`
  walks each layer's end-review findings, anchored over
  `<head>^..<head>`. It probes the anchored ones that carry a probe,
  in one `session.probe_findings` call per layer. It groups what
  qualifies by layer and file, and records each finding with
  `ledger.record_qualification`. A `join` that is not `None` raises
  `ValueError`. A raise from the probe call propagates. Its per-layer walk
  is one helper. It takes the range's base and head, the inputs, the task
  to record under, and the run the probes count from. It returns its
  decided findings in order, and `qualify` groups them once over the
  whole walk.
- `SA-0180`'s `tests/test_qualify.py` builds a two-layer stack in one
  helper, and keeps the layers' expected groups, pool and rows as module
  constants. Its helper already builds the join lens's findings j1, j2
  and j3, and records their copies under the top layer's task. It
  records `TE-1`'s Spec findings c-a, c-m and c-c as copies too, and no
  in-cell finding.
- `SA-0154`'s `end_review.run_end_review` returns a frozen `StackReview`
  (`saffron/end_review.py:496-502`). Its `layers` is the `LayerReview`
  list, top down, and its `join` is the join lens's `LensReview` or
  `None`. It runs the join first (`:530`, `:546`). The join's findings are
  recorded with `record_findings` under the top layer's task (`:485`),
  before that layer's own end-review findings. The join lens keeps the
  default report model, so no join finding carries a probe yet. The rule
  below still covers one, so a later model needs no change here.
- `SA-0146`'s `end_review.layer_fields(ledger, task_key)` returns the
  layer's `spec_id`, `branch` and `head`, its `pushed_sha`
  (`saffron/end_review.py:101-133`).

**An in-cell adequacy concern's probe did not survive.** REVIEW decides
each anchored adequacy finding from its probe, by the rule above. So an
adequacy `concern` left at `READY_FOR_REVIEW` carried no probe that
survived. The `findings` table keeps no probe (`saffron/ledger.py:163-175`),
so the host cannot run one again. ADR 7 qualifies a finding only once any
probe it carries survived, and principle 28 asks one rule of every
producer. So such a concern goes to the pool as `unverified`.

**Recording today.** `record_findings` numbers a task's findings
(`saffron/ledger.py:1293-1319`). `Ledger.findings(task_id)` returns a
task's rows in the order recorded (`:1340-1346`).

**A stored concern carries no verdict and no rebuttal.** REBUT rebuts
anchored blockers alone (`saffron/phases/review.py:545-552`,
`saffron/cell/session.py:2676`, `:2786-2790`). A withdrawn blocker stays
a `blocker`. So no rule here filters a concern on either field.

**What the probe call raises.** A patch that does not apply raises
`CriticPatchRejected`, a `RuntimeError` that `probe_findings` does not
catch (`saffron/cell/session.py:1028`). `CriticPatchUnrepresentable` is
one too (`:1036`), and so is `mirror.GitError`
(`saffron/repos/mirror.py:39`). A `runtime.CellRuntimeError` does not
reach the caller. The body already reads one as `unproven`, at cell entry,
at the baseline and at each probe (`saffron/cell/session.py:1404`,
`:1411`, `:1430`). A join's patch spans every layer, so it is the
likeliest not to apply.

## Problem

**Each layer's in-cell concerns, in `saffron/qualify.py`.** A layer's
inputs become its end-review findings in review order, then its in-cell
concerns. Take those in the order `Ledger.findings` returns them. Rebuild each
concern as a `Finding` with no probe. An anchored in-cell `adequacy`
concern is `unverified`, with the reason "its REVIEW probe did not
survive". An unanchored one is `unanchored`, as any unanchored finding
is. No in-cell concern is handed to the probe call.

**The join, in `saffron/qualify.py`.** Replace the `ValueError` with the
walk. When `join` is not `None` and `layers` holds at least one layer,
call `SA-0180`'s per-layer helper once for the join, before any layer:

- The range is the last layer's `<head>^` to the first layer's head, and
  `read_head` reads the first layer's head.
- The inputs are the join's findings alone, and no in-cell concerns.
- The probe call's `spec_id` and `branch` come from the first layer's
  `LayerFields`. Its `base_sha` is the range's base, resolved to a full
  sha. Pass the last layer's task's run as the helper's run the probes
  count from, so `base_results` is that run's `baseline_results`.
- Each finding is recorded under the first layer's task, and grouped or
  pooled under its key.

A `RuntimeError` from any probe call marks each finding of that call
`unverified`, and the reason carries its message. Any other raise
propagates.

In `tests/test_qualify.py`, give the helper four keywords. They say
whether to record the in-cell findings, whether to pass the join, whether
to add `TE-0`, and which commits' calls the double raises on. `TE-0` is
off unless a witness asks for it. The double records each call, then
raises. Leave `SA-0180`'s three witnesses and their constants as they
are.

## Out of scope

- **The layers' end-review findings.** `SA-0180` walks them, and nothing
  here changes how.
- **Writing follow-up specs.** `SA-0161` writes one from each group, and
  `SA-0165` wires it into `saffron batch --stack`.
- **The tree a follow-up's anchors and probe are keyed to.** It is open.
  ADR 7's Consequences lists it, and no spec in the chain answers it. ADR
  7's principle 27 holds only once one does. A later layer can move both.
- **The finishing layer.** `SA-0151` commits it, and `SA-0170` links the
  stack and marks it ready.
- **The probe call and the table.** `SA-0178` builds `probe_findings`,
  and `SA-0179` builds the `qualifications` table and its write. This
  spec edits neither file.
- **The delegate's `findings.json`.** `SA-0174` writes it from each
  layer's `qualifications` rows.
- **The base a bottom layer's probes count from.** A bottom layer's run
  took its baseline at its run's `base_sha`. When the default branch moved
  before PACKAGE, the head's parent is a later commit. A test the default
  branch added in between is then counted as one the layer adds. A probe
  only that test fails reads `killed`, and its finding is dropped. The
  join counts from the same run, so it carries the same residual. A
  stacked layer's run took its baseline at its predecessor's head, which
  is its head's parent unless a hand push moved it. How often the default
  branch adds a test during a stack batch is unmeasured.
- **The vocabulary.** `CONTEXT.md` has no entry for qualification, a
  follow-up group or the backlog pool. Backlog item b-466005 files them by
  hand.

## Notes for the agent

**Criteria 1 to 4 are new code.** No text at the tree base reads an
in-cell concern or walks the join. There `qualify` raises for a join.
So they declare a witness and no mutant, and `witness` reports `skip` for
them. With `qualify.py` reverted to the tree base, criterion 1's witness
finds no i1 or i6, and the others meet that `ValueError`.

**The arrangement is `SA-0180`'s**, with four changes. When asked, the
helper records these in-cell findings under `TE-2`, before any copy: a
correctness concern "i1" on `src/b.py:1`, an adequacy note "i3" and a
correctness blocker "i4" on `src/b.py:2`, and an adequacy concern "i6" on
`src/b.py:1`. Every witness here asks for them. The helper passes
`LensReview("join", [j1, j2, j3])` as `join` when asked. The double raises
`RuntimeError("no cell at <name>")` when `spec.base_sha` is the sha of a
commit named in its raising set. The join's range starts at `M`, which is
`H1`'s parent, so its call's `base_sha` is `M`. Last, when asked, it adds
a layer the end review did not reach, as `review_stack` leaves one
(`saffron/end_review.py:365-371`). It is `TE-0`, created after the other
two tasks, on a run with `base_sha` `A` whose `tests` result collects
`[]`. It is packaged at `M`, recorded as a layer at position 0 with no
predecessor, and holds one in-cell correctness concern "u1" on
`src/m.py:1`. Its `LayerReview` comes last, with no reviews. `qualify`
reads no position or predecessor, so neither moves a result.

**Criterion 1's witness** runs the helper with no join and with `TE-0`.
Its `groups` are `SA-0180`'s four, with i1 last in `TE-2`'s `src/b.py`
group, as a concern, and then `(TE-0, src/m.py, [u1], [concern])`. Call
the first four the in-cell groups. The pool is `SA-0180`'s, with i6
`unverified` before c-m, its reason "its REVIEW probe did not survive".
Call that the in-cell pool. `TE-2`'s rows are `SA-0180`'s twelve, then i1
and i6. `TE-1`'s are `SA-0180`'s three, and `TE-0`'s are u1 alone. These
fail it, each measured:

- in-cell concerns left out
- every in-cell finding kept, not concerns alone
- every finding of the task kept, the end-review copies included
- in-cell rows selected by excluding `spec` and `standards`, which keeps
  the join copies
- in-cell concerns walked before the end-review findings
- an in-cell adequacy concern qualified as probe-less
- in-cell concerns read only for a layer the end review reached
- a layer with no end-review findings skipped whole

**Criterion 2's witness** runs the helper with the join, raising on `M`.
`TE-0` is not in this arrangement. j1, on `src/c.py:11`, names
`beta_rate`, which the join's diff changed, and qualifies. So `groups`
opens with one `TE-2`, `src/c.py` group of j1, f6 and f4, as concern,
concern and blocker. The other three in-cell groups follow. The first two
pool entries are j2 `unanchored` and j3 `unverified`, whose reason holds
"no cell at M". The rest is the in-cell pool. It then calls the helper
again in a fresh directory, raising on `M` and `H1`. The groups are
`TE-2`'s `src/c.py` with j1 and f6, then `TE-2`'s `src/b.py` with s2 and
i1, then `TE-1`'s two. f1, f2, f3,
f4, f7, f8 and f10 are all in the pool as `unverified`, each reason
holding "no cell at H1". These fail it, each measured:

- the join anchored over the top layer's own diff
- the join anchored from the bottom layer's run base, which anchors j2
- the join left out
- the join's findings put under the bottom layer
- the join walked after the layers
- a raise that propagates
- a raise caught on the join's call alone
- a raise that stops the walk
- the helper groups per call, so the join and the top layer give two
  groups for one file

**Criterion 3's witness** runs the helper with the join, raising on `M`,
and asserts two calls. `TE-0` is not in this arrangement. The first
holds j3 alone. Its `spec.base_sha` is
`M`, with no `stacked_on`. Its `spec_id` is `TE-2`, and its `branch` is
`TE-2`'s. Its patch holds "+alpha_l2_new" and not "moved_main_only". Its
`base_results` collect `[]` and `None`, `TE-1`'s. Its eight keywords are
the objects passed, by `is`. The second call's `spec.base_sha` is `H1`.
These fail it, each measured:

- the join's tree at the top layer's parent, or at the bottom layer's
  run base
- the join's cell built from the bottom layer's fields
- the join's `base_results` from the top layer's run
- the join walked after the layers

**Criterion 4's witness** runs the helper with the join, raising on `M`.
`TE-0` is not in this arrangement.
`TE-2`'s rows are j1, j2 and j3 at positions 1 to 3. Their outcomes are
`qualified`, `unanchored` and `unverified`. Criterion 1's fourteen follow
at 4 to 17. `TE-1`'s are `SA-0180`'s three. These fail it, each measured:

- the join's findings put under the bottom layer
- the join walked after the layers
- the join left out

**How the lists were measured.** A throwaway prototype ran on 2026-09-26
at `eb7b7d37`, on the host's git 2.54. It is `SA-0180`'s, with the
in-cell concerns and the join added as the Problem says. The right build
passed all seven witnesses, and `SA-0180`'s three still passed. Each
wrong version above was made from it by one or two edits, and each
failed the witness it is listed under.
Measured on 2026-09-26 in `saffron/cell:saffron`, whose git is 2.47.3, a
`GIT_CONFIG_GLOBAL` setting `diff.context = 0` gives no context lines. An
explicit `--unified=3` overrides it, giving six context lines around a
one-line change.

**What the witnesses leave undriven.**

- A join with no layers. Walk nothing for it, as the Problem says.
- A join over a stack whose bottom layer the end review did not reach.
  The join's range then starts at that layer's head's parent, as
  `review_joins` builds it (`saffron/end_review.py:450`).
- A raise from the probe call that is not a `RuntimeError`. It
  propagates, so a wrong keyword fails loudly rather than reading
  `unverified`.
- A finding on a binary file. The patch cannot carry one, so the cell
  raises and the finding is `unverified`.

**The `prose` gate** counts every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense, a hedge
or a sentence over 25 words. Keep each docstring within ten lines.

**Commit as each witness passes**, before the full suite runs.

**Size.** No path this spec touches is in `elevate_on`, so `size` is
advisory at the `feature` ceiling of 3000 tokens
(`saffron/gates/core/size.py:26`). The prototype's change over
`SA-0180`'s, formatted with `ruff format`, measured 785 changed tokens
with `size_gate`'s own count: 245 in `qualify.py` and 540 in the tests.
Sibling cells landed at 1.4 to 1.6 times their authors' estimates, so
about 1100, 37% of the ceiling.
