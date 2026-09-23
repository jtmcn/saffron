---
id: SA-0130
title: The IMPLEMENT prompt never says who runs wrong versions of the change, so a cell spends its turn bound running the ones its spec lists
type: bug
priority: 3
depends_on: []
touches:
  - saffron/agents/prompts/implement.md
  - tests/test_context.py
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
  - saffron/cell/**
  - saffron/phases/**
  - saffron/agents/context.py
  - saffron/agents/prompts/turns/**
  - saffron/agents/prompts/criterion-probe.md
  - saffron/agents/prompts/rebut-verdict.md
  - saffron/agents/prompts/review-adequacy.md
  - saffron/agents/prompts/review-contract.md
  - saffron/agents/prompts/review-correctness.md
  - tests/test_session.py
  - tests/test_scheduler.py
budget_usd: 12
max_attempts: 3
max_turns: 60
acceptance:
  - claim: >-
      The IMPLEMENT system prompt, assembled from `implement.md` and
      `CONTEXT.md` by `build_system_prompt`, carries a paragraph of its own
      that names mutants, the `witness` gate, REVIEW and the host. The
      paragraph sits outside the injected vocabulary and the task body. It holds for a spec that
      declares acceptance criteria and for one that declares none.
    witness: tests/test_context.py::test_the_implement_prompt_leaves_running_wrong_versions_to_the_host
---

## Context

Backlog item **b-2dea1c**, the half that tells the implementer. The other
half is the spec-writer's convention in `docs/agents/issue-tracker.md`,
landed by hand in #464: a spec names the wrong versions its witnesses must
kill, and never asks the cell to run them.

Run 14 found it on `SA-0123`. That spec's notes asked its cell to run each
new witness against wrong versions of the change, and to report what each
run printed
(`.saffron/specs/done/SA-0123-the-write-methods-keep-their-own-sql-beside-apply.md:387-391`).
The cell's IMPLEMENT turn and its first REPAIR turn were both cut by the
wall bound. That was read from the cell's `events.jsonl` on the host on
2026-09-22 and is recorded in the item, so it cannot be read at base. That
bound is `TURN_TIMEOUT_S = 900.0` (`saffron/cell/session.py:63`, §4.3). The
item records the rest: IMPLEMENT spent $4.17, and the task ended `EXHAUSTED`
at $38.20.

The host already runs two kinds of wrong version outside the agent's turn,
and neither is a list in a spec's prose. The `witness`
gate applies each criterion's declared mutant and runs its witness
(`saffron/gates/core/witness.py:8-13`, §5.4.1). REVIEW asks one fresh session
per criterion for an edit that breaks the claim
(`saffron/agents/prompts/criterion-probe.md:1-3`,
`saffron/phases/review.py:423-469`). The host applies each edit and runs
that criterion's witness in a gate-only cell
(`saffron/cell/session.py:1395-1414`).

The IMPLEMENT system prompt is assembled once, at
`saffron/cell/session.py:1748-1762`. It reads
`saffron/agents/prompts/implement.md` and passes it to
`context.build_system_prompt` (`saffron/agents/context.py:174-198`) with the
IMPLEMENT sections of `CONTEXT.md` as `{vocabulary}` and the spec body as
`{spec}`. The plan turn (`saffron/cell/session.py:463`), the implement turn
(`saffron/cell/session.py:1958`) and each REPAIR turn
(`saffron/cell/session.py:2203`) all run under that one string. The salvage
turn is handed it too (`saffron/cell/session.py:2020`).

## Problem

Nothing the implementer reads says who runs a spec's wrong versions. Step 3
of `implement.md` says the host runs the gates, and that running the suite
is ordinary development (`saffron/agents/prompts/implement.md:60-63`). It
says nothing about a list of wrong versions in the task body. So when a
spec's notes ask for those runs, the agent does them inside its own turn,
one test run per wrong version. The wall bound on that turn gives no warning
(`saffron/agents/prompts/implement.md:50-53`).

`CONTEXT.md` defines **Mutant** in the IMPLEMENT vocabulary
(`CONTEXT.md:347-348`), and that definition says the `witness` gate
applies one. It says nothing about the wrong versions a spec's notes list, and it tells
the agent nothing about its own turn.

## Out of scope

- **Measurement.** `.github/pull_request_template.md:35-38` asks a diff
  reaching `saffron/agents/prompts/` for a measured pass, and records an
  effect below the noise floor as unmeasured. No pass is in scope here, so
  this change's effect on cells is recorded as unmeasured. PACKAGE renders
  this task's pull request body from the ledger and skips that template
  (`.github/pull_request_template.md:2-4`).
- **The sense of the sentence.** The witness pins where the paragraph sits
  and the four things it names. It cannot tell a paragraph that tells the
  agent not to run the listed wrong versions from one that tells it to.
  REVIEW's lenses read that.
- **A host run of the wrong versions a spec lists in prose.** Nothing runs
  those today, and this spec adds nothing that would.
- **The turns and the call site.** The witness calls
  `build_system_prompt` the way `saffron/cell/session.py:1750-1762` does, and
  drives no cell. So it does not observe which turns run under the string,
  or that `session.py` still reads `implement.md`. At base the plan,
  implement, REPAIR and salvage turns all run under it
  (`saffron/cell/session.py:463`, `:1958`, `:2203`, `:2020`). This spec
  forbids `saffron/cell/**`, so the cell cannot change that.
- **The spec-writer's half**, which #464 lands by hand in `docs/agents/`.
- **Every other prompt.** The lens, verdict and probe prompts and the turn
  prompts stay as they are. A criterion probe exists to name a wrong version,
  so telling it that is not its job would be wrong.

## Notes for the agent

**Where the text goes.** Add it to `saffron/agents/prompts/implement.md`,
under `## How this phase works`, beside step 3. That file is the system
prompt, so every turn of the session carries it. A turn prompt under
`prompts/turns/` reaches one turn only, as a user message, and the witness
reads the system prompt.

**What it says.** Three facts, in one paragraph.

- The host's `witness` gate applies each mutant a criterion declares, and
  runs that criterion's witness against it.
- REVIEW names further wrong versions of the change, and the host runs
  them. It skips a vacuity probe that edits a declared test path
  (`CONTEXT.md:358-359`), so say "runs them" without "every".
- The implementer does not run the wrong versions its task text lists. That
  holds even for a task text that asks it to. Its turn is for making the
  witnesses and the change pass.

Keep "mutant" for the declared edit. That is what `CONTEXT.md:347` defines
it as, and a wrong version a spec lists in prose is not one. Name REVIEW in
bare caps and the gate as `witness` in backticks, as the vocabulary does.
Keep it to one paragraph: the witness reads one.

**Leave the single run against unfixed code standing.** The same system
prompt carries this repo's `CLAUDE.md` as standing instructions
(`saffron/cell/session.py:1605`). Its `CLAUDE.md:217-218` trusts a new test only
after a run against the unfixed code. The wrapper says
the prompt's other rules win on disagreement (`saffron/agents/context.py:149`).
So word the third fact to cover only the wrong versions a task text lists. A
broader sentence would override that one run, which each new witness needs.
`CLAUDE.md` is forbidden, so the paragraph is worded around it.

**Prose rules bind this file.** The `prose` gate reaches
`saffron/agents/prompts/implement.md` (`tests/test_prose_gate.py:338`), and
it fails a file that gains a hit. So the new text takes no em-dash,
semicolon, contraction, perfect tense or sentence over 25 words. It takes no hedge either, and `may` counts as one
(`.saffron/gates/prose.py:86`). Run `python3 hooks/prose_limit.py --file
saffron/agents/prompts/implement.md` before you commit it.

**The witness.** Put it in `tests/test_context.py`, after
`test_the_implement_prompt_never_calls_scope_proposal_diagnose_only`
(`tests/test_context.py:313`). Assemble the prompt the way
`_assembled_implement_prompt` does (`tests/test_context.py:258-275`): the
real `CONTEXT.md`, the real `saffron/agents/prompts/implement.md`, through
`context.build_system_prompt`. Assemble it twice. Pass `witnesses` as
`context.witnesses_block([])` once, and once as `context.witnesses_block`
over one `Criterion`. Import `Criterion` inside the test body, as
`tests/test_context.py:204` does. From each prompt remove the vocabulary
text, `context.sections_for("IMPLEMENT", <CONTEXT.md>)`, and the spec body
you passed. Then assert that one paragraph of what is left, split on blank
lines, names all four of: `mutant`, the backticked `witness`, `REVIEW` and
`host`. Do not read `implement.md` on its
own: the claim is about the assembled prompt.

**Remove the vocabulary before you search.** The claim excludes it, and a
vocabulary entry can name these words. Measured on this base, the
**Vacuity probe** entry (`CONTEXT.md:357`) already names both mutants and the
host. No entry names all four today, so the step does not change the base
result. It keeps the witness true to the claim if one comes to.

**This is new text, so the criterion declares no mutant.** Its spelling is
yours, and a mutant must match text exactly. The `witness` gate will report
`skip` for it, which is expected.

**What the witness must kill, measured on a prototype.** The author ran
these. You do not need to. Each failed the prototype witness, and the same
paragraph added to `implement.md` passed it.

- `implement.md` unchanged.
- The paragraph added to `turns/implement.md` alone, which is a user turn.
- The paragraph added to `turns/plan.md` alone.
- The paragraph added to `review-correctness.md`, `review-contract.md` or
  `review-adequacy.md` alone, each a lens prompt.
- The paragraph added to `criterion-probe.md` alone.
- The paragraph added to `rebut-verdict.md` alone.
- A paragraph in `implement.md` naming mutants and the host alone. It gives
  a spec's listed wrong versions to the host. It names neither the
  `witness` gate nor REVIEW.
- A sentence naming all four added to `context.witnesses_block`
  alone. It reaches only the prompt with a criterion, so the assembly with
  none fails. That file is outside `touches` in any case.

**Size.** A `bug` gets 300 changed lines. The prototype witness ran to
about 25 lines and the paragraph to 5. Allow about 50 with a docstring.

**Commit the prompt edit and the witness** as soon as the witness passes.
