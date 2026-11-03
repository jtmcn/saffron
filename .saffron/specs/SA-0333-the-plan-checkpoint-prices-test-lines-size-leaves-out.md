---
id: SA-0333
title: "The plan checkpoint prices the test lines that `size` leaves out, so it refuses a plan whose diff `size` would pass"
type: bug
priority: 1
estimated_lines: 60
estimate_measured: true
touches:
  - saffron/agents/artifacts.py
  - saffron/agents/context.py
  - saffron/agents/prompts/implement.md
  - saffron/cell/session.py
  - tests/test_artifacts.py
  - tests/test_context.py
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
  - harness/**
  - records/**
  - hooks/**
  - images/**
  - saffron/gates/**
  - saffron/task.py
  - saffron/intake.py
  - saffron/repos/**
  - saffron/agents/prompts/turns/**
  - tests/test_task.py
  - tests/test_suite.py
  - tests/test_size.py
budget_usd: 44
max_attempts: 3
max_turns: 240
risk: standard
acceptance:
  - claim: >-
      The plan carries a required integer `estimated_test_lines`, from 0 up to
      its `estimated_lines`. `estimated_lines` keeps its whole-diff meaning.
      `validate_plan` raises `PlanNotSchema` for a plan that omits the field,
      and for each of the values `null`, -1, 2.5 and `estimated_lines` plus one. It
      accepts 0 and `estimated_lines` itself, and the returned plan carries the
      value it was given.
    witness: tests/test_artifacts.py::test_a_plan_carries_its_test_lines_within_its_whole_estimate
    wrong_versions:
      - The field defaults to 0, so a plan that omits it is accepted.
      - The field is typed `int | None`, so a plan giving `null` is accepted.
      - The field is checked against 0 alone, so a value above `estimated_lines` is accepted.
      - The upper bound is strict, so a plan whose every line is under a test path is refused.
      - The bound raises a plain `PlanRejected` after validation, so the shape failure gets no re-prompt.
  - claim: >-
      `plan_checkpoint` refuses a plan on its estimate exactly where `size`
      blocks the diff the plan describes. The witness drives a policy whose
      `integrity.test_paths` declares `tests/**` and a policy that declares
      none. In each it drives the four spec types `bug`, `feature`, `refactor`
      and `docs`, the three routes to a tier, and lines outside the test paths
      at the ceiling and one line over. The plan and its diff carry the same
      lines under `tests/`. The checkpoint prices `estimated_lines` less
      `estimated_test_lines` where the policy declares test paths, and the whole
      `estimated_lines` where it declares none. Each rejection carries `size`'s
      own failure message for that diff.
    witness: tests/test_session.py::test_the_plan_checkpoint_leaves_out_the_test_lines_size_leaves_out
    wrong_versions:
      - The checkpoint prices the whole `estimated_lines` as it does at base, so a plan whose lines outside `tests/` sit at the ceiling is refused.
      - The checkpoint subtracts `estimated_test_lines` whatever the policy declares, so a policy with no test paths admits a diff `size` blocks.
      - The checkpoint subtracts only when a hard-coded `tests/**` pattern is present, so it subtracts under the policy that declares none.
      - The rejection names its own token count, priced from the whole estimate, so it no longer carries `size`'s failure message.
  - claim: >-
      Where the repo declares test paths, the rejection and the advisory
      sentence each name the plan's `estimated_test_lines` figure as lines left
      out under them. The advisory sentence names the whole `estimated_lines`
      and the tokens it priced. Where the repo declares none, neither names
      the `estimated_test_lines` figure. The witness drives `judge_estimate` for
      a `bug` plan at `elevated` and at `standard`, under `["tests/**"]` and
      under `[]`.
    witness: tests/test_artifacts.py::test_the_estimate_messages_name_the_test_lines_left_out
    wrong_versions:
      - The messages are unchanged from base, so neither names the test lines left out.
      - Only the rejection names the test lines, and the advisory sentence does not.
      - The advisory sentence names the tokens of the whole estimate rather than the tokens it priced.
      - Both messages name the test lines under a policy with no test paths, though `size` counts them there.
  - claim: >-
      A whole cell reads the test paths from the policy at its base. Its
      IMPLEMENT system prompt's `estimated_test_lines` field names each pattern
      the base policy declares, and its plan checkpoint prices against them.
      The witness drives a base policy declaring `tests/**` and
      `harness/tests/**` under a working-copy policy declaring none. That
      field then names both patterns, and an `elevated` plan over the ceiling
      only by its test lines reaches `READY_FOR_REVIEW`. It also drives a base
      policy declaring none under a working copy declaring `tests/**`. That
      field then names neither pattern, and the same plan ends `PLAN_REJECTED`.
    witness: tests/test_session.py::test_a_cell_names_and_prices_the_test_paths_its_base_policy_declares
    wrong_versions:
      - The cell reads `test_paths` from the working-copy policy, so each half sees the other half's patterns.
      - The prompt is rendered from the policy but the checkpoint is called with no test paths, so the first plan is refused.
      - The checkpoint gets the test paths but the prompt names none, so the model cannot tell which lines to put apart.
      - The prompt names only the first declared pattern.
      - The template carries `tests/**` as fixed example text, so the field names it under a policy that declares none.
  - claim: >-
      The spec author's estimate appended to the cell's body says it counts
      changed lines outside the repo's declared test paths. It names both
      `estimated_lines` and `estimated_test_lines` as the figure to compare it
      with, and no longer calls it the unit `estimated_lines` takes.
    witness: tests/test_context.py::test_the_authors_estimate_is_named_against_the_plans_lines_outside_test_paths
    wrong_versions:
      - The section adds a clause about test paths but keeps calling the figure the unit the plan's own `estimated_lines` takes.
      - The section names `estimated_lines` and leaves out `estimated_test_lines`.
  - claim: >-
      The `estimated_lines` field's own bullet still states its unit in lines,
      names the rate of 4 tokens a line, and says a plan is rejected only where
      `size` blocks.
    witness: tests/test_context.py::test_the_plan_field_says_estimated_lines_counts_lines_not_tokens
    preserves: true
  - claim: >-
      `run_task` still appends the author's estimate to the cell's body in
      lines, never in tokens, and appends nothing for a spec that declares
      none.
    witness: tests/test_task.py::test_run_task_hands_the_cell_the_specs_own_estimate_in_lines
    preserves: true
---

## Context

Backlog item **b-15db6e**, under `DESIGN.md` §5.3 and §5.4. Related: 40.
Every line below was read at `b0bbf178`.

**What `size` counts.** `size_gate` takes the repo's declared test paths
(`saffron/gates/core/size.py:217`). It subtracts every block under one of them
from its total (`saffron/gates/core/size.py:274-281`). The suite passes
`policy.integrity.test_paths` (`saffron/gates/suite.py:214-220`). This repo
declares `["tests/**"]` (`.saffron/policy.yaml:70`). With none declared the
default is `[]` (`saffron/repos/policy.py:75`), and `size` counts every file.

**What the checkpoint prices.** `Plan.estimated_lines` is the only size field
(`saffron/agents/artifacts.py:77-81`). `judge_estimate` prices it whole, at
`_TOKENS_PER_LINE` tokens a line (`saffron/agents/artifacts.py:315`). Its
rejection embeds a copy of `size`'s failure message
(`saffron/agents/artifacts.py:320-327`). Its advisory sentence names the
lines and the priced tokens (`saffron/agents/artifacts.py:331-336`).
`plan_checkpoint` calls it with `elevate_on` alone
(`saffron/cell/session.py:739-741`). The cell's call to the checkpoint
passes `elevate_on=policy.elevate_on` and no test paths
(`saffron/cell/session.py:2449-2457`).

**What the model is told.** The plan's fields are listed once, in the
IMPLEMENT system prompt (`saffron/agents/prompts/implement.md:16-32`). The
`estimated_lines` bullet asks for lines "across the whole diff" and says the
host multiplies the estimate by 4 (`saffron/agents/prompts/implement.md:26-32`).
The plan turn's own prompt and the extraction rules list no field
(`saffron/agents/prompts/turns/plan.md:1-5`,
`saffron/agents/prompts/turns/extraction.md:1-2`). The cell fills the
template through `context.build_system_prompt`
(`saffron/cell/session.py:2382-2399`). That calls `str.format` on each part with
the values it is given (`saffron/agents/context.py:316-320`), so a slot no
caller fills raises `KeyError`.

**What the author's figure says.** `context.estimate_section` calls the spec's
`estimated_lines` "the same unit the plan's own estimated_lines field takes"
(`saffron/agents/context.py:246-248`). A spec author measures that figure with
`size_gate` (`.claude/agents/spec-writer.md:61-64`), which leaves the test
paths out.
`run_task` appends it to the cell's body (`saffron/task.py:775`).

**What it cost.** `SA-0330` ended `PLAN_REJECTED` in run 52 before any code.
Its plan estimated 480 lines across the whole diff, priced at 1920 tokens
against `bug`'s 1300 at `elevated`. Its spec's measured estimate outside tests
was 120 lines.

**The test whose claim goes false.**
`test_the_plan_checkpoint_rejects_an_estimate_exactly_where_size_would_block`
says the checkpoint rejects "exactly where the `size` gate would block the real
diff" (`tests/test_session.py:428-430`). Its policy declares no test paths
(`tests/test_session.py:437-439`), so it stays green while the claim is false
for this repo.

## Problem

1. **The plan carries its test lines apart.** `Plan` gains a required integer
   `estimated_test_lines`, at least 0 and at most `estimated_lines`. Both
   bounds are part of the schema, so a plan outside them is `PlanNotSchema`
   and gets the one re-prompt a shape failure gets
   (`saffron/cell/session.py:717-737`). `estimated_lines` keeps its
   whole-diff meaning.
2. **The checkpoint leaves them out where `size` does.** `judge_estimate`
   and `plan_checkpoint` each take the declared test paths, with no default,
   as they take `elevate_on`. Where the list is non-empty the checkpoint
   prices `estimated_lines` less `estimated_test_lines`. Where it is empty it
   prices the whole `estimated_lines`, since `size` then counts every file.
   `run_one_cell` passes `policy.integrity.test_paths`, from the policy at base
   it already reads `elevate_on` from (`saffron/cell/session.py:2454`). That is the list `suite.py` hands
   `size_gate`. The tier stays `effective_risk` over the plan's whole
   `files_to_change`.
3. **The messages say what was priced.** Where test lines are left out, the
   rejection and the advisory sentence each name how many. The rejection still
   embeds `size`'s failure message for the counted tokens.
4. **The prompt names the paths.** `implement.md` gains an
   `estimated_test_lines` bullet after `estimated_lines`. It says the field
   counts the lines under the repo's declared test paths, and it carries one
   new template slot. `run_one_cell` fills that slot from
   `policy.integrity.test_paths`, through a new function in
   `saffron/agents/context.py`. With patterns declared the rendered text names
   each one. With none it says the repo declares none, so the field is 0. The
   `estimated_lines` bullet's sentence about multiplying by 4 says the test
   lines are taken off first where the repo declares test paths.
5. **The author's figure is compared with the right number.**
   `estimate_section` says the figure counts changed lines outside the repo's
   declared test paths. It names `estimated_lines` less `estimated_test_lines`
   as the plan's figure to compare it with. Its signature stays as it is, so
   `saffron/task.py` needs no edit.

## Out of scope

- `size_gate`, `suite.py` and `effective_risk`. They already count as this spec
  wants.
- A plan's `estimated_test_lines` is the model's own figure. The checkpoint
  does not check it against `files_to_change`, since no diff exists yet.
- `DESIGN.md` §3.2's sentence on the plan's `estimated_lines`
  (`DESIGN.md:246`). It says the checkpoint "refuses a plan it prices over the
  ceiling", which stays true.
- `.claude/agents/spec-writer.md` and the spec loop's `driver.py`. A spec's
  own `estimated_lines` keeps its meaning.
- `SA-0330`, queued, also touches `tests/test_cli.py`. This spec edits one plan
  fixture there (`tests/test_cli.py:5561-5575`) and nothing else.

## Notes for the agent

**Mutants and new code.** Every criterion here is new behaviour whose
spelling the base does not determine. So no criterion declares a mutant, and
the `witness` gate reports `skip` for each. The wrong versions under each
criterion are what REVIEW runs. Do not run them yourself. Criteria 6 and 7
name tests that exist, and both must stay green.

**Callers the new arguments reach.** Each of these breaks until it passes the
new value. They are in `touches`.

- `plan_checkpoint` is called directly from `tests/test_session.py`, through
  `_checkpoint_plan` (`tests/test_session.py:385-397`) and at a dozen other
  sites. Each passes `elevate_on=` today. Pass an empty list where the test
  is not about test paths.
- `judge_estimate` is called in `tests/test_artifacts.py` at each site that
  passes `elevate_on` as `[]`.
- The new template slot is filled by four test call sites of
  `build_system_prompt` over `implement.md`. They are
  `tests/test_context.py:455-463`, `:469-477` and `:621-629`, and
  `tests/test_session.py:2222-2231`. The last asserts the assembled prompt
  equals the cell's own, so fill it the way `run_one_cell` does for a policy
  with no test paths.

**Plan fixtures.** Three fixtures carry a plan's fields and need the new one:
`_plan` (`tests/test_artifacts.py:22-35`), `_PLAN`
(`tests/test_session.py:332-340`), and the plan in
`tests/test_cli.py:5561-5575`. That last test expects a `protected` rejection,
and a plan missing the new field fails the schema before it is read.

**Criterion 2's witness.** Build it on the existing test's shape
(`tests/test_session.py:428-474`), with `GateSuite` and `tests.test_suite._Tree`.
Give `Policy` an `integrity` with `test_paths=["tests/**"]` for one half, and
none for the other. The diff needs two file blocks, one under `tests/` and one
outside it, so that `size` subtracts the first. Keep the existing test as it
is. It is the no-test-paths case, and the new witness covers both.

**Criterion 3's witness.** Pick an `estimated_test_lines` figure that no other
number in either message contains, and match it as a whole word.

**Criterion 4's witness.** `_drive` takes a working-copy `policy` and a
`base_policy` (`tests/test_session.py:1381-1406`).
`test_the_cell_goes_on_past_an_advisory_estimate_and_stops_where_size_blocks`
(`tests/test_session.py:529-599`) is the nearest shape, and `elevate_on:
["infra/**"]` with a plan naming `infra/deploy.tf` puts the plan at
`elevated`. Read the prompt from `cell.system_prompts[0]`. Read the
`estimated_test_lines` field from its own bullet up to the next field. The
constraints block lists the spec's `touches`, so a whole-prompt search for
`tests/**` finds it there. This arrangement was run against a prototype of the
change. Both halves held, and with the source reverted the first half failed.

**The new rendering function.** Do not start its name with `test_`. A test
module that imports it by name would have pytest collect it as a test.

**Coercion.** The new field takes the same lax integer validation
`estimated_lines` takes (`saffron/agents/artifacts.py:77`). So `2.5` fails it,
and a string of digits passes. Criterion 1 claims nothing about strings.

**Each new test must fail with the source reverted.** At base `Plan` ignores
an unknown key, so a plan carrying `estimated_test_lines` validates there. A
witness that only checks acceptance passes at base. Each witness above turns
on a refusal or a price that only the change produces. Import any name the
change adds inside the test function, never at module scope.

**Prose.** `implement.md` is in the `prose` gate's scope
(`tests/test_prose_gate.py:430-440`). New lines there and new docstrings take
no em-dash, semicolon, contraction or sentence over 25 words. The existing
`estimated_lines` bullet test reads each sentence that names a token
(`tests/test_context.py:547-591`). Keep every such sentence inside one of the
shapes it allows.
