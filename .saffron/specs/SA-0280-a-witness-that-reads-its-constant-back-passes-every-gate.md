---
id: SA-0280
title: A witness that reads back the constant it tests passes every gate, because `witness` runs only the mutants a spec declares
type: feature
priority: 2
depends_on: [SA-0278]
estimated_lines: 560
estimate_measured: true
touches:
  - saffron/gates/core/constant_mutants.py
  - saffron/gates/core/witness.py
  - saffron/gates/suite.py
  - saffron/repos/policy.py
  - tests/test_constant_mutants.py
  - tests/test_policy.py
  - tests/test_setup_saffron.py
  - .claude/skills/setup-saffron/templates/policy.yaml
  - .claude/skills/setup-saffron/SKILL.md
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
  - docs/backlog/**
  - docs/appendices/**
  - docs/adr/**
  - images/**
  - harness/**
  - records/**
  - hooks/**
  - saffron/agents/**
  - saffron/gates/core/integrity.py
  - saffron/gates/runner.py
  - saffron/intake.py
  - saffron/cell/**
  - tests/test_scheduler.py
budget_usd: 36
max_attempts: 3
max_turns: 190
acceptance:
  - claim: >-
      With the notes' `witness:` patterns declared verbatim, and
      `integrity.test_paths` set to `tests/**`, a gate suite runs a
      constant mutant against each witness whose own text names a
      constant the diff adds. The constant has `SA-0192`'s parenthesized
      shape, a name, ` = (`, then two string lines and a closing paren.
      The test file also defines an upper-case constant both tests name,
      and it is never mutated. The spec declares no mutant. The witness
      that compares the code's output with the constant survives. So
      `witness` reports `fail` with exactly one `survived-mutant` failure,
      filed under that witness. Its message ends with "the witness names
      `GREETING` and passes with any value of it, so pin the value as a
      literal". The witness that pins the literal value dies under the same
      edit. `revert` and `criteria` judge the spec's own two criteria alone,
      so `criteria` reports "2 criteria witnessed at head". The tree is
      unchanged afterwards. The witness drives a real git tree and a real
      `tests` gate through `GateSuite._run`, with a base whose `tests`
      result enumerated no test.
    witness: tests/test_constant_mutants.py::test_a_witness_reading_its_constant_back_survives_a_constant_mutant
    wrong_versions:
      - "`GateSuite` computes the constant mutants and passes only the spec's own criteria to `run_suite`, so `witness` reports `skip`."
      - "`GateSuite` passes `[]` as the test paths, so the test file's own constant is mutated and the reading witness survives twice."
      - "`GateSuite` passes `spec.touches` as the test paths, so the module's constant is skipped and `witness` reports `skip`."
      - A per-line matcher runs each pattern over one line at a time, so the parenthesized constant is never matched.
      - "`witness_name` is applied with `re.match`, so no witness id matches and nothing is derived."
      - The mutant's `replace` is the expanded template alone, so the constant's name is lost and the module fails to import.
      - The `replace` template is inserted as written and never expanded against the match.
      - The derived claim omits the constant's name, or names no remedy.
      - Only the first criterion whose witness names the constant gets a mutant, so the literal witness is never run.
      - One combined acceptance list reaches all three sites, `run_suite`, `revert` and `criteria`, so `criteria` counts four criteria.
  - claim: >-
      With the notes' patterns verbatim, `constant_mutants` derives one
      criterion for each pair of a constant and a witness. It applies
      `witness_name` to a witness id with `re.search`, and each constant
      pattern with `re.finditer` over each hunk's new side, the context
      and added lines joined. The constant is one the diff adds, or one
      whose line the diff changes, in a file outside the given test paths.
      The witness's own text in the diff names the constant as a whole
      word. Each of these derives nothing. A constant only on a context
      line. A constant in a test path. A name that is only the prefix of a
      longer one, as `NEW` of `NEWER`. A name that is only the suffix of a
      longer one, as `NEW` of `OLD_NEW`. A test in the same file whose own
      text never names it. A
      witness id the `witness_name` pattern does not match. A second
      criterion naming a witness already paired with that constant.
    witness: tests/test_constant_mutants.py::test_only_a_constant_the_diff_writes_and_a_witness_names_is_mutated
    wrong_versions:
      - A match on context lines counts, so an unchanged constant is mutated.
      - The given test paths are not skipped, so a constant in a test file is mutated.
      - The name is searched as a substring, so `NEW` matches a test naming `NEWER`.
      - The witness's whole test file is searched rather than its own text, so a sibling test is paired.
      - A witness id the `witness_name` pattern misses is searched under its whole id, or raises.
      - Two criteria naming one witness yield the pair twice.
      - A per-line matcher runs each pattern over one line at a time.
      - The whole-word search has no leading word boundary, so `NEW` matches a test naming `OLD_NEW`.
      - "`witness_name` is applied with `re.match`, anchored at the id's start."
  - claim: >-
      `constant_mutants` derives nothing, and raises nothing, in each of
      five cases. No `witness:` block. `witness_name` absent.
      `witness_body` absent. No constant pattern. A diff it cannot read.
    witness: tests/test_constant_mutants.py::test_a_repo_declaring_no_witness_patterns_derives_nothing
    wrong_versions:
      - An absent `witness_body` falls back to the witness's whole test file.
      - An absent `witness_name` is read as an empty pattern, so its missing `name` group raises.
      - An unreadable diff raises out of `constant_mutants` and so out of the suite.
  - claim: >-
      `load_policy` refuses a `witness:` block with `PolicyError` in each of
      seven cases, and the error quotes the text at fault. A constant
      pattern with no `name` group. One with no `value` group. One that is
      not a regular expression. A `replace` naming a group its pattern
      lacks. A `witness_name` with no `name` group. A `witness_body` with
      no `{name}` in it. A `witness_body` that is not a regular expression
      once `{name}` is filled in. It loads a block declaring all three
      fields, and `Policy.witness` reads them back.
    witness: tests/test_policy.py::test_a_witness_block_is_checked_when_the_policy_loads
    wrong_versions:
      - The patterns are compiled only when the suite runs, so a bad one loads.
      - "`witness_body` is checked for `{name}` and never compiled."
      - The `value` group is not required, so `match.span(\"value\")` fails at gate time.
      - The `replace` template is never parsed at load, so a bad group reference raises out of the suite on every attempt.
  - claim: >-
      The setup skill's policy template names the `witness:` block among
      the policy fields, and that block names every `WitnessPatterns`
      field, as the test already compares the `integrity` block's.
    witness: tests/test_setup_saffron.py::test_the_policy_template_names_every_policy_field
    preserves: true
    wrong_versions:
      - The template's `witness:` block names only `constants`.
---

## Context

Backlog item **b-5b1f8a**, with **b-78ccc7** and **b-7e69d0**. It cites
`DESIGN.md` §5.4.1 and §2.1, and ADRs 2 and 3.

**A witness can assert a constant against output built from it.**
`SA-0192`'s criterion 2 expected `review.NO_STANDING_INSTRUCTIONS`, the
constant under test (`git show 07e0ad21:tests/test_review.py`, lines
585-587). Any wording passes such a witness. Four wrong wordings survived
review. `SA-0195` (#600) made the adequacy prompt name the shape. No gate
refuses it.

**`witness` runs only what a spec declares.** `witness_gate` keeps the
criteria that carry a `mutant` (`saffron/gates/core/witness.py:136`). With
none it reports `skip`, "the spec declares no mutants" (`:137-140`). A
survivor is a `Failure` coded `survived-mutant`, filed under the witness
(`:251-262`). Its message ends with the criterion's claim. `run_witness`
(`saffron/gates/runner.py:174`) probes subset support only when a
criterion declares a mutant. It then hands every criterion to
`witness_gate` (`:294`).

**The suite has the diff and the policy in hand.** `GateSuite._run` reads
the changed files and the patch (`saffron/gates/suite.py:148-149`). It
passes `spec.acceptance` to `run_suite` (`:160`). `revert` takes
`spec.acceptance` and `policy.integrity.test_paths` (`:171-173`).
`integrity` parses the same diff (`:196`). Three production suite runs go
through `GateSuite`. They are GATE's (`saffron/cell/session.py:2034`),
the lens cell's (`saffron/cell/session.py:1452`, called at `:2808`) and
PACKAGE's reverify (`saffron/phases/package.py:515`).

**Core reads a diff already.** `saffron/gates/core/integrity.py` splits a
diff into file blocks (`_split_blocks`, `:103`) and parses each one
(`_parse_block`, `:122`). A parsed `_FileDiff` (`:74`) keeps each hunk as
`(kind, text, new_line)` triples, its paths, and `matches_any` (`:94`). A
diff it cannot trust raises `_DiffError` (`:67`). `size.py` imports two of
its private names already (`saffron/gates/core/size.py:21`).

**A witness id is opaque to core.** `Criterion.witness` is a node id that
"the gate never parses" (`saffron/intake.py:113-114`). Its file and test
name are language knowledge.

**The policy refuses an unknown key.** `IntegrityPatterns`
(`saffron/repos/policy.py:52`) and `Policy` (`:66`) both forbid extra
fields. `load_policy`
turns a validation error into `PolicyError` (`:129-132`), which fails
preflight. The suppression tokens a repo declares are plain substrings,
each tested with `token in content`
(`saffron/gates/core/integrity.py:268`). This block is the first to take
Python `re` patterns.

**The setup template names every policy field.**
`test_the_policy_template_names_every_policy_field` asserts that the
template's keys equal `Policy.model_fields`, and its `integrity` keys
equal `IntegrityPatterns.model_fields`
(`tests/test_setup_saffron.py:158-162`).

## Problem

Derive constant mutants in core, from patterns the repo declares.

Add a `witness:` block to `Policy`, a `WitnessPatterns` model. It holds
three fields, each absent by default. Each pattern is a Python `re`
expression.

- `witness_name`: applied to a witness id with `re.search`. Its `name`
  group is the test's own name.
- `witness_body`: a pattern holding the literal text `{name}`. With
  `{name}` replaced by that test name, escaped, it matches the test's own
  text.
- `constants`: a list of entries, each a `pattern` and a `replace`. The
  `pattern` matches one spelling of a constant. Its `name` group is the
  constant's name, and its `value` group the span the mutant edits. The
  `replace` is a template expanded against the match, as `re` expands
  one. It takes the `value` span's place.

Check each pattern and each `replace` when the policy loads, so a bad one
fails preflight. `re.compile(pattern).sub(replace, "")` parses a template
before it matches anything. It raises `re.error` or `IndexError` on a bad
one.

Add `saffron/gates/core/constant_mutants.py` with one public function,
`constant_mutants(diff, acceptance, patterns, test_paths)`. It returns a
list of `Criterion`, each with a `mutant`. Read the diff with
`integrity`'s parser. Run each constant pattern with `re.finditer` over
each hunk's new side, the context and added lines joined with newlines.
A match counts when it overlaps an added line. Its `find` is the matched
text, and its `replace` the same text with the `value` span replaced.
Skip a file the test paths match, and a deleted or unreadable one. Pair
the constant with each criterion whose witness's own text names it as a
whole word. That text is every `witness_body` match over the hunks' new
sides. The derived criterion keeps the witness. Its claim is the text
below, with the constant's name in place of `NAME`.

```text
the witness names `NAME` and passes with any value of it, so pin the value as a literal
```

Rewrite two docstrings in `saffron/gates/core/witness.py` and change no
code there. The module docstring says the gate applies "a text edit the
*spec* supplied" (`:15-16`). The `witness_gate` docstring says `skip` is
the answer "for a spec that declares no mutants" (`:112-114`). Each must
also cover a constant mutant.

In `GateSuite._run`, pass `run_suite` the spec's criteria followed by the
derived ones, with `policy.integrity.test_paths` as the test paths. Leave
`revert` and `criteria` on the spec's own criteria.

Name the `witness:` block in the setup template, with `FILL` comments
like its neighbours. `witness_name` and `witness_body` are `null` there,
and `constants` is an empty list. One comment names the dialect, Python
`re`. One says
a `replace` must leave every matched file importable. Extend
`test_the_policy_template_names_every_policy_field` to compare the
block's keys with `WitnessPatterns.model_fields`, as it compares the
`integrity` block's. In `.claude/skills/setup-saffron/SKILL.md`, rename
step D's heading to name `witness` beside `protected` and `integrity`,
and add one bullet for it.

## Out of scope

- **This repo's own `witness:` block.** `.saffron/policy.yaml` is
  protected (`.saffron/policy.yaml:67`). `Policy` refuses the key until
  this spec lands, so the block goes in by hand after the merge. The
  notes give the patterns measured for it.
- **The design record.** `DESIGN.md` §2.1, §5.4, §5.4.1 and §11, ADR 2,
  ADR 3 and the `CONTEXT.md` entry are written by hand on this spec's
  branch.
- **A stale docstring sentence.** It says "the gate never parses" the
  `witness` node id (`saffron/intake.py:113-114`). A
  constant mutant reads one through the repo's `witness_name` pattern.
  The file stays forbidden, so the sentence is left for a follow-up.
- **The implement prompt.** Telling the implementer to pin a constant's
  value as a literal is a follow-up in `saffron/agents/`.
- **Comment and docstring lines inside a witness.** A regular expression
  match is one span of text. So `witness_body` cannot drop a comment line
  from inside a test, and a name there still pairs.
- **A constant only an unchanged test names.** The witness's text is read
  from the diff. So a witness the diff leaves alone is never paired.
- **The adequacy prompt and the conventions lens.** `SA-0195` covered them.

## Notes for the agent

**Commit as each witness passes.** A cut-off attempt keeps the work.

**Witness and mutant.** Every criterion declares a witness and no
mutant, so `witness` reports `skip` for this spec's own criteria. The
change is new code whose spelling the spec cannot know.

**Why core holds no Python.** §2.1 keeps language knowledge on the repo's
side. What a constant looks like, and where a test's text ends, are both
Python facts here. So the repo declares them as `re` patterns. Core
applies them to the diff as text and runs nothing new. `witness_gate` and
`run_witness` stay as they are, and the derived criteria reach them as
ordinary criteria.

**Import every new name inside each test body.** That covers
`constant_mutants` and `WitnessPatterns`. A module-scope import of a name
the change adds makes `revert`'s reverted run a collection error, which
`revert` reads as `skip`. Pass `Policy` its `witness:` block as a plain
dict, so the module still imports at the tree base.

**The patterns, verbatim.** Criteria 1 and 2 declare this block, and this
repo declares it by hand after the merge.

```python
_NAME = r"(?m)^(?P<name>[A-Z][A-Z0-9_]*)(?:: [^=\n]+)? = "
PATTERNS = dict(
    witness_name=r"::(?P<name>\w+)$",
    witness_body=r"(?m)^(?P<i>[ \t]*)def {name}\(.*(?:\n(?:(?P=i)[ \t]+.*|[ \t]*))*",
    constants=[
        {
            "pattern": _NAME
            + r"\(?\s*(?P<value>[rbfuRBFU]{0,2}(?:\"\"\"|'''|\"|'))",
            "replace": r"\g<value>saffron constant mutant ",
        },
        {
            "pattern": _NAME
            + r"(?P<value>-?(?:0[xX][0-9a-fA-F_]+|0[oO][0-7_]+|0[bB][01_]+"
            + r"|\d[\d_]*(?:\.[\d_]*)?(?:[eE][-+]?\d+)?j?))(?![\w.])",
            "replace": r"(\g<value> + 1)",
        },
    ],
)
```

A string gains a prefix inside its opening quote. A number becomes the
sum of itself and one, so `0`, `0x1F`, `0o17`, `0b101`, `-3`, `1_000`,
`1.5`, `1e-3`, `2j` and `0.` all stay valid. Measured on a prototype, the
two patterns derived 199 mutants over every tracked `.py` file in this
tree, read as if added. Each compiled once applied, and one `find` was
ambiguous. Seventeen literal spellings, the ones above among them,
compiled too.

Over `git diff 44dd8e17 07e0ad21`, `SA-0192`'s own diff, with its
acceptance and `tests/**` as the test paths, they derived exactly one
constant mutant. It pairs
`test_the_conventions_lens_says_a_repo_without_claude_md_declares_none`
with `NO_STANDING_INSTRUCTIONS` in `saffron/phases/review.py`. Under it
that witness passed at `07e0ad21` and failed at `d2ea4afe`, the review
commit that pinned the literal.

**Criterion 1** builds a git repo under `tmp_path`. Set `HOME`,
`XDG_CONFIG_HOME` and `GIT_CONFIG_NOSYSTEM=1` in every git call's
environment. Commit a base, then a head that adds `prompts.py`, a
`pytest.ini` setting `pythonpath = .` and `tests/test_prompts.py`.

- `prompts.py` defines `GREETING = (`, then `"hello "` and `"world"` on
  their own lines, then `)`. A function returns it.
- `tests/test_prompts.py` defines `EXPECTED = "hello world"`. One test
  compares the function's result with `prompts.GREETING` and also names
  `EXPECTED`. The other compares the result with `EXPECTED` and also
  names `prompts.GREETING`.

The policy sets `integrity.test_paths` to `["tests/**"]`. The spec's
`touches` lists the three files. The `tests` gate is a script that runs
pytest over its arguments with `sys.executable`. It prints the
contract's JSON with `collected` from a `--collect-only` run. The tree
adapter returns `git diff` with `worktree.DIFF_FLAGS` as its patch. It
mutates through `tests.mutation.host_mutator`. Its `reverted` yields
without reverting, and `dirty_paths` returns an empty list. Those two
defaults hide only `revert` and `committed`, which this criterion does
not read. Call `suite._run` with a `prior` holding one readable `tests`
result whose `collected` is empty, so `criteria` judges each witness red at
base. Assert the `criteria` summary exactly. Read the `witness` result. Assert its failures as a list of
`(file, code)` pairs, and the summary saying one of two witnesses
survived. Assert `git diff HEAD` is empty afterwards.

**Criteria 2 and 3** call `constant_mutants` over a diff string written
in the test, with the test paths `["tests/**"]`. Assert the sorted list
of `(witness, file, find, replace)` tuples. Criterion 2's diff holds each
member its claim lists. Use a bare `test_a` as the unmatched witness id,
so a fallback to the whole id would pair it. Criterion 3's test drives
each of its five cases.

**Criterion 4** writes each bad block into a policy file and calls
`load_policy`, as `tests/test_policy.py` does with its `write_repo`
helper. Assert each `PolicyError`'s text holds the offending text.

**Criterion 5** imports `WitnessPatterns` inside the test body. The
template's comments cite no `DESIGN.md` section, since
`test_a_template_cites_no_saffron_design_section` reads every template.

**False survivors.** Two shapes stay green under a constant mutant
although the witness is sound. One feeds the constant in, such as
`LIMIT + 1`, and expects behaviour from it. The other names the constant
only in a comment, a docstring or a string. `witness` is advisory at
`standard` and blocks at `elevated` (§5.4.1). So such a survivor blocks
only an elevated diff, and its message names the remedy.

**The estimate is measured.** A prototype held the policy model, the new
module, the suite wiring, the template block and every witness above.
Its diff came to 1,743 changed tokens, 436 lines at four tokens a line.
The margin covers fuller docstrings, the two in `witness.py` among them,
and the skill's edit. Every wrong
version listed above failed its witness on that prototype. Each new
witness failed with the source at the tree base.
