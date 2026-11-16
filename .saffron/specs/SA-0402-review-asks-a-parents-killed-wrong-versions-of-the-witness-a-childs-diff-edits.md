---
id: SA-0402
title: "REVIEW never asks a parent's killed wrong versions again when a child's diff edits the parent's witness"
type: feature
priority: 3
risk: elevated
estimated_lines: 327
estimate_measured: true
depends_on: [SA-0401, SA-0400]
consumes:
  - saffron/parent_versions.py:parent_version_pairs
touches:
  - saffron/parent_versions.py
  - saffron/cell/session.py
  - saffron/phases/review.py
  - saffron/task.py
  - tests/test_session.py
  - tests/test_cli.py
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
  - saffron/intake.py
  - saffron/scheduler.py
  - saffron/probe.py
  - saffron/cli.py
  - saffron/repos/**
  - saffron/gates/**
  - saffron/agents/**
  - saffron/report/**
  - saffron/phases/rebut.py
  - saffron/cell/worktree.py
  - tests/test_parent_versions.py
  - tests/test_review.py
  - tests/test_intake.py
  - tests/test_queued_specs.py
  - tests/test_scheduler.py
budget_usd: 48
max_attempts: 3
max_turns: 200
acceptance:
  - claim: >-
      REVIEW asks each parent's killed wrong versions of the witness the
      child's diff edits, after the spec's own pairs, in the gate-only
      cell `_apply_criterion_probes` already enters. `_drive_cell` calls
      `parent_versions.parent_version_pairs` once, with
      `CellSpec.depends_on`, the `.saffron/specs` it exported under
      `gates_dir`, `out_dir` and `reviewed_diff`. A parent pair whose edit
      lies outside the spec's `touches` is still asked. A survivor is a
      host-filed `adequacy` blocker whose claim names its own parent and
      version, as `<parent>'s wrong version`. The task writes
      `parent-versions.json` after the edits are asked. It holds
      `versions`, each parent entry with its `outcome` and `summary`, and
      `unread`, the unread parents. One REVIEW line reads `parent wrong
      versions: <c> chosen, <s> survived, <r> refused, <u> unproven`.
      Chosen counts every parent pair. Survived counts an outcome of
      `survived`. Refused counts a pair refused before any cell, which
      carries a `refusal` key. Unproven counts an outcome of `unproven`
      with no `refusal` key. No pair counts in two of the last three, and
      a killed pair counts only as chosen. Then come `; no record read
      for` and the unread parents joined by commas. The spec's own
      `wrong-versions.json` and its REVIEW line hold its own versions
      alone. The witness drives one cell through REVIEW. Its diff edits
      tests/test_p.py alone. The spec declares one criterion on `t.py::a`
      with one wrong version. Its criterion-probe session names no edit,
      and its wrong-version session expresses the version as an edit on
      src/y.py. `depends_on` is `SP-1`, `SP-2`, `SP-3`, `SP-5` and `SP-6`.
      `SP-1`, `SP-2`, `SP-5` and `SP-6` are retired, and `SP-3` is queued.
      Each parent has one criterion, which declares one wrong version. A
      retired non-parent `SP-4` has its witness on tests/test_p.py and
      records one killed version, which is never asked. `SP-6`'s witness
      `test_gone` on tests/test_p.py is not among the tests the head suite
      collected, and it records three killed versions. Every other witness is
      `test_guard` on tests/test_p.py, which the suite collected. `SP-1`
      records two killed versions on src/p.py. `SP-3` records one on
      lib/q.py, outside `touches`, and then one each on spec/t.py and
      spec/u.py, under the declared test path. `SP-2` has no record, and `SP-5`'s is broken JSON. The
      `tests` gate kills the spec's own edit and both of `SP-1`'s.
      `SP-3`'s lib/q.py edit survives. A spy on `parent_version_pairs`
      records its keyword arguments and calls through. A spy on
      `critic_cell` records the `network` of each cell entered. The
      witness asserts the spy's one call, the mutator's exact sequence and
      each `tests` subset. It asserts three cells entered: the gate-only
      suite cell, the critic cell, then one probe cell. It asserts the
      whole record. Each of `SP-3`'s two spec/ versions is `unproven` under
      its refusal. Each of `SP-6`'s three is `unproven` with no `refusal`
      key, and none reaches the mutator. It asserts the line `parent wrong
      versions: 8 chosen, 1 survived, 2 refused, 3 unproven; no record
      read for SP-2, SP-5`. It asserts the spec's own
      record and line. It asserts the one blocker in `rebuttal.json`,
      naming `SP-3`'s wrong version `v0` on lib/q.py line 1.
    witness: tests/test_session.py::test_a_parents_killed_wrong_version_its_witness_now_survives_is_rebutted_as_a_blocker
    wrong_versions:
      - The call passing an empty `depends_on`, so no parent is read.
      - The parent specs read from the operator's checkout under `repo` rather than the export under `gates_dir`.
      - Each parent's record read under the child's own task folder, so every parent reads as unread.
      - The parent pairs put ahead of the spec's own, so the spec's edit is no longer applied first.
      - The finding built without the parent, so its claim says the spec's own wrong version.
      - The blocker naming the first `depends_on` entry, so it says `SP-1`.
      - The record's entries copied before `_apply_criterion_probes` runs, so none carries an outcome.
      - The unread parents left out of the record.
      - The line counting killed versions as survived.
      - The line leaving unproven versions uncounted.
      - The line counting a refused pair as unproven too, so it says 2 unproven.
      - The line leaving refused pairs uncounted.
      - The line naming only the first unread parent.
      - Two count slots of the line swapped, so survived and refused trade places, or refused and unproven do.
      - Refused and unproven defined around the `refusal` key the other way round, so the line says 3 refused and 2 unproven.
      - The parent pairs asked in a second `_apply_criterion_probes` call, so a fourth cell is entered.
      - "`SA-0400`'s scope rule applied to parent pairs, so the edit on lib/q.py is refused."
      - The parent entries folded into the spec's own `wrong-versions.json`.
  - claim: >-
      REVIEW writes `parent-versions.json` and its line exactly when there
      is a parent pair or an unread parent, whether or not the spec
      declares wrong versions of its own. With no unread parent the line
      carries no `; no record read for` tail. The witness drives four
      cells whose specs declare no criterion. Each diff edits
      tests/test_p.py. Retired `SP-1` and `SP-2` each have one criterion
      with one wrong version and its witness `test_guard` there, which the
      head suite collected. Retired `SP-3` has the same, but its witness
      is on tests/test_other.py, which the diff leaves alone. `SP-1` and
      `SP-3` each record one killed version, and `SP-2` has no record. The
      `tests` gate kills `SP-1`'s version. The cells' `depends_on` are
      `SP-1`, `SP-2`, `SP-3` and empty, in that order. It asserts each cell
      ends `READY_FOR_REVIEW`. It asserts the lines `parent wrong versions:
      1 chosen, 0 survived, 0 refused, 0 unproven` and `parent wrong
      versions: 0 chosen, 0 survived, 0 refused, 0 unproven; no record
      read for SP-2`, and no line for the last two. It asserts the record
      exists for the first two cells and not the last two.
    witness: tests/test_session.py::test_review_records_parent_versions_only_when_a_pair_or_an_unread_parent_exists
    wrong_versions:
      - The record written for every cell, so the last two write one.
      - The record written whenever `depends_on` is non-empty, so the `SP-3` cell writes one.
      - The record written only when there is a pair, so the `SP-2` cell writes none.
      - The record written only when a parent is unread, so the `SP-1` cell writes none.
      - The record written only when there are both, so neither of the first two writes one.
      - The parent pairs gathered only when the spec declares wrong versions, so no cell writes a record.
      - The unread tail always appended, so the first line ends with an empty `; no record read for`.
  - claim: >-
      `saffron cell` hands the cell every `depends_on` entry its spec
      declares, in declared order, as `CellSpec.depends_on`. The witness
      declares `SA-0002` then `SA-0001` and asserts that list.
    witness: tests/test_cli.py::test_a_specs_declared_depends_on_reaches_the_cell
    wrong_versions:
      - "`run_task` building `CellSpec` without `depends_on`, so the cell's list is empty."
      - "`run_task` sorting the list, so `SA-0001` comes first."
  - claim: >-
      A survivor of the spec's own wrong version still names `the spec's
      wrong version` in its blocker's claim.
    witness: tests/test_session.py::test_a_wrong_version_its_witness_survives_is_rebutted_as_a_blocker
    preserves: true
    wrong_versions:
      - The claim always naming `parent`, so the spec's own survivor reads `None's wrong version`.
---

## Context

Backlog item **b-9efbe2**, found by both review seats on #856. It cites
`DESIGN.md` §5.4 and §5.5, and §5.4.1 holds the wrong-version paragraph
this spec extends. This spec is the second piece of a split. `SA-0401`
chooses the recorded versions to ask again, and this spec asks them.
Every line number below was read at `3d84d970`.

**What happened**. `SA-0270` declares `depends_on: [SA-0269]`. Its cell
had to edit `SA-0269`'s witness
`test_two_tasks_bring_up_and_tear_down_only_their_own_networks_and_proxy`,
and it deleted the seeding the test needed. `SA-0269`'s record holds the
version "A `cell_up` that pre-cleans every `saffron-` holder on its
subnets", recorded `killed`. After the child's edit that version passed
the witness, and no gate asked it again.

**What the parents give this spec**. `SA-0401` adds
`parent_versions.parent_version_pairs(*, depends_on, specs_dir, out_dir,
diff)`. Each pair it returns is a parent criterion and an entry. The
entry holds `parent`, `witness`, `version`, `edit` and an empty `reason`.
It also returns the unread parent ids. `SA-0400` refuses a criterion probe outside
`touches` in `_apply_criterion_probes`. It never refuses a pair whose
entry carries `version`, and every parent entry carries it.

**Where REVIEW asks an edit today**. After the critic cell is torn down,
REVIEW builds one `pairs` list. The criterion probes come first, then each
wrong version with its criterion (`saffron/cell/session.py:3538-3555`).
`_drive_cell` hands it to `_apply_criterion_probes`
(`saffron/cell/session.py:3559-3575`). That function refuses a pair
through `probe_refusal` (`saffron/cell/session.py:2117`). It asks the
rest in one gate-only cell, with the noun `wrong version` for a pair whose
entry carries `version` (`saffron/cell/session.py:2201-2208`). It writes
each pair's `outcome` and `summary` in place
(`saffron/cell/session.py:2210-2211`). A survivor becomes
`review.survivor_finding(criterion, edit, content, version=...)`
(`saffron/cell/session.py:2222-2224`). Its claim names "the spec's wrong
version" (`saffron/phases/review.py:914-919`). REVIEW then writes the
spec's own `wrong-versions.json` and its line
(`saffron/cell/session.py:3590-3600`).

**What REVIEW holds to find a parent**. `gates_dir` is the `.saffron/`
export at `base_sha` (`saffron/cell/session.py:2363`). `task_dir` is
`out_dir / spec.spec_id` (`saffron/cell/session.py:2352`).
`reviewed_diff` is the critic cell's export
(`saffron/cell/session.py:3406`). `witness_gate` records a witness the
head suite did not collect as unproven and never applies its edit
(`saffron/gates/core/witness.py:187-189`). `CellSpec` carries no `depends_on`
(`saffron/cell/session.py:352-418`). `run_task` builds it from the spec
field by field (`saffron/task.py:859-879`), and `intake.Spec` declares
`depends_on` (`saffron/intake.py:244`).

**What reads a survivor after REVIEW**. The post-rebuttal probe selects
survivors by `probe` and `probe_verdict` alone
(`saffron/cell/session.py:3715`). Its verdicts reach
`rebut-probes.json`, `revert-exempt.json` and an infrastructure check
alone (`saffron/cell/session.py:3766-3788`). `rebut._guarded_blockers` keeps a
blocker whose claim opens with a `preserves` criterion's own witness
(`saffron/phases/rebut.py:545-564`). A parent survivor matches no such
prefix unless the child's criterion shares its witness, and keeping a
blocker is the safe direction. Neither reads the survivor's criterion
from `spec.acceptance`.

## Problem

Add `depends_on: list[str]` to `CellSpec`, empty by default, and pass
`spec.depends_on` from `run_task`.

In `_drive_cell`, after the spec's own wrong versions join `pairs`, call
`parent_versions.parent_version_pairs` through the module, so a test's
stub reaches it. Pass `depends_on=spec.depends_on`,
`specs_dir=gates_dir / ".saffron" / "specs"`, `out_dir=out_dir` and
`diff=reviewed_diff`, and append its pairs. After
`_apply_criterion_probes` returns, write `parent-versions.json` and emit
the line when there is a pair or an unread parent. The record is a
mapping with `versions`, the parent entries, and `unread`, the ids.

Add `describe_parent_versions(entries, unread)` to
`saffron/parent_versions.py`, the line the first criterion states.

Give `review.survivor_finding` a keyword `parent: str | None = None`.
With a parent, the claim reads `<parent>'s wrong version` where it reads
`the spec's wrong version` today. Pass `entry.get("parent")` from
`_apply_criterion_probes`. The docstring is at ten lines already, so say
it inside the lines it holds.

## Out of scope

- **A review commit**. #1202 rewrote `SA-0389`'s clause in a review commit, and no cell judged it. `saffron regate` could ask the same versions of a pull request's head. That is a later spec.
- **A fix in REBUT**. The post-rebuttal probe counts kills only among tests the diff adds, and a parent's witness exists at base. Its verdict on a parent survivor reaches no lens verdict.
- **An `error` outcome**. A parent pair the probe cell could not ask counts as chosen and in no other count. No witness drives it.
- **A withdrawn parent survivor**. A lens can withdraw a parent survivor's blocker in REBUT, as it can any survivor of a criterion that is not `preserves`. Guarding it as `_guarded_blockers` guards a `preserves` one is a later spec.
- **The pull request body**. It names no parent outcome and no unread parent, because `saffron/report/**` is forbidden here.
- **`reviewed_diff` against `patch_to_review`**. The session stub exports one patch for both, so no witness tells them apart.
- **Which parents count and which versions**. That is `SA-0401`'s, and this spec forbids its test file.
- **A `retired_first`**. This spec adds no refusal of a spec.
- **Hand edits, made in this spec's own pull request**. `DESIGN.md` §5.4.1, the paragraph on an edit a spec lists in prose, gains three sentences after the one ending `(SA-0396)`.

  > When the diff edits a file a parent's witness names, the host asks
  > that witness each version the parent's own record killed. A survivor
  > names its parent. The REVIEW line counts them chosen, survived,
  > refused and unproven (`SA-0401`, `SA-0402`).

  `CONTEXT.md`'s Wrong version entry gains two sentences after the one
  ending ``That is not a task **Refusal** (`SA-0233`).``

  > A child whose diff edits its parent's witness file is asked the
  > parent's killed versions too. Their outcomes are recorded in
  > `parent-versions.json`, and REVIEW's line counts the refused apart
  > from the unproven (`SA-0402`).

## Notes for the agent

**The behaviour is new code**, so each new criterion declares a witness
and no mutant, and `witness` will report `skip`. The fourth criterion is
`preserves`, and its witness exists at base.

**At base each new witness fails**. Both session witnesses raise
`TypeError` from `_spec(depends_on=...)`, since `CellSpec` has no such
field. The cli witness finds no `depends_on` on `CellSpec`.

**The session witnesses** follow
`test_a_wrong_version_its_witness_survives_is_rebutted_as_a_blocker` in
`tests/test_session.py`. Write the parent specs under
`<root> / "repo" / ".saffron" / "specs"` before `_drive`, since
`_stub_the_export` copies that `.saffron` to `gates_dir`. Write the
records under `<root> / "out" / <id>`. Use `_PROBE_POLICY`, whose test
path is `spec/**`. `_spec` declares `touches` `src/**` and `tests/**`
(`tests/test_session.py:253`), so lib/q.py lies outside them. Pass `_stub_the_runtime` the diff as `patch`, its
file as `changed`, and `gate_cell_suite=[_tests_result("pass", collected=...)]`.
That `collected` holds `t.py::a` and tests/test_p.py::test_guard, and
not `test_gone`. Stub `read_at_head`
so the survivor's `find` is on line 1 of lib/q.py. The survivor is applied
twice, once for its witness and once for the whole `tests` gate. So the
first witness scripts the gate results `fail`, `fail`, `fail`, `pass`,
`pass`. Install the spy with `monkeypatch.setattr` on the
`saffron.parent_versions` module. Spy on `critic_cell` as
`test_a_survivor_the_whole_suite_kills_stays_a_blocker_naming_the_killing_tests` does,
through `saffron.cell.session.critic_cell`. In the second witness drive each cell
under its own `tmp_path` subdirectory, with `_probe_turns()` and no
rebuttal turns.

**The cli witness** sits beside
`test_a_specs_declared_renames_reach_the_cell` in `tests/test_cli.py` and
uses `_ceiling_spec` and `_capture_cell_spec`.

**The `prose` gate** counts each new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words.

**Size**. A prototype on both parents measured 230 changed tokens outside
`tests/` and 1076 under it, about 327 changed lines.
