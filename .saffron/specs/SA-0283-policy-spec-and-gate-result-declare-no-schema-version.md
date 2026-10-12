---
id: SA-0283
title: policy.yaml, a spec and a gate result declare no schema version, so an engine cannot say which format it read
type: feature
priority: 2
depends_on: [SA-0282]
estimated_lines: 130
estimate_measured: true
touches:
  - saffron/repos/policy.py
  - saffron/intake.py
  - saffron/gates/contract.py
  - tests/test_policy.py
  - tests/test_intake.py
  - tests/test_contract.py
  - tests/test_runner.py
  - .claude/skills/setup-saffron/templates/policy.yaml
  - .claude/skills/setup-saffron/GATES.md
  - docs/agents/issue-tracker.md
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
  - README.md
  - pyproject.toml
  - uv.lock
  - .saffron/**
  - .claude/skills/setup-saffron/SKILL.md
  - .claude/skills/run-saffron-spec-loop/**
  - .claude/agents/**
  - ontology/**
  - tests/ontology/**
  - images/**
  - harness/**
  - records/**
  - hooks/**
  - saffron/gates/runner.py
  - saffron/gates/core/**
  - saffron/cell/**
  - saffron/record/**
  - saffron/ledger.py
  - saffron/scheduler.py
  - saffron/task.py
  - saffron/cli.py
  - saffron/replay.py
  - tests/test_setup_saffron.py
  - tests/test_scheduler.py
budget_usd: 34
max_attempts: 3
max_turns: 180
acceptance:
  - claim: >-
      `load_policy` reads a `policy.yaml` that declares no `schema_version`
      as version 1, the integer, and reads one declaring 1 the same way. One
      declaring 2, one declaring `true` and one declaring 1.0 each raise
      `PolicyError`, and the message lists the versions the engine reads.
      The witness loads all five files.
    witness: tests/test_policy.py::test_a_policy_reads_as_version_1_and_refuses_any_other
    wrong_versions:
      - A field defaulting to None, so a policy declaring none reads as no version.
      - A field typed float, so a policy declaring none reads as 1.0.
      - A refusal that names the declared value and lists no supported version.
      - A lax integer check, so `true` loads as version 1.
      - A check that refuses a `bool` and then tests membership in the supported set, so 1.0 passes it and loads as 1.
      - A check that refuses every declared value, 1 included.
      - A check that never runs on a declared value, so 2 loads.
  - claim: >-
      `parse_spec` reads frontmatter that declares no `schema_version` as
      version 1, the integer, and reads frontmatter declaring 1 the same way.
      Frontmatter declaring 2, `true` or 1.0 raises `SpecError` each time,
      and the message lists the versions the engine reads. The witness
      parses all five.
    witness: tests/test_intake.py::test_a_spec_reads_as_version_1_and_refuses_any_other
    wrong_versions:
      - A field defaulting to None, so a spec declaring none reads as no version.
      - A field typed float, so a spec declaring none reads as 1.0.
      - A refusal that names the declared value and lists no supported version.
      - A lax integer check, so `true` parses as version 1.
      - A check that refuses a `bool` and then tests membership in the supported set, so 1.0 passes it and parses as 1.
      - A check that refuses every declared value, 1 included.
      - A check that never runs on a declared value, so 2 parses.
  - claim: >-
      `parse_gate_json` reads a result that declares no `schema_version` as
      version 1, the integer, and reads one declaring 1 the same way. One
      declaring 2, one declaring `true` and one declaring 1.0 each raise,
      and the message lists the versions the engine reads. The witness
      parses all five.
    witness: tests/test_contract.py::test_a_gate_result_reads_as_version_1_and_refuses_any_other
    wrong_versions:
      - A field defaulting to None, so a result declaring none reads as no version.
      - A field typed float, so a result declaring none reads as 1.0.
      - A refusal that names the declared value and lists no supported version.
      - A lax integer check, so `true` parses as version 1.
      - A check that refuses a `bool` and then tests membership in the supported set, so 1.0 passes it and parses as 1.
      - A check that refuses every declared value, 1 included.
      - A contract that keeps ignoring the key, so a result declaring 2 parses.
  - claim: >-
      A gate that prints a passing result declaring `schema_version` 2 comes
      back from `run_gate` as `error`, and its summary lists the versions the
      engine reads. The same gate declaring 1 comes back as `pass`. The
      witness runs both gates as executables.
    witness: tests/test_runner.py::test_a_gate_declaring_an_unsupported_version_is_an_error
    wrong_versions:
      - A contract that keeps ignoring the key, so the gate declaring 2 is `pass`.
      - A refusal that lists no supported version, so the summary names none.
      - A check that refuses every declared value, so the gate declaring 1 is `error`.
  - claim: >-
      The setup skill's policy template still names every `Policy` field,
      `schema_version` included, and still validates as a `Policy`.
    witness: tests/test_setup_saffron.py::test_the_policy_template_names_every_policy_field
    preserves: true
  - claim: >-
      The setup skill's `GATES.md` still names every gate contract field,
      `schema_version` included.
    witness: tests/test_setup_saffron.py::test_gates_md_names_every_contract_field
    preserves: true
---

## Context

Backlog item **b-0569f7**, the child half of its split. It cites
`DESIGN.md` §3.2 and §5.4, and ADR 10. The parent, `SA-0282`, takes the
item's other two parts: the two inert policy fields and the shared-kernel
warning. Every line number below was read at `bc879e2c`. Those in
`saffron/repos/policy.py` are cited by name, since `SA-0282` moves them.

**ADR 10 makes `.saffron/` an interface other operators write against.**
One operator changes a format and fixes every repo in an afternoon. Another
operator's repo meets the change at their next engine upgrade.

**None of the three formats carries a version.** No field of `Policy`
in `saffron/repos/policy.py` names a format. No field of `Spec` in
`saffron/intake.py` names one, and no field of `GateResult` in
`saffron/gates/contract.py` does.

**The three refuse an unknown key differently.** `Policy` and `Spec` each
set `extra="forbid"` in their `model_config`. So today a declared `schema_version` refuses the
whole file, whatever its value. `GateResult` sets no `model_config`
in `GateResult`, so pydantic drops an unknown key. A
gate printing `"schema_version": 2` today parses as whatever status it
reports.

**Each refusal already has a path to the operator.** `load_policy` turns a
`ValidationError` into a `PolicyError` carrying its text, in
`load_policy`'s `Policy.model_validate` call. `parse_spec` turns one into a
`SpecError` the same way, around its `Spec.model_validate` call. `run_gate` turns
any exception from `parse_gate_json` into an `error` result. Its summary
carries the exception's text (`saffron/gates/runner.py:140-146`,
`:353-356`).

## Problem

Give `Policy`, `Spec` and `GateResult` each a field named `schema_version`.
A file or result that declares none reads as 1. A declared 1 reads as 1.
Any other value is refused when the model is validated. The refusal's
message names the value it refused and lists every version the engine
reads.

The three formats version apart, so each module keeps its own set of
supported versions. Each set holds 1 alone today.

Refuse a boolean and a float with the same message as a 2. Pydantic's
lax integer mode reads `true` as 1 and 1.0 as 1. Its strict mode refuses
both, with its own message, which lists no supported version. Measured on
a prototype. So the refusal sees the value before pydantic coerces it.

Then write the three documents that name these fields.

- `.claude/skills/setup-saffron/templates/policy.yaml` declares
  `schema_version: 1`, with a one-line comment.
  `tests/test_setup_saffron.py:158-162` holds the template's keys equal to
  `Policy.model_fields`.
- `.claude/skills/setup-saffron/GATES.md` names `schema_version` in its
  contract section, in backticks. `tests/test_setup_saffron.py:196-201`
  holds every `GateResult` field named there.
- `docs/agents/issue-tracker.md` names the frontmatter key beside the
  defaults its Conventions list (`docs/agents/issue-tracker.md:12-16`).

## Out of scope

- **`GateDeclaration.when`, `Policy.envelope_default` and the shared-kernel
  warning.** `SA-0282` owns them, and this spec runs after it.
- **Declaring the key in this repo.** `.saffron/policy.yaml` and every
  spec under `.saffron/specs/` stay as they are. `.saffron/**` is
  protected, and a spec cannot use a key before intake accepts it
  (§3.2).
- **Recording the version anywhere.** No ledger column, no fact key, no
  rendered line names it. `record_gate_result` dumps the whole model into
  its fact (`saffron/ledger.py:2017`), so a live `gate_result` fact gains
  the key. The fold reads named keys and ignores it
  (`saffron/ledger.py:777-790`). The migration writes named keys without it
  (`saffron/record/migrate.py:276-291`). Leave both.
- **A version 2 of any format.** Nothing here reads one.
- **`DESIGN.md`.** §3.2 and §5.4 were edited by hand with this spec.
- **`.saffron/deadcode-allow.py`.** It lists `schema_version` for this spec
  already. A validator reads the value it is handed, never the attribute,
  so vulture sees no reader.

## Notes for the agent

**The change is new code**, so each criterion declares a witness and no
mutant, and `witness` will report `skip`. Criteria 5 and 6 are `preserves`
witnesses that pass at base and must still pass.

**Name the field `schema_version` on all three models.**
`.saffron/deadcode-allow.py` lists that name, and the `dead` gate fails an
unread field under any other.

**At base every new witness fails.** Criteria 1 and 2 read
`.schema_version` from the loaded model, which does not exist there. Their
declared-1 file is refused at base as an unknown key. Criterion 3 reads the
attribute too. Criterion 4's gate declaring 2 comes back `pass` at base,
since pydantic drops the key. Keep every new name out of the module-scope
imports of the four test files. Read it from the model inside the test, so
the reverted run fails in the test and not at collection.

**Assert the integer, not equality alone.** `1.0 == 1` and `True == 1` in
Python. Assert the type is `int` beside the value.

**Criteria 1 to 3 drive five values each: none, 1, 2, `true` and
1.0.** None and 1 read as the integer 1. A 2, `true` and 1.0 are refused
with the supported list. No witness drives 0 or the
string "1". The claims name the five values they reach.

**Assert the list of supported versions, not a bare digit.** Pydantic's
error text holds `1 validation error for ...` and a URL with its own
version, `errors.pydantic.dev/2.13`. So `"1" in message` passes a refusal
that lists nothing. Assert on the fragment your message uses to list them.

**Criterion 1** loads through `load_policy` with `write_repo` from
`tests/test_policy.py`, appending a `schema_version:` line to the module's
`VALID` text. `SA-0282` edits `VALID` and the test that reads `when`, so
build on what the file holds at your base.

**Criterion 4** writes two executables under `tmp_path`. Each is a `/bin/sh`
script echoing one JSON line with a `tool`. The witness calls `run_gate` from
`saffron/gates/runner.py` with the default `LocalExecutor`. No fake stands
in for the runner.

**The `.claude/` files.** The Write tool is refused on a path under
`.claude/` (`docs/evidence/2026-10-10-agent-unwritable-paths.md`). Write
each of the two with a `python3` script run through Bash, as `SA-0259`
documented. The script reads the file, replaces the text and writes it back. Read each back with `cat` afterwards. The template's comment
cites no `DESIGN.md` section and no `§`, since
`test_a_template_cites_no_saffron_design_section` refuses one in any
template. It names neither `when` nor `envelope_default`, since `SA-0282`
holds the template free of both names.

**Criteria 5 and 6** name tests in `tests/test_setup_saffron.py`, which
this spec forbids and `SA-0282` edits. Both pass at base. Each fails once
a model gains the field, until the template or `GATES.md` names it.
Measured on the prototype. Change neither test.

**`saffron/gates/**` is in `elevate_on`,** so this task runs `elevated`
and `size` blocks.

**The `prose` gate** counts every new comment, docstring and Markdown line.
Write none with an em dash, a semicolon, a contraction, the perfect tense
or a sentence over 25 words.

**Size.** A prototype measured 444 changed tokens with `size_gate`'s
counter, against the `feature` ceiling of 3000. Each of the three
modules held a field, a before-mode validator and a supported-version
constant. It also held the four new witnesses, the template line, one
`GATES.md` bullet and one `issue-tracker.md` bullet. It held no docstring. The full
suite on it passed except the two `test_setup_saffron.py` tests, before
the template and `GATES.md` lines were written. No other test compares a
dumped `GateResult` whole. `estimated_lines` is that count over four, plus
a margin for comments.
