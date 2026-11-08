---
id: SA-0355
title: A survived mutant reaches REPAIR as its whole claim, so the repair turn cannot find the case the witness left untested
type: bug
priority: 1
depends_on: [SA-0351]
estimated_lines: 53
estimate_measured: true
touches:
  - saffron/intake.py
  - saffron/gates/core/witness.py
  - tests/test_witness_gate.py
  - tests/test_mutants.py
  - tests/test_mutant_command.py
  - docs/agents/issue-tracker.md
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
  - docs/adr/**
  - docs/appendices/**
  - docs/backlog/**
  - docs/evidence/**
  - images/**
  - harness/**
  - records/**
  - hooks/**
  - saffron/mutants.py
  - saffron/gates/baseline.py
  - saffron/gates/contract.py
  - saffron/gates/runner.py
  - saffron/gates/suite.py
  - saffron/cell/**
  - saffron/phases/**
  - saffron/agents/**
  - saffron/scheduler.py
  - saffron/task.py
  - tests/mutation.py
budget_usd: 36
max_attempts: 3
max_turns: 170
risk: standard
acceptance:
  - claim: >-
      A mutant whose witness survives it fails `witness` with a
      `survived-mutant` failure whose message still names the claim, and
      quotes the mutant's `case` when one is declared. Each failure quotes its
      own criterion's case and no other's. A mutant with no `case` gives the
      message the base gives, character for character. No mutant's `find`
      text appears in the serialized gate result, or in the text
      `saffron.phases.implement.repair_prompt` renders from its failures.
      Neither does a mutant's `replace` text that no claim or case holds. The
      witness drives three surviving criteria in one call, in this order: two
      with distinct cases, then one with none. Their mutants are read from a
      mutants file's text by `saffron.mutants.parse_mutants`, and applied
      through `tests.mutation.host_mutator`.
    witness: tests/test_witness_gate.py::test_a_surviving_mutant_quotes_its_own_case_and_never_its_edit
    wrong_versions:
      - The case replaces the claim in the message, so the claim is lost.
      - The first case declared among the criteria is quoted in every survivor's message.
      - A mutant with no case still gets the case's lead-in, or the text `None`, appended to its message.
      - The message quotes the `find` text beside the case, so REPAIR can locate the line.
      - The case is added to the gate's summary and never to a failure's message.
      - A survivor with no case carries over the case of the survivor before it.
  - claim: >-
      A mutants file's entry may declare `case`, a string. `parse_mutants`
      loads it as declared, whitespace included, and loads an entry without
      it as `None`. It refuses an empty case and a whitespace-only one as a
      `MutantsError` naming the file. The witness drives all five: a plain
      case, a case with leading and trailing spaces, an omitted case, an
      empty one and a whitespace-only one.
    witness: tests/test_mutants.py::test_a_mutant_case_loads_when_declared_and_is_refused_blank
    wrong_versions:
      - The field defaults to the empty string, so an entry without a case loads as `""`.
      - Only the empty string is refused, so a case of three spaces loads.
      - A blank case is stripped to `None` and loads.
      - A declared case is stripped on load, so its leading and trailing spaces are lost.
  - claim: >-
      `saffron.mutants.attach_mutants` refuses a mutant whose `find` text its
      own `case` holds, and one whose `find` text another criterion's mutant's
      `case` holds, as a `DisclosedMutantError`. For the second, the message
      names the witness whose case holds the text. A case holding no mutant's
      `find` attaches, and the attached criterion carries it. The witness
      drives each in one spec of two criteria. It drives the second in both
      orders: the holder's criterion first, then second.
    witness: tests/test_mutants.py::test_a_case_that_holds_any_mutants_find_is_refused_as_a_disclosure
    wrong_versions:
      - Only a criterion's own case is compared with its own find, so a sibling's case that holds it attaches.
      - "`Mutant` refuses its own find in its own case at validation, and `refuse_disclosed_mutants` never reads a case."
      - The case is compared with the find for equality, so a sentence holding the find among other words attaches.
      - The refusal is raised as a plain `MutantsError`.
      - The sibling refusal says "its own case" and never names the holder's witness.
      - The `replace` text is compared too, so an empty `replace`, which every string holds, refuses a clean case.
      - Each find is checked only against the cases of criteria up to and including its own, so a holder declared after it attaches.
---

## Context

Backlog item **b-fa4a83**. It cites `DESIGN.md` §5.4.1. Every line below was
read at `3bac6ab9`.

**What `SA-0330` lost.** In the spec loop's run 53, the `witness` gate failed
both of `SA-0330`'s declared mutants in all three attempts. Both claims ran
to about a dozen sentences. The repair turns wrote mutants of their own and
hardened against those, and never found the case either declared mutant
broke. The cell ended `EXHAUSTED` at $41.67 of $40. Each missing case took
the delegate one test block to write.

**What a survivor says today.** A witness that passes under its mutant adds
one `Failure` with code `survived-mutant`. Its `file` is the witness, and its
message is `ran and passed with its mutant applied to <file> — <claim>`
(`saffron/gates/core/witness.py:260-272`). The comment there says the
message reaches REPAIR verbatim and withholds the edit (§5.4.1).
`repair_prompt` renders each new failure's code and message as one line
(`saffron/phases/implement.py:194-213`). A `survived-mutant` failure is never
cancelled by the baseline (`saffron/gates/baseline.py:24-32`), so its message
is no part of any identity that matters here.

**Where a mutant comes from.** `parse_mutants` reads a mutants file's text
and validates each entry with `Mutant.model_validate`
(`saffron/mutants.py:40-64`). `Mutant` declares `file`, `find` and `replace`
under `extra="forbid"` (`saffron/intake.py:93-128`), so an entry with any
other key is refused today. `attach_mutants` sets each criterion's mutant and
then runs `refuse_disclosed_mutants` on the result
(`saffron/mutants.py:83-112`). That check refuses a `find` that the body, any
claim or any wrong version holds (`saffron/intake.py:378-431`). `run_task`
reads and attaches the mutants (`saffron/task.py:784-785`). So does
`driver.py`'s probe (`.claude/skills/run-saffron-spec-loop/driver.py:2336-2340`).
`SA-0339`'s `saffron mutant` validates with `parse_mutants` and
`attach_mutants` too (its Problem, step 1). So every reader and the writer
take the new field with no edit of their own.

## Problem

1. **A mutant names its case.** Add an optional `case` to `Mutant`. It is
   a string, and `None` when absent. It is one sentence naming the case the claim
   leaves untested, taken from the claim or written beside it. A declared
   case that is empty or only whitespace is refused.
2. **A survivor quotes it.** The `survived-mutant` message keeps
   everything it carries today. It then quotes the surviving mutant's case,
   where one is declared. With no case, the message is exactly today's. The
   message adds no `find` text, and no `replace` text beyond what a claim
   or a case already holds.
3. **The disclosure check reads it.** Every survivor's message reaches
   REPAIR with its case. So a case holding any mutant's `find` hands that
   edit to the implementer. `refuse_disclosed_mutants` refuses a `find` that any
   criterion's mutant's case holds, as it refuses one any claim holds. Name
   the holder's witness when it is another criterion, as the claim check does
   (`saffron/intake.py:409-415`). Update its docstring.
4. **Prose that turns false.** The comment above the message
   (`saffron/gates/core/witness.py:261-262`) names only the claim and the
   file. In `docs/agents/issue-tracker.md`, add `case` to the mutants file's
   example (`docs/agents/issue-tracker.md:80-86`) and say in one sentence
   what it is for. Keep each new comment to two lines.

**Why `case`.** The item asks for the case its claim leaves untested, and
`SA-0330`'s two missing tests were each one case. The word sits beside
`file`, `find` and `replace` in the YAML as one short noun. It names no new
concept, so no glossary entry is owed.

## Out of scope

- The find-count failures `SA-0351` adds. Their messages do not quote the
  case.
- Refusing a case that holds the `replace` text. An empty `replace` is held
  by every string, and a short one such as `False` is common prose. The
  `find` check is the tripwire `DESIGN.md` §5.4.1 describes, and the same
  limit holds: a paraphrase evades it.
- Enforcing one sentence. Only a blank case is refused.
- A criterion probe or a wrong version. Their edits come from a REVIEW
  session's JSON (`saffron/cell/session.py:2065`), and no prompt asks for a
  case. One that carries `case` now loads and is quoted if it survives.
- `refuse_disclosed_mutants` run from `parse_spec` over an inline mutant.
  It is the same function, but a queued spec's inline mutant is refused at
  intake, so no witness drives that path.
- `saffron/mutants.py`. Nothing in it changes.
- `SA-0339`'s `README.md` line and the `saffron mutant` help text. Neither is
  known to name the fields of a mutant. The delegate greps `SA-0339`'s merged
  `README.md` before this spec runs.

## Notes for the agent

**Stack order.** `depends_on: [SA-0351]` puts this spec after `SA-0351`,
which restructures `witness_gate` around the same `survived-mutant` branch.
Find the message by its text, not its line. `SA-0350` edits
`saffron/intake.py` too, on another branch of the dependency graph. A stack
batch is linear: it takes each ready spec by priority, then id
(`saffron/scheduler.py:1178-1212`). `SA-0350` and `SA-0351` are both
priority 2, and `SA-0350` sorts first. This spec is ready only once
`SA-0351` is taken, so its tree carries `SA-0350`'s change. That spec's
criteria add `retired_first` to `Spec` and name neither `Mutant` nor
`refuse_disclosed_mutants`. Find each of the two by its name. At priority 1
this spec then runs before `SA-0352` to `SA-0354`, and `SA-0353` forbids
`saffron/intake.py`.

**`DESIGN.md` §5.4.1.** Amended by hand at this spec's base, to say a
mutant can carry a case and a survivor's failure quotes it.

**Edit or new.** The case field, its quoting and its disclosure check are
new code, so the base fixes none of their spelling. No criterion declares a
mutant, and `witness` reports an honest `skip` on each.

**A shape that worked.** A prototype added the field with a
`field_validator` refusing a blank value. It appended the case to the message
after one fixed lead-in, only when `mutant.case is not None`. It added one
loop after the wrong-versions loop in `refuse_disclosed_mutants`. Every
existing test passed over it.

**Two traps the prototype hit.** REVIEW records each probe and wrong version
with `model_dump()` (`saffron/phases/review.py:573`, `:675`,
`saffron/probe.py:327`). A plain `case: str | None = None` put `'case': None`
in each dump. Those dumps are read back with `Mutant.model_validate`, which
hands an explicit `None` to the validator. Over that shape, 64 existing tests
failed. 53 met a validator calling `.strip()` on `None`. The rest met a
dump, or a count downstream of one, that the key changed. Declaring the field with
`Field(default=None, exclude_if=lambda value: value is None)` and letting the
validator pass `None` through left every one green. The locked Pydantic is
2.13.4.

**The witnesses.** Plain `def`s, never a parametrised test. Import
`parse_mutants`, `attach_mutants`, `MutantsError`, `NewFailure` and
`repair_prompt` inside the test body, as `tests/test_mutants.py` does.

- Criterion 1 writes three files, each holding its own `find` once. Give each
  `find` and `replace` a shared distinctive prefix that no claim or case
  holds, so one substring check covers every edit. Declare the two criteria
  with cases first and the case-less one last. Build the mutants with `parse_mutants` over one YAML
  text, as the ref holds them. Give each criterion its own claim, and assert
  the case-less one's message equals the base format in full. Render
  `repair_prompt` over the failures, each wrapped as `NewFailure("witness",
  failure)`.
- Criterion 3 parses one spec with two criteria, neither of whose witness
  ids contains the other. For the sibling case, put the holder's case on the
  first criterion and the disclosed `find` on the second. Then swap them,
  with the disclosed `find` on the first and the holder's case on the second.

**Every new test fails with the source reverted.** On the prototype, all
three failed with `saffron/` reverted. `Mutant` refuses `case` as an extra
key at base, so each test raises before its first assert.

**`SA-0339`'s tests.** Its refusal witness drives "a key `Mutant` lacks". If
its test spells that key `case`, it now loads. Change that test's key to
another name, and change nothing else in it.
