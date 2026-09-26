---
id: SA-0147
title: An end review's findings reach no follow-up, because nothing anchors, probes or groups them
type: feature
priority: 1
depends_on: [SA-0159, SA-0138]
touches:
  - saffron/qualify.py
  - saffron/ledger.py
  - saffron/cell/session.py
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
budget_usd: 28
max_attempts: 3
max_turns: 160
pending_symbols:
  - saffron/qualify.py::qualify
  - saffron/qualify.py::groups
  - saffron/qualify.py::pool
acceptance:
  - claim: >-
      `qualify.qualify(ledger, layers, join, ...)` walks the join lens
      first, then each layer in the order given. A layer's inputs are its
      end-review findings in review order, then its in-cell concerns in the
      order recorded. An in-cell concern is a finding of a lens in
      `review.LENSES`, of severity `concern`. Each input is anchored by `findings.anchor` against the
      diff `<head>^..<head>` of its own layer, reading cited lines at that
      head. A join finding is anchored against `<bottom head>^..<top head>`,
      reading at the top head, and belongs to the top layer. An anchored
      in-cell `adequacy` concern goes to the pool as `unverified`, since its
      REVIEW probe did not survive. Any other anchored finding with a probe
      then takes the probe's verdict.
      `killed` drops it. `unproven`, or a `RuntimeError` from the probe
      call, sends it to the pool as `unverified`, with the reason, and the
      walk goes on. An entry's reason is matched to a finding by
      `review.probe_key`. `survived` makes it a `blocker`. An unanchored
      finding goes to the pool as `unanchored`, whatever its severity, and a
      `note` as `note`. Every other finding qualifies. `groups` holds one
      `FollowUpGroup` per layer and file, in the order its first finding
      was met. `pool` holds the rest in that order. The witness drives
      both halves of the anchoring rule, a bottom layer whose run's base is
      not its head's parent, a cited line that moved between a layer's
      parent and its head, all four probe outcomes, a refused probe, two
      findings sharing one probe, two probes differing only in `replace`, a
      `note` whose probe survives, an unanchored `note`, an in-cell
      `adequacy` concern, and one layer and one file each shared by two
      groups.
    witness: tests/test_qualify.py::test_each_end_review_finding_is_anchored_probed_and_grouped_by_layer_and_file
  - claim: >-
      `qualify` hands the anchored findings with a probe to
      `session.probe_findings`, one call per layer and one for the join,
      and no call where there are none. The `CellSpec` of each call is the
      tree the probes run on. Its `base_sha` is the full sha of the diff's
      base, it has no `stacked_on`, the `spec_id` and `branch` are the
      layer's, and the patch is the diff the findings were anchored
      against. `base_results` is `ledger.baseline_results` of the layer's
      task's run, and of the bottom layer's for the join. `repo`, `mirror`,
      `gates_dir`, `thread_env`, `test_paths`, `gates`, `created` and
      `note` pass through as given. The witness drives a stacked layer, the
      join, a layer with no probe, and run ids that differ from task ids.
    witness: tests/test_qualify.py::test_a_findings_probe_runs_in_a_gate_only_cell_on_its_own_layers_tree
  - claim: >-
      Each finding `qualify` meets becomes one `qualification` fact under
      its layer's task, numbered from 1 per task in the order met. It
      carries the finding's lens, the severity its lens filed, its file,
      line and claim, the probe's verdict or none, the outcome and the
      reason. A killed finding is recorded too. Folding the record into a
      fresh ledger whose task ids differ rebuilds the same rows. Folding it
      into the ledger that wrote them leaves them as they were.
      `fold_task` with a layer's key and no facts removes that layer's rows
      and no other.
    witness: tests/test_qualify.py::test_each_findings_qualification_is_a_fact_the_fold_rebuilds
  - claim: >-
      REVIEW still probes each anchored adequacy finding once per distinct
      edit, in one suite run.
    witness: tests/test_session.py::test_two_findings_naming_one_probe_are_decided_by_a_single_suite_run
    preserves: true
  - claim: >-
      REVIEW still enters no probe cell when no probe can be answered.
    witness: tests/test_session.py::test_a_probed_review_no_probe_cell_could_answer_enters_none
    preserves: true
  - claim: >-
      A fact kind the ledger does not place still aborts the fold.
    witness: tests/test_ledger_fold_task.py::test_a_kind_the_ledger_cannot_place_aborts_the_fold_in_either_mode
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

**This spec builds step 4 alone.** `SA-0146` builds the two lenses.
`SA-0153` runs them over a stack and returns one `LayerReview` per layer.
`SA-0154` adds the join lens and runs the whole end review. `SA-0157`
wires it into `saffron batch --stack`. This spec qualifies what they
return. `SA-0161` writes a follow-up spec from each group this spec
returns, and `SA-0165` wires that writer into `saffron batch --stack`.

**What the tree base holds.** This spec's tree base is `SA-0159`'s head.
Only `depends_on[0]` stacks (`saffron/task.py:144-147`), and the chain
`SA-0142` to `SA-0159` puts these names there. `SA-0138`, the second
entry, does not stack. It and its parent `SA-0133` are merged at
`e3020b3b`, so their code is under the chain's root. The chain's names are
cited by symbol, and every line number below was read at `e3020b3b`. No
spec from `SA-0142` to `SA-0159` touches `saffron/cell/session.py`, so its
lines stand at the tree base.

- `SA-0138` gives `_probe_adequacy` a required keyword `base_results`,
  the task's pre-turn suite. After the probe cell's own baseline run it
  computes `probe.added_tests(base_results, <that run>)` once. It passes
  that as `counted` to every `check_probe` call. A probe is then killed
  only by a failure of a test in `counted`. `added_tests` returns `None`
  when `base_results` holds no `tests` result, or one whose `collected`
  is `None`. A probe with a new failure then reads `unproven`.

- `SA-0145` writes one `stack_layers` row per layer with
  `record_stack_layer`, each row naming its predecessor.
- `SA-0146` adds `end_review.layer_fields(ledger, task_key)`. It returns
  `LayerFields`, whose `spec_id`, `branch` and `head` are the layer's
  task's own. `head` is its `pushed_sha`.
- `SA-0153` adds the frozen dataclass `end_review.LayerReview`, with
  `task_key` and `reviews`. `review_stack` returns one per layer, top
  down. A layer the end review did not reach has empty `reviews`. Each of
  the others holds the Spec review, then the Standards review. A Spec
  finding keeps the probe it carried. `review_stack` also records each
  layer's end-review findings with `record_findings` under the layer's own
  task, unanchored, after its in-cell findings.
- `SA-0154` adds the join lens and `end_review.run_end_review`. It
  returns a frozen `StackReview`. Its `layers` is the `LayerReview` list,
  top down, and its `join` is the join lens's `LensReview` or `None`.
  `SA-0157`'s `_stack_end_review` in `saffron/cli.py` is the callable
  that returns it. `qualify` takes both fields from it. `run_end_review`
  records the join's
  findings with `record_findings` under the top layer's task, before that
  layer's own end-review findings. The join lens keeps the default report
  model, so no join finding carries a probe yet. The rule below still
  covers one, so a later model needs no change here.

**Anchoring today.** `CONTEXT.md:444-450` defines **Anchored**: inside a
diff hunk, or citing a line that names an identifier the diff changed.
`findings.anchor(findings, diff, *, read_head)` applies both halves and
returns copies (`saffron/agents/findings.py:128-146`). The second half reads
the cited line through `read_head` and compares its words with every
changed line's (`:149-166`). `mirror.file_at(mirror, sha, path)` reads a
file at a sha, and returns `None` for a path the tree lacks
(`saffron/repos/mirror.py:241-268`). It raises `UnreadablePath`, a
`GitError` (`:43`), for a path it cannot read as a file (`:258-268`).

**Probing today.** `session._probe_adequacy` probes REVIEW's anchored
adequacy findings (`saffron/cell/session.py:1291-1449`). It takes them from
`review.adequacy_probes(reviews)` (`:1320`) and asks each distinct edit once.
It enters a Gate-only cell through `critic_cell` with `network=None` and the
repo's gate env (`:1391-1402`). The cell is seeded at `spec.tree_base` with
`patch` applied and committed (`:1207`, `:1217`). It runs the baseline
`tests` gate, then `probe.check_probe` per probe (`:1407-1448`). `decide` calls
`review.apply_probe_verdict` on every finding of that probe (`:1332-1335`).
So `survived` makes it a `blocker`, `killed` a `note`, and `unproven` leaves
it as filed (`saffron/phases/review.py:574-584`). A probe whose `find`
matches no line, or more than one, is `unproven` with its reason
(`saffron/cell/worktree.py:642-648`, `saffron/probe.py:206-210`). It returns
`probes.json`'s entries, each with the `probe` dumped and its `reason`
(`saffron/cell/session.py:1336-1350`, `saffron/probe.py:319-338`). The
entries are one per distinct `review.probe_key`, and the refused probes
come first (`saffron/cell/session.py:1356-1366`). So an entry's index is
not its finding's. A patch that does not apply raises
`CriticPatchRejected`, a `RuntimeError` it does not catch
(`saffron/cell/session.py:1028`). `CriticPatchUnrepresentable` is one too
(`:1036`), and so are `runtime.CellRuntimeError` and `mirror.GitError`.

**An in-cell adequacy concern's probe did not survive.** REVIEW decides
each anchored adequacy finding from its probe. `survived` makes it a
`blocker`, `killed` a `note`, and `unproven` leaves it as filed
(`saffron/phases/review.py:574-584`). So an adequacy `concern` left at
`READY_FOR_REVIEW` carried no probe that survived. The `findings` table
keeps no probe (`saffron/ledger.py:153-165`), so the host cannot run one
again. ADR 7 qualifies a finding only once any probe it carries survived,
and principle 28 asks one rule of every producer. So such a concern goes
to the pool as `unverified`.

**Recording today.** `record_findings` numbers a task's findings
(`saffron/ledger.py:1143-1169`). `record_rebuttal` sets a finding's
`verdict` and `rebuttal` (`:1171-1188`). `Ledger.findings(task_id)` returns
a task's rows in the order recorded (`:1190-1196`). Each write builds one
fact with `_build_fact` and hands it to `_commit_and_append` (`:372-404`).
`_apply` raises on a kind it has no branch for (`:649`). `fold_task` drops a
task's rows through `_drop_task_rows` and applies its facts again
(`:406-433`).

**A stored concern carries no verdict and no rebuttal.** REBUT rebuts
anchored blockers alone (`saffron/phases/review.py:534-541`,
`saffron/cell/session.py:2676`, `:2786-2790`). A withdrawn blocker stays
a `blocker`. So no rule here filters a concern on either field.

**A run's baseline and its names.** Each cell makes its own run
(`saffron/cell/session.py:1702`). It takes the pre-turn suite on the
task's tree base, `baseline = suite.baseline(tree)` (`:1758`), and records
each result under the run (`:1775-1776`). At `e3020b3b` the ledger keeps no
`collected` (`saffron/ledger.py:1205-1233`, `:1274-1303`). `SA-0159` keeps
it, so `ledger.baseline_results(run_id)` returns each result's `collected`
as the run recorded it. Without that, `SA-0138`'s `added_tests` would read
every probe with a new failure `unproven`, and none `killed`.

**The fact kind is added by hand before this spec is committed.** A cell
cannot add it, because `CONTEXT.md` is protected. The operator adds
`qualification` to `KINDS` in `saffron/record/contract.py` and to
`ontology/factory.ttl`, and renders `CONTEXT.md`, as `8a41411c` did for
`end_review`. Nothing places it at the tree base.

## Problem

Build three things.

1. **The probe call, for any findings.** The new name is
   `probe_findings(targets, *, spec, repo, mirror, gates_dir, thread_env,
   test_paths, gates, patch, base_results, created, note)`. Rename
   `SA-0138`'s `def _probe_adequacy` to it in place, in
   `saffron/cell/session.py`. Replace its line that selects
   adequacy findings with the `targets` parameter. Beside it, add a thin
   `_probe_adequacy` with the old signature that calls `probe_findings`
   with `review.adequacy_probes(reviews)`. Do not copy the body, since
   `size` blocks at 3000 tokens here. Two tests find
   `_probe_adequacy` on the stack by name (`tests/test_session.py:3543`,
   `:3933`), so it stays a function of its own.
2. **The record of each outcome.** Add `qualifications` to `SCHEMA` in
   `saffron/ledger.py`, with no reference to another table:

   | column | type |
   |---|---|
   | `task_key` | `TEXT NOT NULL` |
   | `position` | `INTEGER NOT NULL` |
   | `lens` | `TEXT NOT NULL` |
   | `severity` | `TEXT NOT NULL` |
   | `file` | `TEXT NOT NULL` |
   | `line` | `INTEGER` |
   | `claim` | `TEXT NOT NULL` |
   | `probe_verdict` | `TEXT` |
   | `outcome` | `TEXT NOT NULL` |
   | `reason` | `TEXT NOT NULL` |

   Its primary key is `(task_key, position)`. The row carries the finding
   itself, so it reads alone. Add
   `Ledger.record_qualification(task_id, *, finding, filed, outcome,
   reason)`. It builds one `qualification` fact under the task's key and
   writes it through `_commit_and_append`. `position` is one more than the
   task's rows so far. `severity` is `filed`, and `probe_verdict` is the
   finding's own. `_apply` places the fact as one row, `task_key` from the
   fact. `_drop_task_rows` deletes the key's rows. `outcome` is one of
   `qualified`, `killed`, `unverified`, `unanchored` and `note`. `reason`
   is empty except for `unverified`.
3. **Qualification.** Add `saffron/qualify.py` with three frozen
   dataclasses. `Qualified` has `task_key`, `finding`, `outcome` and
   `reason`. `FollowUpGroup` has `task_key`, `file` and `findings`, a
   tuple. `Qualification` has `groups` and `pool`, two lists. Add
   `qualify(ledger, layers, join, *, mirror, repo, gates_dir, thread_env,
   test_paths, gates, created, note)`. `layers` is the `LayerReview` list,
   top down, and `join` is a `LensReview` or `None`. For the join first,
   when there is one and at least one layer, then for each layer in order:
   - Build the diff, `git diff` with `DIFF_FLAGS` over the range in
     `mirror`. A layer's range is `<head>^..<head>`. The join's is the
     last layer's `<head>^` to the first layer's head.
   - Anchor the inputs with `findings.anchor`. `read_head` reads the
     range's head through `mirror.file_at`, and `GitError` reads as
     `None`.
   - When any anchored finding carries a probe, hand all such findings to
     one call of `session.probe_findings`. Its `spec` is a
     `CellSpec` whose `base_sha` is the range's base resolved to a full
     sha. `spec_id` and `branch` come from the layer's `LayerFields`, the
     first layer's for the join. `patch` is the diff. `base_results` is
     `ledger.baseline_results` of the layer's task's run, the last layer's
     for the join. A `RuntimeError` marks each of those findings
     `unverified`, and the reason carries its message. Any other raise
     propagates. Otherwise an `unproven` finding's reason is the entry
     whose `probe` has its `review.probe_key`.
   - An anchored in-cell `adequacy` concern is `unverified`, with the
     reason "its REVIEW probe did not survive". An unanchored one is
     `unanchored`, as any unanchored finding is.
   - Decide each finding in the order of the inputs, and record it with
     `record_qualification` under the layer's task. The join's go under
     the first layer's task. Capture each severity before the probe call,
     since the call promotes in place.

   `qualify` returns the `Qualification`.

`ledger.py`'s module docstring counts the kinds that fold back, and that
count gains one. It also names the tables it holds, and `qualifications`
joins them.

`qualify` has no production caller until `SA-0165` binds it for
`SA-0161`'s `write_follow_ups`, which passes its groups to the spec
writer. So `qualify`, and the `groups` and `pool` fields only `SA-0161`
reads, are `pending_symbols`. The `dead` gate defers them while this spec is open
(`.saffron/gates/dead.py:4-6`).

## Out of scope

- **Writing follow-up specs.** `SA-0161` writes one from each group, and
  `SA-0165` wires it into `saffron batch --stack`.
- **The tree a follow-up's anchors and probe are keyed to.** It is open.
  ADR 7's Consequences lists it, and no spec in the chain answers it. ADR
  7's principle 27 holds only once one does. A later layer can move both.
- **The finishing layer.** `SA-0151` commits it, and `SA-0170` links the
  stack and marks it ready.
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

**Criteria 1 to 3 are new code.** No text at the tree base qualifies a
finding or places a `qualification` fact. So they declare a witness and no
mutant, and `witness` reports `skip` for them. Criteria 4 to 6 are
`preserves` and name tests that pass at the tree base. Criteria 4 and 5
hold the extraction to REVIEW's behaviour.

**Import every new name inside the test body.** `qualify`,
`record_qualification` and `probe_findings` do not exist at the tree base.
A module-scope import fails collection when the source is reverted, and
`revert` reads that as `skip`.

**Criteria 1 to 3 share one arrangement.** A helper builds it and runs
`qualify` once. Point `GIT_CONFIG_GLOBAL` at a file in `tmp_path` that sets
`diff.context = 0`, with `monkeypatch`. That file replaces the global
config, so give each commit its own identity with `-c user.email` and
`-c user.name`. Build a git repo in `tmp_path` as
the mirror. Each file below holds twelve lines, `<name>_l1` to
`<name>_l12`, except where the table says.

| commit | change |
|---|---|
| `A` | `src/a.py` of `alpha`, `src/b.py` of `beta`, `src/c.py` of `gamma` with line 10 `gamma_calls beta_rate alpha_l2_new` |
| `M` | adds `src/m.py`, one line `moved_main_only` |
| `H1` | `src/a.py` line 2 becomes `alpha_l2_new` |
| `H2` | `src/b.py` line 2 becomes `beta_rate`. `src/c.py` line 2 becomes `gamma_l2_new`, and a line `gamma_inserted` goes in after line 5, so line 10 of `H1` is line 11 of `H2` |

Build a `Ledger` with a `MemoryRecord`. Create one spare run with no task,
so run ids and task ids differ. Then create a run with `base_sha` `A` and a
task for `TE-1`, then the same for `TE-2`. Record two baseline results
under each run. The `tests` result collects `[]` for `TE-1` and
`["tests/t.py::test_old"]` for `TE-2`. The `lint` result collects `None`. Package `TE-1`
`READY_FOR_REVIEW` at `H1` and `TE-2` at `H2`. Record `TE-1` as the layer at
position 1 and `TE-2` at position 2 on it. Record these in-cell findings
first:

- `TE-1`: correctness concerns "c-a" on `src/a.py:2`, "c-m" on
  `src/m.py:1` and "c-c" on `src/c.py:10`. At `H1` that line names
  `alpha_l2_new`, which `TE-1`'s diff changed.
- `TE-2`: a correctness concern "i1" on `src/b.py:1`. Then an adequacy
  note "i3" and a correctness blocker "i4" on `src/b.py:2`. Last, an
  adequacy concern "i6" on `src/b.py:1`.

The Spec lens's findings for `TE-2`, each on the line shown:

| claim | severity | at | probe `find`, `replace` | verdict |
|---|---|---|---|---|
| f1 | concern | `src/b.py:2` | `beta_rate`, `beta_gone` | `survived` |
| f2 | blocker | `src/b.py:3` | `beta_l3`, `beta_k` | `killed` |
| f3 | concern | `src/c.py:2` | `nothing_here`, `x` | `unproven` |
| f4 | note | `src/c.py:3` | `gamma_l2_new`, `gamma_s` | `survived` |
| f5 | blocker | `src/c.py:13` | `gamma_l12`, `gamma_x` | never asked |
| f6 | concern | `src/c.py:11` | none | |
| f7 | concern | `src/c.py:4` | f3's probe | `unproven` |
| f8 | concern | `src/c.py:5` | on `tests/test_c.py` | refused |
| f10 | concern | `src/c.py:6` | `nothing_here`, `y` | `unproven` |

Every probe but f8's is on `src/c.py` or `src/b.py`. f3's and f10's share
the file and `find`, and differ only in `replace`.

The Standards lens's are a note "s1" on `src/b.py:4`, a blocker "s2" on
`src/b.py:5` and a note "s3" on `src/c.py:12`. The join lens's are a
concern "j1" on `src/a.py:2`, a concern "j2" on `src/m.py:1`, and a blocker
"j3" on `src/b.py:2` with a probe. Record copies of the three join findings
under `TE-2` with `record_findings`, then copies of the twelve Spec and
Standards findings, as `SA-0154` and `SA-0153` do. `layers` is `TE-2`'s `LayerReview`, its Spec then
Standards reviews, then `TE-1`'s with no reviews.

Replace `session.probe_findings` with a double. It records each call,
`base_results` included. It raises `RuntimeError("no cell for the join")`
when `spec.base_sha` is `M`. Otherwise it builds one entry per distinct
`review.probe_key`, in first-seen order, with the refused probes first, as
the real call does. A probe `probe.probe_refusal` refuses reads `unproven`
with the refusal as its reason. The cell keyword `test_paths` is
`["tests/**"]`, which matches `tests/test_c.py` and no path under `src/`.
Every other probe's verdict is looked up by `spec.base_sha`, its `find`
and its `replace`, and a key the table lacks raises `KeyError`. An
`unproven` probe's reason is "src/c.py: find text not found for" and its
`replace`.
It calls `review.apply_probe_verdict` on every target of each probe. Each
entry holds the probe dumped and its reason. Pass each of the eight cell
keywords as a distinct object.

**Criterion 1's witness** asserts `groups`, as layer, file, claims and
severities:

1. `TE-2`, `src/a.py`: j1.
2. `TE-2`, `src/b.py`: f1, s2, i1, as blocker, blocker, concern.
3. `TE-2`, `src/c.py`: f4, f6, as blocker, concern.
4. `TE-1`, `src/a.py`: c-a.
5. `TE-1`, `src/c.py`: c-c.

It asserts `pool` as layer, claim, outcome and reason: j2 `unanchored`, j3
`unverified`, f3 `unverified`, f5 `unanchored`, f7 `unverified`, f8
`unverified`, f10 `unverified`, s1 `note`, s3 `unanchored`, i6
`unverified`, and c-m `unanchored`. j3's reason holds "no cell for the
join". f3's and f7's name `x`, and f10's names `y`. f8's is the refusal,
and i6's is "its REVIEW probe did not survive". Every other reason is
empty.
These fail it, each measured:

- a layer anchored over its `LayerFields.base`, which anchors c-m
- the identifier half dropped, which leaves f6 unanchored
- a diff without `DIFF_FLAGS`, which reads `diff.context = 0`
- the join anchored over the top layer's own diff, or from the bottom
  layer's run base, or left out
- the join's findings put under the bottom layer
- a probe asked for an unanchored finding
- a killed finding kept, or an `unproven` one read as survived
- a `note` judged by the severity its lens filed
- a raise from `probe_findings` that propagates, or one that stops the
  walk
- entries matched to findings by index
- a `note` decided before anchoring, which pools s3 as `note`
- the join walked after the layers
- the probe's tree at the head itself, with no patch
- groups by layer alone, by file alone, or sorted
- in-cell concerns left out
- every in-cell finding kept, not concerns alone
- every finding of the task kept, the end-review copies included
- in-cell rows selected by excluding `spec` and `standards`, which keeps
  the join copies
- in-cell concerns walked before the end-review findings
- the `note` outcome dropped from the pool
- an in-cell adequacy concern qualified as probe-less
- `read_head` at `<head>^`, or at the top head for every layer
- entries matched to findings by `find`, or by file and `find`

**Criterion 2's witness** asserts two calls. The first holds j3, and the
second f1, f2, f3, f4, f7, f8 and f10. The first's `spec.base_sha` is `M` and
the second's `H1`, and neither has a `stacked_on`. Each `spec_id` is
`TE-2`, and each `branch` is `TE-2`'s. The first patch holds
"+alpha_l2_new" and not "moved_main_only". The second holds "+beta_rate"
and not "alpha_l2_new". The first call's `base_results` collect `[]` and
`None`, `TE-1`'s. The second's collect `["tests/t.py::test_old"]` and
`None`, `TE-2`'s. Each call's eight keywords are the objects passed, by
`is`. These fail it, each measured:

- the probe's tree at the head itself, with no patch
- the join's tree at the top layer's parent, or at the bottom layer's run
  base
- a probe asked for an unanchored finding
- a call for `TE-1`, whose inputs carry no probe
- the join's cell built from the bottom layer's fields
- the base in `stacked_on`, with the head as `base_sha`
- the join's `base_results` from the top layer's run, or a layer's from
  the bottom layer's
- the baseline read by task id, not by the task's run id
- a copied `test_paths`

**Criterion 3's witness** reads the rows by `task_key` and claim. `TE-2`
holds j1, j2, j3, f1 to f8, f10, s1, s2, s3, i1 and i6 at positions 1 to
17. `TE-1` holds c-a, c-m and c-c at 1 to 3. Twenty rows in all. f1's row is `spec`,
`concern`, `src/b.py`, 2, "f1", `survived`, `qualified` and an empty
reason. f2's verdict and outcome are both `killed`. f3 is `unproven` and
`unverified`, with the double's reason. s1 has no verdict and is `note`.
f4 is `note`, `survived`, `qualified`. f5 has no verdict and is
`unanchored`. It opens a fresh `Ledger` with no record, and creates one
unrelated repo, run and task there first. It folds the record into it and
asserts the same rows. It folds the record into the source ledger and
asserts the rows unchanged. Last, `fold_task` on the fresh ledger with
`TE-2`'s key and no facts leaves `TE-1`'s three rows alone. These fail it,
each measured:

- `_apply` with no branch for `qualification`
- `_drop_task_rows` that leaves the rows, which raises on the primary key
- `INSERT OR REPLACE` with `_drop_task_rows` untouched, which leaves
  `TE-2`'s rows after `fold_task(key, [])`
- the severity recorded after the probe promoted it
- a pooled finding left unrecorded
- `position` counted over the whole table, not per task

**How the lists were measured.** A throwaway simulation ran on 2026-09-23
at `3699aeb8`, on the host's git 2.54. It subclassed `Ledger` with this
spec's table and methods, and with `SA-0159`'s. It stood in for `layer_fields` and
`LayerReview` with `SA-0146`'s and `SA-0153`'s fields. It ran the real
`findings.anchor`, `mirror.file_at`, `probe.probe_refusal` and
`review.apply_probe_verdict`. It could not set `GIT_CONFIG_GLOBAL`, so the
config case ran as a diff with `--unified=0`. How the cell's git 2.39.5
reads that config is unmeasured. The right build passed every assertion
above, and each wrong version listed failed its own witness. The code of
`SA-0138` and `SA-0145` to `SA-0159` is not at `3699aeb8`, so no witness ran
against it. A later revision dropped the verdict and rebuttal filter, with
the rows i2 and i5 and the two wrong versions only they killed. Nothing
ran after that edit.

**What the witnesses leave undriven.**

- The real `probe_findings` in a Gate-only cell, and so the kill rule
  itself. Criteria 4 and 5 hold its body as REVIEW runs it, `SA-0138`'s
  own witnesses hold the rule, and `tests/test_probe_cell.py` runs it in a
  cell.
- A raise from the probe call that is not a `RuntimeError`. It propagates,
  so a wrong keyword fails loudly rather than reading `unverified`.
- A run whose baseline holds no `tests` result. `added_tests` returns
  `None`, so a probe with a new failure reads `unproven` and its finding
  goes to the pool as `unverified`.
- A `GitError` from `file_at`, and a join with no layers. Handle both as
  the Problem says.
- A probed finding the call leaves with no verdict. Read it as
  `unverified`. The real call leaves none, since it decides every target
  or raises.
- A layer whose lens errored. Its `LensReview` holds no findings, so its
  in-cell concerns are its only inputs.
- A finding on a binary file. The patch cannot carry one, so the cell
  raises and the finding is `unverified`.

**The `prose` gate** counts every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words. Keep each docstring within ten lines.

**Commit as each witness passes**, before the full suite runs.

**Size.** `saffron/ledger.py` and `saffron/cell/session.py` are in
`elevate_on`, so `size` blocks at the `feature` ceiling of 3000 tokens
(`saffron/gates/core/size.py:26`). A prototype of all four files, counted
by `size_gate` itself, came to 1962. That is 214 in `ledger.py`, 56 in
`session.py`, 608 in `qualify.py` and 1084 in the tests. The assertions
the prototype left short, and the docstrings and comments, bring it to
about 2330. The adequacy rule and the round-2 arrangement add about 80
more. Dropping the filter and two fixture rows takes about 30 off, near
2380, 79% of the ceiling. That is near it, so keep the helper shared, the
test docstrings short and the double compact. Rename the probe function in
place rather than copy its body.
