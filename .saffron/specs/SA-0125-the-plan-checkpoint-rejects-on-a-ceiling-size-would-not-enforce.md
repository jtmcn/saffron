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
max_turns: 130
risk: elevated
acceptance:
  - claim: >-
      The plan checkpoint rejects a plan on its estimate exactly where the
      `size` gate would block the diff. The witness drives four spec types,
      `bug`, `feature`, `refactor` and `docs`. For each it drives three ways
      to a tier. One is a `standard` spec whose plan names no `elevate_on`
      path. One is a spec declaring `elevated`. One is a `standard` spec whose
      plan names an `elevate_on` path. Each runs with the estimate at the
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
      advisory, and `standard`. A plan estimating exactly the ceiling emits no
      event at all.
    witness: tests/test_session.py::test_an_estimate_over_an_advisory_ceiling_is_recorded_and_the_plan_stands
    mutant:
      file: saffron/repos/policy.py
      find: "    return spec_risk"
      replace: '    return "elevated"'
  - claim: >-
      A whole cell reads `elevate_on` from the policy at base. The witness
      drives `run_one_cell` twice under a policy whose `elevate_on` names one
      directory, each with a `feature` plan 20 lines over the ceiling. The
      plan naming no path in that directory reaches the IMPLEMENT turn. That
      task does not end `PLAN_REJECTED`, and its watch lines carry the
      advisory `PLAN:` line. The plan naming a path in that directory ends
      `PLAN_REJECTED` after one turn. Its `PLAN: rejected` line names the
      ceiling and `elevated`.
    witness: tests/test_session.py::test_the_cell_goes_on_past_an_advisory_estimate_and_stops_where_size_blocks
    mutant:
      file: saffron/repos/policy.py
      find: "if matches(path, pattern):"
      replace: "if False:"
---

## Context

Backlog item **b-408cf5**, found in the spec loop's run 9 and again in run
11. It cost `SA-0110` a whole cell. The plan checkpoint is `DESIGN.md` §5.3.
The `size` gate and its ceilings are §5.4, and the risk tier that makes it
blocking is §5.6.

Every sentence below about current code was read at `5edfefef` on
2026-09-22.

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
   advisory and the tier. Then the task goes on.
3. **Say nothing within the ceiling.** An estimate at or under it emits no
   such event.
4. **One rule decides where `size` blocks.** `_advisory` and the checkpoint read
   the same predicate from `saffron/gates/suite.py`. Expose it there as a
   public function, and have `_advisory` call it.
5. **Wire `elevate_on` in.** `plan_checkpoint` gains a required keyword for
   the policy's `elevate_on`, and `_drive_cell` passes `policy.elevate_on`.
6. **Name the new line.** `FAMILIES` in `saffron/events.py` gains one row
   for the advisory line, citing `plan_checkpoint` through `_PC`. The count
   `tests/test_events.py:1217-1218` pins moves from 63 to 64.

## Out of scope

- **The prompt's sentence, a follow-up.** `saffron/agents/prompts/implement.md:26-29`
  stays as it is, and the file is `forbidden`. A diff under
  `saffron/agents/prompts/` needs a measured pass that a cell cannot run
  (`.github/pull_request_template.md`). After this change the sentence
  overstates the rule at `standard`. It errs toward smaller plans, which is
  safe. Rewrite it by hand once this spec merges.

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

**Mutants.** Every criterion declares a mutant in `saffron/repos/policy.py`,
which is `forbidden`. The file's text is fixed, so each mutant applies
exactly once. The mutants of criteria 2 and 3 are killed only if the
checkpoint computes its tier through `effective_risk`. A copy of that
function's matching, written beside the checkpoint, survives both. Criterion
1's mutant is killed through the witness's own count of `size` failures,
whatever the checkpoint does. That count is what makes the witness's
agreement mean something, as the notes on criterion 1 say.

**Commit as each witness passes.** A long cell can reach its turn limit
before its first commit.

**A suggested shape.** Keep `validate_plan`'s signature, and move the ceiling
check out of it into a new function in `saffron/agents/artifacts.py`. It
takes the validated `Plan`, the spec type, the spec's risk and
`elevate_on`. It returns `None` within the ceiling. Over the ceiling it
raises `PlanRejected` where `size` blocks, and otherwise returns the
advisory sentence. `plan_checkpoint` keeps the `Plan` that `validate_plan`
returns, calls the new function after it, and emits the sentence when there
is one. Place the call inside the checkpoint's existing `try`, so a
rejection gets its spend set at `saffron/cell/session.py:543-548`.

This shape keeps the 16 existing `validate_plan` calls in
`tests/test_artifacts.py`, and `tests/test_cli.py:2438`, as they are. Adding
keywords to `validate_plan` instead changes every one of them, and
`tests/test_cli.py` is `forbidden`.

**The three existing ceiling tests change body and keep their names.** They
are `tests/test_artifacts.py:176`, `:187` and `:198`. Each still passes a plan
through `validate_plan`. Each then judges its estimate with the new function
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
`["src/x.py", "tests/test_x.py"]`, or `["infra/deploy.tf", "tests/test_x.py"]`
on the path route. The head tree's changed files are the plan's files. Its
patch is one file block with one hunk header, then one added line of code
per changed line counted. Judge it with `suite.against(head,
suite.baseline(_Tree()))`. Drive the checkpoint with `_agent` and `_block`
from `tests/test_session.py:238` and `:276`, and `_spec` from `:142`, with
the same risk, touches and type. Read each ceiling from `_CEILINGS` and
`_DEFAULT_CEILING`, never as a literal.

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
per plan, each into its own subdirectory of `tmp_path`. Pass the policy as
YAML through `_drive`'s `policy` argument, and the wider `touches` through
`spec`. Script the plan turn and one more `_turn()`. Count the turns in
`cell.turns`, and read the lines from `cell.watched`.

**A prototype of this change ran at this base.** It followed the suggested
shape, and all three witnesses passed. With the source reverted, all three
failed. Both mutants were killed. The one criteria 1 and 3 declare failed
those two witnesses. The one criterion 2 declares failed all three. These
wrong implementations were killed too:

- a tier from `spec.risk` alone: criteria 1 and 3 failed
- `_drive_cell` passing an empty `elevate_on`: criterion 3 failed
- an estimate equal to the ceiling judged as over it: criteria 1 and 2 failed
- no advisory event: criteria 2 and 3 failed
- a rejection that does not name the tier: criteria 1 and 3 failed
- a tier computed from the spec's `touches` in place of the plan's files:
  all three failed

One wrong implementation passes all three. It is a second copy of "`size`
blocks only at `elevated`" in the checkpoint. It behaves identically, and
only item 4 of the Problem forbids it.

**Size.** The prototype measured 234 changed lines before docstrings: 138 in
`tests/test_session.py`, 39 in `tests/test_artifacts.py`, 29 in
`saffron/agents/artifacts.py`, 16 in `saffron/cell/session.py`, 7 in
`saffron/gates/suite.py`, and 5 across the two event files. Expect about 275 with
docstrings. The `feature` ceiling is 600, and `size` blocks at `elevated`,
which `saffron/cell/session.py` makes this task.

**Prose.** Each touched file's `prose` count must not rise. New comments and
docstrings take no em-dash, semicolon, contraction, perfect tense or hedge.
Keep a docstring within ten lines and a comment within two. Check each file with
`python3 hooks/prose_limit.py --file <path>`.
