---
id: SA-0129
title: A spec estimated near its `size` ceiling runs unsplit, because nothing reads the estimate
type: feature
priority: 2
depends_on: [SA-0128]
touches:
  - saffron/intake.py
  - .claude/skills/run-saffron-spec-loop/driver.py
  - tests/test_spec_size_estimate.py
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
  - records/**
  - saffron/gates/**
  - saffron/agents/**
  - tests/test_spec_loop_driver.py
  - tests/test_intake.py
  - tests/test_queued_specs.py
  - .claude/agents/**
  - .claude/skills/run-saffron-spec-loop/SKILL.md
  - .claude/skills/create-saffron-spec/**
budget_usd: 20
max_turns: 130
max_attempts: 3
acceptance:
  - claim: >-
      A spec may declare `estimated_lines` in its frontmatter, a count of
      changed lines. A positive YAML integer parses to that value. A spec
      that omits the key, or leaves it empty, parses with `estimated_lines` of `None`. Zero, a negative
      integer, a fraction, a word and `true` are each refused at intake as a
      `SpecError`.
    witness: tests/test_spec_size_estimate.py::test_a_spec_declares_its_estimate_as_a_positive_integer_or_not_at_all
  - claim: >-
      `driver.py check SA-NNNN` prices the spec's `estimated_lines` in
      tokens, at `_TOKENS_PER_LINE` from `saffron.gates.core.size` a line. It
      judges that price against the same module's token ceiling for the
      spec's `type`, the entry in `_CEILINGS` or `_DEFAULT_CEILING` for a
      type with no entry. A price at or above 80% of that ceiling, exactly
      80% included, prints one line that starts `blocker: `. It holds the
      line estimate, its price, the ceiling and the words `parent and
      children`, and the command exits 1. An estimate one line under that
      boundary prints no such line. It prints one line that starts `size: `
      and holds the same three numbers. This holds for each of the six spec
      types, with and without past cells of the spec's shape, for a spec
      read from its file, and for whatever rate, table entry and default
      the module holds when `check` runs.
    witness: tests/test_spec_size_estimate.py::test_check_blocks_an_estimate_at_80_percent_of_its_types_size_ceiling
  - claim: >-
      A spec that declares no `estimated_lines` draws no size blocker from
      `check`. It prints the line `size: no estimated_lines declared` and
      exits 0 when the ceilings clear, with and without past cells of the
      spec's shape.
    witness: tests/test_spec_size_estimate.py::test_check_names_a_missing_estimate_and_blocks_nothing_for_it
  - claim: >-
      A size blocker does not replace the ceilings judgement. A spec with
      `max_turns` at or below a past cell's peak and an estimate priced at
      80% of its ceiling prints both the `max_turns` blocker and the size blocker,
      and exits 1. With the estimate a line under that, the `max_turns` blocker
      alone still prints and exits 1.
    witness: tests/test_spec_size_estimate.py::test_check_prints_a_size_blocker_beside_a_ceilings_blocker
  - claim: >-
      A spec with no estimate is judged on its turns and budget exactly as
      before. The `max_turns` and `budget_usd` blocker thresholds, and the
      exit status they set, do not move.
    witness: tests/test_spec_loop_driver.py::test_check_blocks_the_ceilings_check_4_calls_blockers_and_no_others
    preserves: true
  - claim: >-
      A spec with no past cells of its shape and no estimate still reads as
      having no evidence. `check` claims no pass for its ceilings there.
    witness: tests/test_spec_loop_driver.py::test_check_with_nothing_to_compare_against_claims_no_pass
    preserves: true
---

## Context

Backlog item **b-db95e1**, found in the spec loop's run 14 on 2026-09-22.
It cites `DESIGN.md` §5.4, whose table sets the `size` ceilings.

`SA-0117` landed at 979 changed lines against the `refactor` ceiling of
1000. `SA-0123`, the next spec on the same file, landed at 1001 and ended
`EXHAUSTED`. Its prototype had measured 865. Each spec's estimate lived in
its prose notes, where nothing reads it.

This spec stacks on `SA-0128`, which stacks on `SA-0126`,
which stacks on `SA-0125`.
Every sentence below about current code was read at `c4344e46`. Sentences
about the `size` gate after `SA-0128` cite that spec, because its cell
writes that code.

**The spec model refuses an unknown key.** `Spec` declares
`model_config = ConfigDict(extra="forbid")` (`saffron/intake.py:135`). Its
ceilings are declared fields with `gt=0`, such as `max_turns`
(`saffron/intake.py:163`). The parser drops a key whose value is `None`
before it validates (`saffron/intake.py:193`). So an empty
`estimated_lines:` reads as an omitted one. The six spec types are
`SpecType` (`saffron/intake.py:25`).

**The ceilings, in tokens after `SA-0128`.** At `c4344e46` `_CEILINGS` counts
lines, `bug` 300, `feature` 600 and `refactor` 1000
(`saffron/gates/core/size.py:25`). Every other type takes
`_DEFAULT_CEILING` (`saffron/gates/core/size.py:34`). `size_gate` reads
them as `_CEILINGS.get(spec_type, _DEFAULT_CEILING)`
(`saffron/gates/core/size.py:172`). `SA-0128` makes the gate count
whitespace-separated tokens. It re-measures the ceilings as `bug` 1300,
`feature` 3000 and `refactor` 4200, with the default still `refactor`'s
(`.saffron/specs/SA-0128-size-counts-tokens-so-rewrapping-moves-nothing.md:204-205`).
It declares `_TOKENS_PER_LINE`, set to 4, in the same module, and its plan
checkpoint prices a line estimate by it
(`.saffron/specs/SA-0128-size-counts-tokens-so-rewrapping-moves-nothing.md:208-212`).

**What `check` judges now.** `cmd_check` finds the spec through
`_known_specs` (`.claude/skills/run-saffron-spec-loop/driver.py:1962`). It
prints what `_ceilings_line` returns (`:1974`). With no rows it returns 0
at once (`:1975-1976`). Otherwise it prints each turns or budget blocker and exits 1
on either (`:1977-1987`). No line of it reads a size estimate.
`_known_specs` parses every spec under `SPECS_DIR` and its `done/`
(`.claude/skills/run-saffron-spec-loop/driver.py:1686-1697`).

## Problem

A spec's estimate of its own size is prose, so no command can refuse a spec
whose estimate sits near its ceiling. The operator's rule is "Split a spec
whose estimate is within 20% of its ceiling."

1. **Declare the estimate in lines.** Add an optional `estimated_lines`
   field to `Spec`. It is a positive integer, `None` when omitted. It
   counts changed lines, the unit a spec's author estimates in, and the
   unit `Plan.estimated_lines` uses (`saffron/agents/artifacts.py:70`).
   A boolean is refused, so
   `estimated_lines: true` is not read as one line.
2. **Judge its price in `check`.** Multiply the estimate by
   `_TOKENS_PER_LINE` and compare the product with the gate's token
   ceiling for the spec's `type`. A price at or above 80% of it blocks.
   The boundary is inclusive. With a rate of 4, 600 lines price at 2400
   tokens and block a `feature` spec at 3000, and 599 lines do not.
   Print one of these three lines, with the real numbers.
   - At or above 80%:
     `blocker: estimated_lines=600 (2400 tokens at 4 a line) is at or above 80% of the feature ceiling of 3000 tokens, split into a parent and children`
   - Under 80%:
     `size: estimated_lines=599 (2396 tokens at 4 a line) is under 80% of the feature ceiling of 3000 tokens`
   - Not declared: `size: no estimated_lines declared`
3. **Exit 1 on a size blocker, rows or no rows.** The early return with no
   rows must not skip the size judgement. The turns and budget blockers,
   the concern and the `check: ceilings clear this shape's history` line
   keep their rules unchanged.

## Out of scope

- **`judge_estimate`.** `SA-0125` writes it and `SA-0128` prices it
  (`.saffron/specs/SA-0128-size-counts-tokens-so-rewrapping-moves-nothing.md:90-101`).
  It takes a `Plan`, a risk and `elevate_on`, and it judges at the whole
  ceiling. This rule needs 80% and has no plan or tier, so `check` does
  not call it. Both share the gate's rate and table instead.
- **The size gate itself.** `saffron/gates/**` stays forbidden.
- **The prose that describes `check`.** The loop skill's section 1b says
  `check` exits 1 on either of two rules
  (`.claude/skills/run-saffron-spec-loop/SKILL.md:67-68`). The operator
  updates it and the writer guidance by hand.
- **`docs/agents/issue-tracker.md`'s frontmatter list.** It lists each
  field's default (`docs/agents/issue-tracker.md:13-16`). It stays as it is.
- **Any other command.** `history`, `size` and the queue do not read the
  estimate.

## Notes for the agent

**Every change here is new code.** So each criterion declares a witness and
no mutant, and `witness` will report `skip` for all four new ones. Criteria
5 and 6 are `preserves` and name tests that pass now.

**Where the field goes.** Beside the other ceilings in `Spec`, with a
comment of one or two lines. Refusing a boolean needs a strict integer.
`Field(default=None, gt=0, strict=True)` on `int | None` does it. A lax
`int` reads `true` as 1, measured on this repo's pydantic on 2026-09-22.

**The dead-code gate.** `driver.py` sits outside `ROOTS`
(`.saffron/gates/dead.py:21-29`), so the driver's read does not count. The
name is still read in a root, as `plan.estimated_lines`
(`saffron/agents/artifacts.py:289`). Vulture matches names globally, so the
new field is not reported. The gate passed on a prototype on 2026-09-22.

**Where the judgement goes.** Import `_CEILINGS`, `_DEFAULT_CEILING` and
`_TOKENS_PER_LINE` from `saffron.gates.core.size` inside the function that
judges, as `_size` imports `size_gate`
(`.claude/skills/run-saffron-spec-loop/driver.py:600-601`). Every `saffron`
import in `driver.py` sits inside a function. Criterion 2's witness patches
the module's names and expects `check` to see the patch, so a module-scope
import fails it. Never copy the numbers. Compare in integers,
`5 * price >= 4 * ceiling`, so no float rounding moves the boundary. Run it
before the early return at
`.claude/skills/run-saffron-spec-loop/driver.py:1975`. Count a size blocker
into the exit status with the others. Update the `check` subparser's help
text (`.claude/skills/run-saffron-spec-loop/driver.py:2754`) and
`cmd_check`'s docstring to name the size judgement.

**The test file.** All four new witnesses go in
`tests/test_spec_size_estimate.py`. `tests/test_spec_loop_driver.py` is
forbidden, because `SA-0128` edits it. Import its helpers instead, as
`tests/test_batch.py:12` imports from `tests.test_scheduler`. Take
`driver`, `_spec`, `_cell` and `_StubLedger` from
`tests.test_spec_loop_driver`. Every name imported at module scope exists
at base, so the reverted run fails rather than failing to collect. Set the
estimate on a built spec with `target.estimated_lines = n`, as the
existing check tests set `target.max_turns`. Monkeypatch `_known_specs`,
`_ledger_and_repo` and `_past_cells` as
`test_check_blocks_the_ceilings_check_4_calls_blockers_and_no_others` does.
Find that test and the one below by name, since `SA-0128` edits the same
file above them.

**Criterion 1's witness** calls `parse_spec` on frontmatter declaring 480,
omitting the key, leaving it empty, and declaring 0, -3, 1.5, `many` and
`true`. It asserts the value for the first three and a `SpecError` for each
of the five others. These wrong implementations fail it: a field with no
lower bound, a lax `int` that reads `true` as 1, a `float` field and a
required field.

**Criterion 2's witness** loops over all six types in `SpecType`. For each
it reads the ceiling from `_CEILINGS` and `_DEFAULT_CEILING`, and the rate
from `_TOKENS_PER_LINE`, at test time and never as literals. Import them
inside the test body. It computes the boundary in lines as
`-(-4 * ceiling // (5 * rate))`. It drives the boundary and one line under
it, first with no rows and then with one clear row of the same type from
`_cell`. Each blocker asserts the return code 1 and one `blocker: ` line
holding the estimate, its price and the ceiling as whole words, and
`parent and children`. Each pass asserts the return code 0, no `blocker: `
line and one `size: ` line holding the same three numbers. Then, with
`monkeypatch`, it sets `_CEILINGS["feature"]` to 3500, `_DEFAULT_CEILING`
to 5000 and `_TOKENS_PER_LINE` to 5. It drives the new boundary and one
under it for `feature` and for `docs`. Last, it writes a `feature` spec
file declaring the boundary into a temporary `SPECS_DIR`, as
`test_known_specs_skips_a_missing_done_directory` does, and leaves
`_known_specs` unpatched. That run exits 1. These wrong implementations
fail it:

- the line estimate compared with the token ceiling, unpriced
- a literal rate of 4
- a strict `>` at the boundary
- one ceiling for every type
- a literal default of 4200
- a copy of the ceilings in `driver.py`
- a judgement placed after the early return with no rows
- a blocker printed with exit 0
- a printed price that is the line count
- an estimate that `_known_specs` drops on the way from the file

**Criterion 3's witness** builds a spec with no estimate, with no rows and
then with one clear row. Each run asserts return code 0, the exact line
`size: no estimated_lines declared`, and no `blocker: ` line. A missing
estimate read as zero prints the under-80% line and fails it.

**Criterion 4's witness** sets `max_turns` to 10 against one `bug` row
whose peak is 41, the `_cell` default. With the estimate at the boundary it asserts
both blocker lines and return code 1. With the estimate one under, it
asserts the `max_turns` blocker, no size blocker and return code 1. A
judgement that returns early on a size blocker fails it.

**Size.** A prototype of the change measured 159 changed lines, 29 of
source and 130 of test. Expect about 200 with the help text and the
docstring. `SA-0112`, which added `check` to the same two kinds of file,
landed at 243. The `feature` ceiling is 600 lines at `c4344e46` and 3000
tokens after `SA-0128`. This spec declares no `estimated_lines` of its own,
because intake at base refuses the key.

**Measured wrong implementations, to run again.** On 2026-09-22 the
prototype ran at `c4344e46` with a stand-in for `SA-0128`'s constants: the
token ceilings above and `_TOKENS_PER_LINE = 4` in
`saffron/gates/core/size.py`, and nothing else of `SA-0128`. With the source
reverted, all four new witnesses failed rather than erroring. Each of these
failed its witness:

- an unpriced estimate
- a literal rate of 4
- a strict `>`
- a literal default of 4200
- a copied ceiling table
- one ceiling for every type
- the judgement after the no-rows return
- a size blocker that returns before the ceilings judgement
- a blocker with exit 0
- a lax `int`
- a missing estimate read as zero
- a printed price that is the line count

`SA-0128`'s code does not exist at `c4344e46`. So run this list
again at `SA-0128`'s branch head before the cell, against the real gate.
