---
id: SA-0180
title: An end review's layer findings reach no follow-up, because nothing anchors, probes or groups them
type: feature
priority: 1
depends_on: [SA-0179]
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
budget_usd: 24
max_attempts: 3
max_turns: 140
estimated_lines: 590
pending_symbols:
  - saffron/qualify.py::qualify
  - saffron/qualify.py::groups
  - saffron/qualify.py::pool
acceptance:
  - claim: >-
      `qualify.qualify(ledger, layers, None, ...)` walks each layer in the
      order given. A layer's inputs are its end-review findings in review
      order. Each input is anchored by `findings.anchor` against the diff
      `<head>^..<head>` of its own layer, reading cited lines at that head.
      An anchored finding with a probe then takes the probe's verdict.
      `killed` drops it. `unproven` sends it to the pool as `unverified`,
      with the reason of the entry whose probe has its `review.probe_key`.
      `survived` makes it a `blocker`. An unanchored finding goes to the
      pool as `unanchored`, whatever its severity, and a `note` as `note`.
      Every other finding qualifies. `groups` holds one `FollowUpGroup` per
      layer and file, in the order its first finding was met. `pool` holds
      the rest in that order. The witness drives both halves of the
      anchoring rule, a bottom layer whose run's base is not its head's
      parent, a cited line that moved between a layer's parent and its
      head, the verdicts `survived`, `killed` and `unproven`, a probe never
      asked, a refused probe, two findings sharing one probe, two probes
      differing only in `replace`, a `note` whose probe survives, an
      unanchored `note`, one layer and one
      file each shared by two groups, and a first group whose file sorts
      after the next one's.
    witness: tests/test_qualify.py::test_each_layers_findings_are_anchored_probed_and_grouped_by_layer_and_file
  - claim: >-
      `qualify` hands a layer's anchored findings with a probe to
      `session.probe_findings`, one call per layer, and no call for a
      layer with none. The `CellSpec` of each call is the tree the probes
      run on. Its `base_sha` is the full sha of `<head>^`, it has no
      `stacked_on`, its `spec_id` and `branch` are the layer's, and the
      patch is the layer's diff. `base_results` is
      `ledger.baseline_results` of the layer's task's run. `repo`,
      `mirror`, `gates_dir`, `thread_env`, `test_paths`, `gates`, `created`
      and `note` pass through as given. The witness drives a stacked
      layer, a layer with no probe, and run ids that differ from task ids.
    witness: tests/test_qualify.py::test_a_layers_probes_run_in_a_gate_only_cell_on_its_own_tree
  - claim: >-
      Each finding `qualify` meets becomes one `qualification` fact under
      its layer's task, numbered from 1 per task in the order met. It
      carries the finding's lens, the severity its lens filed, its file,
      line and claim, the probe's verdict or none, the outcome and the
      reason. A killed finding is recorded too. The witness drives two
      layers and each of the five outcomes.
    witness: tests/test_qualify.py::test_each_layers_qualifications_are_facts_numbered_within_its_task
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

**Step 4 is four specs.** `SA-0178` lets the host probe any findings,
with `session.probe_findings`. `SA-0179` adds the `qualifications` table
and `Ledger.record_qualification`. This spec qualifies each layer's
findings. `SA-0147` adds the join lens's findings to the walk. The four
were one spec, `SA-0147`, until its cell ended `PLAN_REJECTED` on
2026-09-26. Its plan priced itself at 5800 changed tokens, and `size`
blocked it at `elevated`.

`SA-0146` builds the two layer lenses. `SA-0153` runs them over a stack
and returns one `LayerReview` per layer. `SA-0154` adds the join lens and
runs the whole end review. `SA-0157` wires it into `saffron batch
--stack`. `SA-0161` writes a follow-up spec from each group `qualify`
returns, and `SA-0165` wires that writer into `saffron batch --stack`.

**What the tree base holds.** This spec's tree base is `SA-0179`'s head.
Only `depends_on[0]` stacks (`saffron/task.py:165-166`, `:213`), and
`SA-0179` stacks on `SA-0178`. Every other spec named above is merged at
`eb7b7d37`, where every line number below was read. `SA-0178` edits
`saffron/cell/session.py` and `SA-0179` edits `saffron/ledger.py`, so
their names are cited by symbol, and no line below is in either file's
changed range.

- `SA-0178` adds `session.probe_findings(targets, *, spec, repo, mirror,
  gates_dir, thread_env, test_paths, base_results, gates, patch, created,
  note)`. It is REVIEW's `_probe_adequacy` body, renamed, over `targets`
  rather than REVIEW's adequacy findings. It asks each distinct
  `review.probe_key` once, the refused probes first, in one Gate-only
  cell seeded at `spec.tree_base` with `patch` applied. It decides every
  target in place with `review.apply_probe_verdict`, and returns one
  `probes.json` entry per distinct edit, each with the `probe` dumped and
  its `reason`. So an entry's index is not its finding's.
- `SA-0179` adds `Ledger.record_qualification`. Its signature is
  `(task_id, *, finding, filed, outcome, reason)`. It writes one `qualification` fact under the task's
  key, and one `qualifications` row whose `position` is one more than the
  task's rows so far. The row holds the finding's lens, file, line, claim
  and `probe_verdict`, with `filed` as its severity. `_apply` places the
  fact, and `_drop_task_rows` deletes the key's rows.
- `SA-0138` makes a probe killed only by a failure of a test the diff
  adds. `_probe_adequacy`, and so `probe_findings`, takes `base_results`,
  the task's pre-turn suite. It computes `probe.added_tests(base_results,
  <the probe cell's baseline>)` once and passes it as `counted` to every
  `check_probe` call (`saffron/cell/session.py:1419-1428`). `added_tests`
  returns `None` when `base_results` holds no `tests` result, or one whose
  `collected` is `None` (`saffron/probe.py:302-316`). A probe with a new
  failure then reads `unproven`.
- `SA-0145` writes one `stack_layers` row per layer with
  `record_stack_layer`, each row naming its predecessor.
- `SA-0146`'s `end_review.layer_fields(ledger, task_key)` returns
  `LayerFields`, whose `spec_id`, `branch` and `head` are the layer's
  task's own (`saffron/end_review.py:101-133`). `head` is its
  `pushed_sha`. `base` is the predecessor's recorded head, or the run's
  `base_sha` for a bottom layer.
- `SA-0153`'s `end_review.LayerReview` has `task_key` and `reviews`
  (`saffron/end_review.py:240-246`). `review_stack` returns one per layer,
  highest position first (`:324`). A layer the end review did not reach
  has empty `reviews` (`:365-371`). Each of the others holds the Spec
  review, then the Standards review. A Spec finding keeps the probe it
  carried. `review_stack` records each reached layer's end-review
  findings with `record_findings` under the layer's own task, after its
  in-cell findings (`:354-356`).
- `SA-0154`'s `end_review.run_end_review` returns a frozen `StackReview`
  (`saffron/end_review.py:496-502`). Its `layers` is the `LayerReview`
  list, top down, and its `join` is the join lens's `LensReview` or
  `None`. It runs the join first (`:530`, `:546`). The join's findings are
  recorded with `record_findings` under the top layer's task (`:485`),
  before that layer's own end-review findings. `SA-0157`'s
  `_stack_end_review` in `saffron/cli.py` is the callable that returns it,
  and `qualify` takes both fields from it.
- `SA-0159` keeps each run-level baseline result's `collected`, so
  `ledger.baseline_results(run_id)` returns it as the run recorded it
  (`saffron/ledger.py:1403-1404`, `:1440-1446`).

**Anchoring today.** `CONTEXT.md:444-450` defines **Anchored**: inside a
diff hunk, or citing a line that names an identifier the diff changed.
`findings.anchor(findings, diff, *, read_head)` applies both halves and
returns copies (`saffron/agents/findings.py:128-146`). The second half reads
the cited line through `read_head` and compares its words with every
changed line's (`:149-166`). `mirror.file_at(mirror, sha, path)` reads a
file at a sha, and returns `None` for a path the tree lacks
(`saffron/repos/mirror.py:241-269`). It raises `UnreadablePath`, a
`GitError` (`:43`), for a path it cannot read as a file (`:258-269`).

**Probing, at the tree base.** `probe_findings` enters its cell through
`critic_cell`, which seeds it at `spec.tree_base` and applies and commits
`patch` (`saffron/cell/session.py:1207`, `:1217`). `tree_base` is
`base_sha` when `stacked_on` is `None` (`:293-301`). `apply_probe_verdict`
sets `probe_verdict`. `survived` makes a finding a `blocker`, `killed` a
`note`, and `unproven` leaves it as filed
(`saffron/phases/review.py:585-595`). A probe whose `find` matches no
line, or more than one, is `unproven` with its reason
(`saffron/cell/worktree.py:642-648`, `saffron/probe.py:206-210`). Each
entry's fields come from `probe.record_fields`
(`saffron/probe.py:319-338`).

**A run's baseline.** Each cell makes its own run
(`saffron/cell/session.py:1702`). It takes the pre-turn suite on the
task's tree base, `baseline = suite.baseline(tree)` (`:1758`), and records
each result under the run (`:1775-1776`). `ledger.baseline_results(run_id)`
reads each back with its `collected`. Without that, `added_tests` would
read every probe with a new failure `unproven`, and none `killed`.

**The fact kind exists.** `qualification` is in `KINDS`
(`saffron/record/contract.py:40`), and `SA-0179` places it.

## Problem

**Qualification, over the layers.** Add `saffron/qualify.py` with three
frozen dataclasses. `Qualified` has `task_key`, `finding`, `outcome` and
`reason`. `FollowUpGroup` has `task_key`, `file` and `findings`, a tuple.
`Qualification` has `groups` and `pool`, two lists. Add
`qualify(ledger, layers, join, *, mirror, repo, gates_dir, thread_env,
test_paths, gates, created, note)`. `layers` is the `LayerReview` list,
top down, and `join` is a `LensReview` or `None`. `SA-0147` walks the
join. Until then a `join` that is not `None` raises `ValueError`, so no
caller loses its findings unseen. For each layer in order:

- Read the layer's `task_id` and `run_id` from its record key with a
  `ledger._db` query on `tasks`, as `end_review.layer_fields` does
  (`saffron/end_review.py:111`). No public `Ledger` method maps a key to
  either, and `saffron/ledger.py` is forbidden here.

- Build the diff, `git diff` with `DIFF_FLAGS` over `<head>^..<head>` in
  `mirror`, `head` from the layer's `LayerFields`.
- Anchor the inputs with `findings.anchor`. `read_head` reads the head
  through `mirror.file_at`, and `GitError` reads as `None`.
- When any anchored finding carries a probe, hand all such findings to
  one call of `session.probe_findings`. Reach it through the `session`
  module, so a test can replace it. Its `spec` is a `CellSpec` whose
  `base_sha` is `<head>^` resolved to a full sha. `spec_id` and `branch`
  come from the layer's `LayerFields`. `patch` is the diff.
  `base_results` is `ledger.baseline_results` of the layer's task's run.
  `CellSpec` also requires `spec_sha`, `touches`, `spec_type` and `body`
  (`saffron/cell/session.py:250-257`). Fill them with placeholders, such
  as empty values. `critic_cell` reads only `spec_id`, `branch` and
  `tree_base` (`:1170-1218`), and `probe_findings` reads nothing else of
  `spec`.
  An `unproven` finding's reason is the entry whose `probe` has its
  `review.probe_key`.
- Decide each finding in the order of the inputs, and record it with
  `ledger.record_qualification` under the layer's task, `filed` the
  severity its lens filed. Capture each severity before the probe call,
  since the call promotes in place.

`qualify` returns the `Qualification`. Keep the per-layer walk in one
helper. It takes the range's base and head, the inputs, and the task to
record under. It also takes the run the probes count from. That run's
`baseline_results` become `base_results`. `qualify` passes the layer's
own task and run for both. `SA-0147` adds each layer's in-cell concerns
to its inputs, and calls the helper once more for the join. That call
records under the top layer's task and counts from the bottom layer's
run.

`qualify` has no production caller until `SA-0165` binds it for
`SA-0161`'s `write_follow_ups`, which passes its groups to the spec
writer. So `qualify`, and the `groups` and `pool` fields only `SA-0161`
reads, are `pending_symbols`. The `dead` gate defers them while this spec
is open (`.saffron/gates/dead.py:4-6`, `:113-127`).

## Out of scope

- **A layer's in-cell REVIEW concerns.** `SA-0147` adds them to each
  layer's inputs, after its end-review findings.
- **The join lens's findings.** `SA-0147` walks them first, over the
  whole stack, under the top layer's task.
- **A raise from the probe call.** `SA-0147` catches a `RuntimeError`
  from any call, the join's or a layer's. Here it propagates.
- **Writing follow-up specs.** `SA-0161` writes one from each group, and
  `SA-0165` wires it into `saffron batch --stack`.
- **The probe call and the table.** `SA-0178` builds `probe_findings`,
  and `SA-0179` builds the `qualifications` table, its write and its
  fold. This spec edits neither file.
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
  only that test fails reads `killed`, and its finding is dropped. A
  stacked layer's run took its baseline at its predecessor's head, which
  is its head's parent unless a hand push moved it. How often the default
  branch adds a test during a stack batch is unmeasured.
- **The vocabulary.** `CONTEXT.md` has no entry for qualification, a
  follow-up group or the backlog pool. Backlog item b-466005 files them by
  hand.

## Notes for the agent

**Criteria 1 to 3 are new code.** No text at the tree base qualifies a
finding. So they declare a witness and no mutant, and `witness` reports
`skip` for them. `SA-0178` holds the probe call to REVIEW's behaviour, and
`SA-0179` the fold of the `qualifications` rows.

**Import `qualify` inside the test body.** `saffron/qualify.py` does not
exist at the tree base. A module-scope import fails collection when the
source is reverted, and `revert` reads that as `skip`.

**Criteria 1 to 3 share one arrangement.** A helper builds it and runs
`qualify` once, with `join` `None`. `SA-0147` extends the same helper with
the join, so keep the expected groups, pool and rows below as module
constants it can reuse. Point `GIT_CONFIG_GLOBAL` at a file in `tmp_path`
that sets `diff.context = 0`, with `monkeypatch`. That file replaces the
global config, so give each commit its own identity with `-c user.email`
and `-c user.name`. Build a git repo in `tmp_path` as the mirror. Each
file below holds twelve lines, `<name>_l1` to `<name>_l12`, except where
the table says.

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
`["tests/t.py::test_old"]` for `TE-2`. The `lint` result collects `None`.
Package `TE-1` `READY_FOR_REVIEW` at `H1` and `TE-2` at `H2`. Record `TE-1`
as the layer at position 1 and `TE-2` at position 2 on it. Record no
in-cell finding. `SA-0147` adds those behind a keyword of the helper.

The Spec lens's findings for `TE-2`, in this order, each on the line shown:

| claim | severity | at | probe `find`, `replace` | verdict |
|---|---|---|---|---|
| f6 | concern | `src/c.py:11` | none | |
| f1 | concern | `src/b.py:2` | `beta_rate`, `beta_gone` | `survived` |
| f2 | blocker | `src/b.py:3` | `beta_l3`, `beta_k` | `killed` |
| f3 | concern | `src/c.py:2` | `nothing_here`, `x` | `unproven` |
| f4 | note | `src/c.py:3` | `gamma_l2_new`, `gamma_s` | `survived` |
| f5 | blocker | `src/c.py:13` | `gamma_l12`, `gamma_x` | never asked |
| f7 | concern | `src/c.py:4` | f3's probe | `unproven` |
| f8 | concern | `src/c.py:5` | on `tests/test_c.py` | refused |
| f10 | concern | `src/c.py:6` | `nothing_here`, `y` | `unproven` |

Every probe but f8's is on `src/c.py` or `src/b.py`. f3's and f10's share
the file and `find`, and differ only in `replace`. f6 comes first so that
the first group's file sorts after the second's.

The Standards lens's are a note "s1" on `src/b.py:4`, a blocker "s2" on
`src/b.py:5` and a note "s3" on `src/c.py:12`. Build the join lens's
findings too, though this spec passes no join: a concern "j1" on
`src/a.py:2`, a concern "j2" on `src/m.py:1`, and a blocker "j3" on
`src/b.py:2` with a probe of `beta_rate` to `beta_j`. Record copies of the
three join findings under `TE-2` with `record_findings`, then copies of
the twelve Spec and Standards findings, as `SA-0154` and `SA-0153` do.
`TE-1`'s Spec lens has three concerns: "c-a" on `src/a.py:2`, "c-m" on
`src/m.py:1` and "c-c" on `src/c.py:10`. At `H1` that line names
`alpha_l2_new`, which `TE-1`'s diff changed. Record their copies under
`TE-1`. `layers` is `TE-2`'s `LayerReview`, its Spec then Standards
reviews, then `TE-1`'s with its Spec review.

Replace `session.probe_findings` with a double. It records each call and
its keywords. It raises `KeyError` for a `spec.base_sha` other than `H1`.
Otherwise it builds one entry per distinct `review.probe_key`, in
first-seen order, with the refused probes first, as the real call does. A
probe `probe.probe_refusal` refuses reads `unproven` with the refusal as
its reason. The cell keyword `test_paths` is `["tests/**"]`, which
matches `tests/test_c.py` and no path under `src/`. Every other probe's
verdict is looked up by its `find` and `replace`. An `unproven` probe's
reason is "src/c.py: find text not found for " and its `replace`. It
calls `review.apply_probe_verdict` on every target of each probe. Each
entry holds the probe dumped and its reason. `mirror` is the repo. Pass
each of the other six cell keywords as a distinct `object()`.

**Criterion 1's witness** asserts `groups`, as layer, file, claims and
severities:

1. `TE-2`, `src/c.py`: f6, f4, as concern, blocker.
2. `TE-2`, `src/b.py`: f1, s2, as blocker, blocker.
3. `TE-1`, `src/a.py`: c-a.
4. `TE-1`, `src/c.py`: c-c.

It asserts `pool` as layer, claim, outcome and reason: f3 `unverified`, f5
`unanchored`, f7 `unverified`, f8 `unverified`, f10 `unverified`, s1
`note`, s3 `unanchored`, and c-m `unanchored`. f3's and f7's reasons
name `x`, and f10's names `y`. f8's is the refusal. Every other reason is
empty. These
fail it, each measured:

- a layer anchored over its `LayerFields.base`, which anchors c-m
- the identifier half dropped, which leaves f6 unanchored
- a diff without `DIFF_FLAGS`, which reads `diff.context = 0`
- a probe asked for an unanchored finding
- a killed finding kept, or an `unproven` one read as survived
- a `note` judged by the severity its lens filed
- entries matched to findings by index
- a `note` decided before anchoring, which pools s3 as `note`
- the probe's tree at the head itself, with no patch
- groups by layer alone, by file alone, or sorted
- the `note` outcome dropped from the pool
- `read_head` at `<head>^`, or at the top head for every layer
- entries matched to findings by `find`, or by file and `find`

**Criterion 2's witness** asserts one call. It holds f1, f2, f3, f4, f7,
f8 and f10. Its `spec.base_sha` is `H1`, and it has no `stacked_on`. Its
`spec_id` is `TE-2`, and its `branch` is `TE-2`'s. Its patch holds
"+beta_rate" and not "alpha_l2_new". Its `base_results` collect
`["tests/t.py::test_old"]` and `None`, `TE-2`'s. Its eight keywords are
the objects passed, by `is`. These fail it, each measured:

- the probe's tree at the head itself, with no patch
- a call for `TE-1`, whose inputs carry no probe
- the base in `stacked_on`, with the head as `base_sha`
- the baseline read by task id, not by the task's run id
- a layer's `base_results` from the bottom layer's run
- a copied `test_paths`

**Criterion 3's witness** reads the rows by `task_key` and position.
`TE-2` holds f6, f1 to f5, f7, f8, f10, s1, s2 and s3 at positions 1
to 12. `TE-1` holds c-a, c-m and c-c at 1 to 3. f1's row is `spec`,
`concern`, `src/b.py`, 2, "f1", `survived`, `qualified` and an empty
reason. f2's verdict and outcome are both `killed`. f3 is `unproven` and
`unverified`, with the double's reason. s1 has no verdict and is `note`.
f4 is `note`, `survived`, `qualified`. f5 has no verdict and is
`unanchored`. These fail it, each measured:

- the severity recorded after the probe promoted it
- a pooled finding left unrecorded

**How the lists were measured.** A throwaway prototype ran on 2026-09-26
at `eb7b7d37`, on the host's git 2.54, with `GIT_CONFIG_GLOBAL` set as
above. It patched `Ledger` with the table and method `SA-0179` builds, and
replaced `probe_findings` with the double. It ran the real `layer_fields`,
`record_stack_layer`, `findings.anchor`, `mirror.file_at`,
`probe.probe_refusal` and `review.apply_probe_verdict`. The right build
passed all three witnesses. Each wrong version above was made from it by
one or two edits, and each failed the witness it is listed under.
Measured on 2026-09-26 in `saffron/cell:saffron`, whose git is 2.47.3, a
`GIT_CONFIG_GLOBAL` setting `diff.context = 0` gives no context lines. An
explicit `--unified=3` overrides it, giving six context lines around a
one-line change.

**What the witnesses leave undriven.**

- The real `probe_findings` in a Gate-only cell, and so the kill rule
  itself. `SA-0178`'s witnesses hold its body as REVIEW runs it,
  `SA-0138`'s own witnesses hold the rule, and `tests/test_probe_cell.py`
  runs it in a cell.
- A run whose baseline holds no `tests` result. `added_tests` returns
  `None`, so a probe with a new failure reads `unproven` and its finding
  goes to the pool as `unverified`.
- A `GitError` from `file_at`. Handle it as the Problem says.
- A probed finding the call leaves with no verdict. Read it as
  `unverified`. The real call leaves none, since it decides every target
  or raises.
- A layer whose lens errored. Its `LensReview` holds no findings, so it
  has no inputs here.
- A `join` that is not `None`. `SA-0147` replaces the `ValueError`.

**The `prose` gate** counts every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense, a hedge
or a sentence over 25 words. Keep each docstring within ten lines.

**Commit as each witness passes**, before the full suite runs.

**Size.** No path this spec touches is in `elevate_on`, so `size` is
advisory at the `feature` ceiling of 3000 tokens
(`saffron/gates/core/size.py:26`). A plan whose files stay inside
`touches` is priced at `standard`, where an estimate over the ceiling
stands (`saffron/agents/artifacts.py:299-336`). The prototype, formatted
with `ruff format`, measured 1684 changed tokens with `size_gate`'s own
count: 582 in `qualify.py` and 1102 in the tests. Sibling cells landed at
1.4 to 1.6 times their authors' estimates, so about 2360, 79% of the
ceiling. Keep the helper shared, the test docstrings short and the double
compact.
