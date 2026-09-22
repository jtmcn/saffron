---
id: SA-0125
title: The plan checkpoint rejects an estimate over a ceiling that the `size` gate would not have enforced
type: feature
priority: 2
touches:
  - saffron/agents/artifacts.py
  - saffron/cell/session.py
  - saffron/gates/suite.py
  - saffron/events.py
  - tests/test_artifacts.py
  - tests/test_session.py
  - tests/test_events.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
  - README.md
  - pyproject.toml
  - uv.lock
  - .saffron/**
  - ontology/**
  - tests/ontology/**
  - docs/**
  - images/**
  - harness/**
  - saffron/agents/prompts/**
  - saffron/gates/core/**
  - saffron/repos/**
  - saffron/phases/**
  - saffron/record/**
  - saffron/report/**
  - saffron/cell/worktree.py
  - saffron/cell/runtime.py
  - saffron/ledger.py
  - saffron/intake.py
  - saffron/task.py
  - saffron/cli.py
  - tests/test_suite.py
  - tests/test_cli.py
  - tests/test_ledger.py
  - tests/test_ledger_fold_task.py
  - tests/test_fold.py
  - tests/test_package.py
  - tests/test_scheduler.py
budget_usd: 22
max_attempts: 3
max_turns: 150
risk: elevated
acceptance:
  - claim: >-
      The plan checkpoint rejects a plan on its estimate exactly where the
      `size` gate would block the diff. The witness drives four spec types,
      `bug`, `feature`, `refactor` and `docs`. For each it drives three ways
      to a tier. One is a `standard` spec whose plan names no `elevate_on`
      path. One is a spec declaring `elevated`. One is a `standard` spec whose
      plan names an `elevate_on` path second, after a test file. Each runs
      with the estimate at the
      type's ceiling and one line over it. For each of the 24 cases a
      `GateSuite`, under the same spec and policy, judges a diff of that many
      changed lines over the plan's files. It must report a new `size`
      failure in exactly the 8 cases that are over the ceiling and elevated.
      The plan checkpoint rejects the plan in those 8 cases and accepts it in
      the other 16. Each rejection's message holds that `size` failure's own
      message, and names the `size` gate and `elevated`.
    witness: tests/test_session.py::test_the_plan_checkpoint_rejects_an_estimate_exactly_where_size_would_block
    mutant:
      file: saffron/repos/policy.py
      find: "if matches(path, pattern):"
      replace: "if False:"
  - claim: >-
      Where `size` is advisory, the plan checkpoint records the overrun and
      the plan stands. A `feature` plan estimating 20 lines over its ceiling,
      at `standard` and naming no `elevate_on` path, is accepted in one turn.
      The checkpoint emits exactly one event for it. That event renders as a
      `PLAN:` line naming the estimate, the ceiling, the `size` gate, the word
      advisory, and `standard` as the tier from the plan's files. A plan
      estimating exactly the ceiling emits no event at all.
    witness: tests/test_session.py::test_an_estimate_over_an_advisory_ceiling_is_recorded_and_the_plan_stands
    mutant:
      file: saffron/repos/policy.py
      find: "    return spec_risk"
      replace: '    return "elevated"'
  - claim: >-
      A whole cell reads `elevate_on` from the policy at base. The witness
      drives `run_one_cell` twice. The policy at base has an `elevate_on`
      naming one directory, and the working copy's policy names none. Each
      run has a `feature` plan 20 lines over the ceiling. The plan naming no
      path in that directory reaches the IMPLEMENT turn. That task does not
      end `PLAN_REJECTED`, and its watch lines carry the advisory `PLAN:`
      line. The plan naming a path in that directory, second after a test
      file, ends `PLAN_REJECTED` after one turn. Its `PLAN: rejected` line
      names the ceiling and `elevated`. Its outcome reports `elevated` as the
      effective risk, the tier from the plan's files, never the baseline's
      `standard`.
    witness: tests/test_session.py::test_the_cell_goes_on_past_an_advisory_estimate_and_stops_where_size_blocks
    mutant:
      file: saffron/repos/policy.py
      find: "if matches(path, pattern):"
      replace: "if False:"
  - claim: >-
      One function decides whether `size` blocks at a tier, and both of its
      readers call it. `size_blocks` in the gate suite module is public.
      `_advisory` calls it, and so does `judge_estimate` in the artifacts
      module, which judges a plan's estimate. The witness reads each
      caller's source as a syntax tree and finds a call to `size_blocks` in
      both.
    witness: tests/test_artifacts.py::test_the_advisory_set_and_the_plan_checkpoint_ask_one_function_whether_size_blocks
---

## Context

Backlog item **b-408cf5**, found in the spec loop's run 9 and again in run
11. It cost `SA-0110` a whole cell. The plan checkpoint is `DESIGN.md` §5.3.
The `size` gate and its ceilings are §5.4, and the risk tier that makes it
blocking is §5.6.

Every sentence below about current code was read at `5edfefef` on
2026-09-22, and re-read at `0531fcd7`, which changes no source.

**The checkpoint rejects on the ceiling at every tier.**

- `validate_plan` ends with the ceiling check
  (`saffron/agents/artifacts.py:288-294`). It reads the ceiling from
  `size`'s own table, imported at `saffron/agents/artifacts.py:21`. Any
  estimate over it raises `PlanRejected`, whose message says the `size`
  gate "will fail on" the diff.
- `validate_plan` takes `touches`, `forbidden`, `protected` and
  `spec_type` (`saffron/agents/artifacts.py:243-250`). It knows no tier.
- `plan_checkpoint` calls it at `saffron/cell/session.py:506-513` and
  discards the returned `Plan`. Its signature is at
  `saffron/cell/session.py:433-441`. It already holds `spec.risk` through
  `CellSpec.risk` (`saffron/cell/session.py:267`), and no `elevate_on`.
- `_drive_cell` loads the policy at `saffron/cell/session.py:1612`. It
  calls `plan_checkpoint` at `saffron/cell/session.py:1792-1799`, passing
  `policy.protected` alone.
- A `PlanRejected` ends the task `PLAN_REJECTED`, through a `Terminal`
  event whose detail is the message
  (`saffron/cell/session.py:1855-1875`). `describe` renders it as
  `PLAN: rejected, $N spent` and the detail
  (`saffron/events.py:830-833`).
- That branch reports the baseline's tier. `latest` is bound to the
  baseline suite (`saffron/cell/session.py:1698`), and the `PLAN_REJECTED`
  outcome takes `effective_risk=latest.effective_risk`
  (`saffron/cell/session.py:1873`). `run_task` writes that tier into the
  task's queue line (`saffron/task.py:377`). The baseline's diff is empty,
  so a task elevated only by a path in its plan is listed `standard`.

**The gate blocks only at `elevated`.**

- `GateSuite._run` computes the tier from the spec's risk and the run's
  changed files, with `effective_risk` (`saffron/gates/suite.py:145`).
- `_advisory` adds `size` to the advisory set unless that tier is
  `elevated` (`saffron/gates/suite.py:212-220`).
- `effective_risk` returns `elevated` in two cases
  (`saffron/repos/policy.py:93-111`). The spec declares it, or a changed
  path matches an `elevate_on` pattern.
- The gate's failure message is built at
  `saffron/gates/core/size.py:196-199`, and the ceilings sit at
  `saffron/gates/core/size.py:25` and `:34`.

**The prompt repeats the false half.** The plan instructions say a plan over
the ceiling "is rejected" (`saffron/agents/prompts/implement.md:26-29`).
This spec leaves that sentence alone, as Out of scope says.

## Problem

`SA-0110` touched `records/` and `tests/records/`, which elevate nothing. Its
plan estimated 620 lines against the `feature` ceiling of 600. The
checkpoint ended the task at `PLAN_REJECTED` for $1.20 with nothing edited.
At `standard`, `size` would have held that diff advisory. `SA-0115`'s cell
later spent its turn wall compacting toward 600 for the same reason.

At plan time no diff exists. The plan's `files_to_change` is the nearest
thing to one, and `validate_plan` already judges it against `touches`. So
the checkpoint computes the tier from `spec.risk`, the plan's
`files_to_change` and the policy's `elevate_on`, through `effective_risk`.

1. **Reject only where `size` blocks.** Over the ceiling and `elevated`,
   the plan is rejected. The message holds the sentence the `size` gate
   would fail the diff with, and names `size` and `elevated`.
2. **Record where `size` is advisory.** Over the ceiling and not
   `elevated`, the plan stands. The checkpoint emits one `PhaseStart` with
   label `PLAN`, naming the estimate, the ceiling, the `size` gate, the word
   advisory and the tier. The line calls the tier the one from the plan's
   files, since it is a forecast. Then the task goes on.
3. **Say nothing within the ceiling.** An estimate at or under it emits no
   such event.
4. **One rule decides where `size` blocks.** Add a public function
   `size_blocks` to `saffron/gates/suite.py`, taking a tier and answering
   whether `size` blocks at it. `_advisory` calls it in place of its own
   comparison. The estimate check lives in a new function `judge_estimate`
   in `saffron/agents/artifacts.py`, and it calls `size_blocks` too.
   Criterion 4 reads both by name.
5. **Wire `elevate_on` in.** `plan_checkpoint` gains a required keyword for
   the policy's `elevate_on`, and `_drive_cell` passes `policy.elevate_on`.
6. **Name the new line.** `FAMILIES` in `saffron/events.py` gains one row
   for the advisory line, citing `plan_checkpoint` through `_PC`. The count
   `tests/test_events.py:1217-1218` pins moves from 63 to 64.
7. **Report the plan's tier on a rejection.** Take a plan rejected because
   `size` blocks. Its outcome's `effective_risk` is the tier from the plan's
   files. Every other `PLAN_REJECTED` keeps the baseline's
   tier, as today.

## Out of scope

- **The prompt's sentence, a follow-up.** `saffron/agents/prompts/implement.md:26-29`
  stays as it is, and the file is `forbidden`. A diff under
  `saffron/agents/prompts/` needs a measured pass that a cell cannot run
  (`.github/pull_request_template.md`). After this change the sentence
  overstates the rule at `standard`. It errs toward smaller plans, which is
  safe. Rewrite it by hand once this spec merges.
- **The plan-time tier is a forecast, and `size` at GATE is the judgement.**
  `GateSuite._run` takes its tier from the diff's changed files
  (`saffron/gates/suite.py:142-145`). The checkpoint takes it from the
  plan's `files_to_change`. The two differ when the diff and the plan name
  different files. A diff that edits an `elevate_on` path its plan omitted
  records the advisory line and then blocks on `size`. A plan naming an
  `elevate_on` path its diff never edits is rejected where `size` would not
  block. This spec does not reconcile them.
- **The outcome's `advisory_gates` on a rejection.** It stays the
  baseline's. A `PLAN_REJECTED` task never reaches PACKAGE, where the set
  is read (`saffron/phases/package.py:826`).
- **The estimate as an instrument.** The item notes that one scope drew
  estimates of 620 and 520 from two cells. Replacing the estimate is a
  separate question. This spec changes only when it is enforced.
- **Telling the implementer its tier.** The advisory line reaches the event
  log and the operator, and not the agent.
- **`size`'s counting and its ceilings.** `saffron/gates/core/**` is
  `forbidden`. `SA-0128` changes the unit and re-measures the ceilings,
  stacked on this spec.
- **`plan.json`.** It stays the raw block verbatim, so its hash stays
  re-derivable (`saffron/cell/session.py:1899-1906`). The advisory line is
  an event, never a field in the artifact.
- **`DESIGN.md` §5.3.** Its list of automatic rejections omits the estimate
  already, so nothing there turns false. It is `protected` in any case.
- **The scope proposal door and the other plan rules.** Leave
  `validate_scope_proposal` and every other check in `validate_plan` as
  they are.

## Notes for the agent

**Mutants.** Criteria 1 to 3 each declare a mutant in
`saffron/repos/policy.py`, which is `forbidden`. The file's text is fixed, so
each mutant applies exactly once. The mutants of criteria 2 and 3 are killed only if the
checkpoint computes its tier through `effective_risk`. A copy of that
function's matching, written beside the checkpoint, survives both. Criterion
1's mutant is killed through the witness's own count of `size` failures,
whatever the checkpoint does. That count is what makes the witness's
agreement mean something, as the notes on criterion 1 say.

Criterion 4 declares a witness and no mutant, because its change is new
code. Both `size_blocks` and `judge_estimate` are new, and so is the call in
`_advisory`, whose spelling this spec cannot know. `witness` reports `skip`
for it, and that skip is honest.

**Commit as each witness passes.** A long cell can reach its turn limit
before its first commit.

**The shape.** Keep `validate_plan`'s signature, and move the ceiling check
out of it into `judge_estimate`. It takes the validated `Plan`, the spec
type, the spec's risk and `elevate_on`. It returns `None` within the
ceiling. Over the ceiling it raises `PlanRejected` where `size_blocks`
says so, and otherwise returns the advisory sentence. `plan_checkpoint`
keeps the `Plan` that `validate_plan` returns, calls `judge_estimate` after
it, and emits the sentence when there is one. Place the call inside the
checkpoint's existing `try`, so a rejection gets its spend set at
`saffron/cell/session.py:543-548`.

For Problem item 7, the prototype gave `PlanRejected` a class attribute
beside `spent_usd`, defaulting to `None`. `judge_estimate` sets it to the
tier on the rejection it raises. The `PLAN_REJECTED` branch reports that
tier when it is set, and `latest.effective_risk` otherwise.

This shape keeps the 16 existing `validate_plan` calls in
`tests/test_artifacts.py`, and `tests/test_cli.py:2438`, as they are. Adding
keywords to `validate_plan` instead changes every one of them, and
`tests/test_cli.py` is `forbidden`.

**The three existing ceiling tests change body and keep their names.** They
are `tests/test_artifacts.py:176`, `:187` and `:198`. Each still passes a plan
through `validate_plan`. Each then judges its estimate with `judge_estimate`
at `elevated`. `census` fails a test that disappears, so rename nothing.
Import the new function inside each test body, never at module scope.

**The ten existing `plan_checkpoint` calls gain the new keyword.** They are
in `tests/test_session.py` at `:282`, `:301`, `:314`, `:338`, `:351`,
`:376`, `:395`, `:415`, `:470` and `:3517`. Pass an empty list.

**Criterion 1's witness.** Build each `GateSuite` from the helpers in
`tests/test_suite.py`. Import `_Tree` and `_Spec` from `tests.test_suite`
inside the test body. Use one declared gate, `lint`, so `revert` does not
run. Give the policy `elevate_on=["infra/**"]` and the spec
`touches=["src/**", "infra/**", "tests/**"]`. The plan names
`["src/x.py", "tests/test_x.py"]`, or `["tests/test_x.py", "infra/deploy.tf"]`
on the path route. Keep the `infra/` path second. A tier read from the
first file alone passes when it comes first. The head tree's changed files are the plan's files. Its
patch is one file block with one hunk header, then one added line of code
per changed line counted. Judge it with `suite.against(head,
suite.baseline(_Tree()))`. Drive the checkpoint with `_agent` and `_block`
from `tests/test_session.py:238` and `:276`, and `_spec` from `:142`, with
the same risk, touches and type. Read each ceiling from `_CEILINGS` and
`_DEFAULT_CEILING`, never as a literal. `SpecType` has six members
(`saffron/intake.py:25`). `test` and `chore` take `_DEFAULT_CEILING` as
`docs` does (`saffron/gates/core/size.py:34`), so `docs` stands for all three.

Call the checkpoint through a module-level helper that takes the spec, the
plan and `elevate_on` as arguments. The prototype first splatted a `dict` of
keywords, and the `types` gate refused it. A closure over the loop variables
then failed `lint` (B023).

Assert the count of `size` new failures for every case. That assertion is
what stops a fixture whose patch the gate never counts. Without it, a
checkpoint that never rejects would pass. Then assert that the failure's
`message` is a substring of the rejection's text.

**Criteria 2 and 3 read the ceiling from `_CEILINGS["feature"]`.** Its
number is `SA-0128`'s to change. Criterion 2 drives `plan_checkpoint` with
`emit` collecting events, and renders each with `describe`. Criterion 3
drives `_drive` (`tests/test_session.py:966`) with `_stub_the_runtime`, once
per plan, each into its own subdirectory of `tmp_path`. Pass the policy with
`elevate_on` through `_drive`'s `base_policy` argument, and leave `policy`
at its default, which names none. `_stub_the_export`
(`tests/test_session.py:945-952`) copies the working copy's policy unless
`base_policy` overrides it, so only this split fails a working-copy read.
Pass the wider `touches` through `spec`, and list the `infra/` path second.
Script the plan turn and one more `_turn()`. Count the turns in
`cell.turns`, read the lines from `cell.watched`, and read
`outcome.effective_risk` on the rejected run.

**Criterion 4's witness** follows `_source_calls` at
`tests/test_cli.py:2260-2295`. It parses `inspect.getsource` of
`suite._advisory` and of `artifacts.judge_estimate`, walks each tree for an
`ast.Call` whose name is `size_blocks`, and asserts one in each. Import both
modules inside the test body. At base `judge_estimate` does not exist, so
the witness fails there with an `AttributeError`, not a collection error.

**A prototype of this change ran at this base.** It followed the shape
above, and all four witnesses passed. With the source reverted, all four
failed. Both mutants were killed. The one criteria 1 and 3 declare failed
those two witnesses. The one criterion 2 declares failed criteria 1, 2
and 3. These wrong implementations were killed too:

- a tier from `spec.risk` alone: criteria 1 and 3 failed
- `_drive_cell` passing an empty `elevate_on`: criterion 3 failed
- an estimate equal to the ceiling judged as over it: criteria 1 and 2 failed
- no advisory event: criteria 2 and 3 failed
- a rejection that does not name the tier: criteria 1 and 3 failed
- a tier computed from the spec's `touches` in place of the plan's files:
  criteria 1 to 3 failed
- a tier read from the plan's first file only: criteria 1 and 3 failed
- `_drive_cell` reading `elevate_on` from the working copy's policy:
  criterion 3 failed
- the rejection branch keeping the baseline's tier: criterion 3 failed
- `_advisory` keeping its own comparison: criterion 4 failed
- `judge_estimate` with its own copy of the comparison: criterion 4 failed
- an advisory line that does not name the plan's files: criterion 2 failed

**Size.** The prototype measured 271 changed lines before docstrings: 147 in
`tests/test_session.py`, 58 in `tests/test_artifacts.py`, 36 in
`saffron/agents/artifacts.py`, 18 in `saffron/cell/session.py`, 7 in
`saffron/gates/suite.py`, and 5 across the two event files. Expect about 315
with docstrings. The `feature` ceiling is 600, and `size` blocks at `elevated`,
which `saffron/cell/session.py` makes this task.

**Prose.** Each touched file's `prose` count must not rise. New comments and
docstrings take no em-dash, semicolon, contraction, perfect tense or hedge.
Keep a docstring within ten lines and a comment within two. Check each file with
`python3 hooks/prose_limit.py --file <path>`.
