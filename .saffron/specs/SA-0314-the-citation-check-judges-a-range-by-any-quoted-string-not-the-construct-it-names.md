---
id: SA-0314
title: The citation check judges a range by any quoted string in its sentence, not by the construct the citation names
type: bug
priority: 2
estimated_lines: 201
estimate_measured: true
pending_symbols:
  - saffron/repos/policy.py::definitions
touches:
  - saffron/spec_citations.py
  - tests/test_spec_citations.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
  - README.md
  - pyproject.toml
  - uv.lock
  - .saffron/**
  - .claude/skills/run-saffron-spec-loop/**
  - .claude/skills/setup-saffron/**
  - .claude/agents/**
  - ontology/**
  - tests/ontology/**
  - docs/**
  - harness/**
  - records/**
  - hooks/**
  - images/**
  - saffron/cli.py
  - saffron/batch.py
  - saffron/task.py
  - saffron/scheduler.py
  - saffron/ledger.py
  - saffron/repos/**
  - saffron/gates/**
  - saffron/cell/**
  - saffron/record/**
  - saffron/phases/**
  - saffron/agents/**
  - tests/test_cli.py
  - tests/test_batch.py
  - tests/test_spec_loop_driver.py
  - tests/test_scheduler.py
  - tests/test_policy.py
  - tests/test_setup_saffron.py
budget_usd: 30
max_attempts: 3
max_turns: 130
risk: standard
acceptance:
  - claim: >-
      `citation_defects` judges a citation by the constructs its clause
      names. A construct is a line the policy's definition patterns match,
      through the last line indented past it or a closing `)`, `]` or `}`
      level with it. A blank line inside does not end it. A range passes when it
      lies inside a named construct, holds one whole, or holds a named
      identifier, as a whole word, on a line outside every named construct. Any other range
      is refused with one line naming where each named construct sits. A
      clause that names no construct the file holds is not refused for
      that. A name is a backticked identifier in one of four forms, `x`,
      `a.b`, `f()` and `a.f(x)`, read by its last dotted part. The witness
      drives each form, the shapes of three real drifts, a `def`, an
      `async def` and a `class` construct, a construct closed by each
      bracket, and a token that is no identifier.
    witness: tests/test_spec_citations.py::test_citation_defects_judge_a_citation_by_the_construct_its_clause_names
    wrong_versions:
      - Every backticked string read as a name, so `IF NOT EXISTS` on line 44 clears that citation.
      - No use rule, so the `_print_summary` use on line 43 is refused.
      - Only a construct's own name counted as a use, so the `end_review` call on line 33 is refused.
      - A use inside the construct counted, so `dest` on lines 19 to 22 clears the range 17-22.
      - Any overlap with the construct passes, so the range 4-15 passes.
      - Inside read as starting on the header line, so the range 10-16 is refused.
      - A blank line ends the construct, so the citation of line 15 is refused.
      - A closing bracket level with the `def` ends the construct, so the citation of line 15 is refused.
      - A pattern searched anywhere in a line, so the comment on line 37 is a construct too.
      - The refusal names the first construct only, so line 21's report drops `38-39`.
      - Only the first declared pattern applied, so `Ledger` is never a construct.
      - A dotted name kept whole, so `git_mirror.export_saffron_dir(mirror, sha, dest)` names nothing.
      - A call form not read as a name, so the same citation names nothing.
      - A name matched as a substring, so `_diff_cache` on line 57 clears the citation of line 57.
      - A call with no arguments not read as a name, so `_diff()` names nothing and line 20 passes.
      - A `]` level with the `def` ends the construct, so the citation of line 50 is refused.
      - A `}` level with the `def` ends the construct, so the citation of line 56 is refused.
  - claim: >-
      A citation's names are those its own clause quotes, from the previous
      citation in its sentence or the sentence's start. A clause that names
      none takes the names of the clause before it in the same sentence. A
      list item starts a sentence, marked by `-`, `*` or `N.`. So does the
      text after a bold heading's closing `**`, when a capital, digit,
      backtick, quote or `*` follows. A bare number anchors to the nearest
      path before it, in its sentence and then in its paragraph, across its
      list items too. That path is a plain backticked path or one a
      citation carries.
    witness: tests/test_spec_citations.py::test_citation_defects_scope_names_to_each_citations_own_clause
    wrong_versions:
      - Names scoped to the whole sentence, so `_diff` refuses the `qualifications` citation of line 21.
      - No carry from the clause before, so the bare 21 after `_diff` passes.
      - A list item does not start a sentence, so `_diff` on the first item refuses the import on the second.
      - Only `-` marks a list item, so the `*` and the numbered paragraphs each refuse the import.
      - A bold heading does not end its sentence, so `_diff` in the heading refuses the import after it.
      - A bold heading ends only before a capital, so each heading followed by a backtick, digit, quote or `*` refuses the import.
      - The anchor resets at each list item, so the bare 4-6 in the second item has no path.
      - A bare number anchors to the paragraph's first plain path, so the bare 4-6 reads `pkg/other.py`.
      - A bare number anchors to the paragraph's first path citation, so the bare 5 reads `pkg/other.py`.
  - claim: >-
      The definition patterns come from `.saffron/policy.yaml` at the
      commit the citations are checked at, read from the mirror. A commit
      with no policy file, or a policy with no `citations:` block, finds no
      construct, so only the path and line checks apply. A policy edited in
      the working tree after the commit changes nothing. A policy at the
      commit that does not validate raises `PolicyError`.
    witness: tests/test_spec_citations.py::test_citation_defects_read_definition_patterns_from_the_policy_at_the_commit
    wrong_versions:
      - "`def` and `class` built into core, so the commit with no policy still refuses the range 4-15."
      - The policy read from the working tree, so the commit declaring `def` alone refuses the `Ledger` citation.
      - A policy that does not validate read as no patterns, so no `PolicyError` is raised.
  - claim: >-
      `citation_count_and_defects(mirror, commit, text)` returns how many
      citations the text makes and the defects `citation_defects` returns,
      which are its second half. A range starting below line 1 is refused,
      and so is one ending before it starts. Each holds for a path citation
      and an anchored bare one, and before the file is looked up.
    witness: tests/test_spec_citations.py::test_citation_count_and_defects_count_each_citation_and_refuse_a_range_before_line_one_or_reversed
    wrong_versions:
      - A reversed range not refused, so the range 6-2 resolves.
      - A start below line 1 not refused, so line 0 resolves.
      - The range checked after the file lookup, so the range 3-1 in `missing.py` reports as a missing file.
      - The count read as the number of defects, so it is 7 where the text makes 8.
      - The start checked after the file lookup, so `missing.py` line 0 reports as a missing file.
  - claim: >-
      Citations still resolve against the commit's tree as before. A missing
      file, a directory and a range past a file's end are refused, and a
      host and port, a dotted module name and a clock time are no citations.
    witness: tests/test_spec_citations.py::test_citation_defects_resolve_each_citation_at_the_given_commit
    preserves: true
  - claim: >-
      A bare citation still anchors only inside its own paragraph, and one
      with no path before it there is refused as unanchored.
    witness: tests/test_spec_citations.py::test_citation_defects_anchor_a_bare_line_number_inside_its_own_paragraph
    preserves: true
---

## Context

Backlog item **b-2da959**. It cites `DESIGN.md` §3.2, and the check runs in
the stack batch of §4.2.1. Every line number below was read at `af2831e8`.

**The check passes a drifted range and refuses a right one.**
`_paragraph_citations` gives each citation every other backticked
string of its sentence as `candidates` (`saffron/spec_citations.py:93`).
`_moved_lines` clears a citation when one candidate sits anywhere in its
range, as a substring (`saffron/spec_citations.py:111-123`). So a common
token clears a range that moved, and a name on the `def` line above a right
range refuses it. Run 46 measured it on `SA-0304` at `a0ef5401`. The check
refused 20 citations there, and 19 were right (#933). One said `run_stack_batch` creates its row at line 829 of
`saffron/batch.py`. That line was the `create_batch` call inside
`run_stack_batch`.

**It also passes a range that starts below line 1, or ends before it
starts.** Only the end is checked against the file
(`saffron/spec_citations.py:156`). With a start of 0, `_moved_lines` slices
`lines[-1:end]` (`saffron/spec_citations.py:111-123`). That is empty unless
the range ends on the file's last line.

**A sentence runs on past a list item and a bold heading.** A paragraph is
joined into one line before sentences are split (`saffron/spec_citations.py:63`).
`_SENTENCE_END` needs whitespace right after the period
(`saffron/spec_citations.py:33`). So `- item` lines merge into one sentence,
and `**Heading.** Text` stays one sentence. Refreshes for `SA-0305` and
`SA-0306` split sentences and widened ranges only to pass the check (#940,
#942).

**A bare number already takes the nearest path.** The loop sets
`last_path` at each path citation and each plain path, in text order
(`saffron/spec_citations.py:77-86`). #933 said four bare numbers took "the
paragraph's first path". In that paragraph `saffron/ledger.py` was both the
first and the nearest. No test puts a bare number after two different
paths in one paragraph.

**Who calls it.** `_stack_cite` returns
`citation_defects(pinned.mirror, head, spec_text)` (`saffron/cli.py:1295`).
The batch's `cite` call refuses a spec on any defect, and a raise is a miss
raised again (`saffron/batch.py:655-673`). The spec loop's `driver.py cite` keeps
its own copy until `SA-0317` points it at `citation_count_and_defects`.

**This pull request lands the policy key by hand.** Its lines below were
read at `929067bb`. `Policy` refuses an unknown key, so the key lands
before the cell. `CitationPatterns` holds one
field, `definitions`, a list of Python `re` patterns each holding `{name}`
(`saffron/repos/policy.py:162-186`). `Policy.citations` defaults to an empty
block (`saffron/repos/policy.py:189-200`). `parse_policy(raw: bytes)` parses
and validates a policy's bytes with no gate read on disk
(`saffron/repos/policy.py:274-283`). `load_policy` calls it.
`test_a_citations_block_is_checked_when_the_policy_loads` holds both
(`tests/test_policy.py:314-351`). The setup template declares an empty
block (`.claude/skills/setup-saffron/templates/policy.yaml:41-43`). This
repo declares `def`, `async def` and `class` in `.saffron/policy.yaml`.

## Problem

Judge a citation by the construct it names. What a definition line looks
like is language knowledge, so the repo declares it in its policy and core
reads only that (§2.1). Build the check in `saffron/spec_citations.py`
against the landed key, and edit no policy code.

**The patterns at the commit.** `citation_count_and_defects` reads
`.saffron/policy.yaml` at `commit` through `file_at`, only when the
`ls-tree` listing holds it. `file_at` returns `str`, so it encodes the text before `parse_policy`. No
file means no patterns. A `PolicyError` propagates.

**Names.** A citation's names are the backticked strings of its clause
that are identifiers, after a dotted path or a call: `x`, `a.b`, `f()`,
`a.f(x)`. Each reads as its last dotted part. Paths and citations are never
names. A clause runs from the previous citation in the sentence, or the
sentence's start, to the citation. A clause with no names takes the names
of the clause before it in the same sentence.

**Sentences.** A list item starts a new sentence. That is a line whose
first text is `-`, `*` or `N.`, then whitespace. A period followed by
`**` ends a sentence when whitespace and a capital, digit, backtick, quote
or `*` follow. The bare number anchor carries across list items in a
paragraph, as it does across sentences.

**Constructs.** For each name and each pattern, fill `{name}` with
`re.escape(name)` and match it at a line's start with `re.match`. A
matching line opens a construct. It runs to the last later non-blank line
indented past it. A non-blank line level with it whose text starts with
`)`, `]` or `}` continues it too. Any other non-blank line ends it.

**The judgement.** After the path and line checks, a citation whose names
find no construct passes. Otherwise it passes when its range lies inside
one or holds one whole. It also passes when a line of the range outside
every construct found holds a named identifier as a whole word. Count every name, not only construct names.
Otherwise refuse it with
`f"{path}:{range}: the construct it names sits at {path}:{spans}"`.
`spans` joins each construct's `first-last` by `", "`, in line order, with
`first` alone when the two are equal.

**The ranges.** Check the range's shape before the file. A start below 1
is `f"{path}:{range}: starts before line 1"`. An end before the start is
`f"{path}:{range}: ends before it starts"`. The order is no path, then
start, then end, then missing file, then past the end, then the construct.

**The counted entry.**

```python
def citation_count_and_defects(mirror: Path, commit: str, text: str) -> tuple[int, list[str]]: ...
```

It returns the citation count and the defects. `citation_defects` keeps its
signature and returns `citation_count_and_defects(mirror, commit, text)[1]`.
`saffron/cli.py` does not change. Rewrite `citation_defects`' docstring,
which states the quoted-text rule (`saffron/spec_citations.py:126-132`).
Name the construct rule and the range shapes in their place, within ten
lines.

## Out of scope

- **The spec loop's driver.** `SA-0317` makes `driver.py cite` call
  `citation_count_and_defects` and deletes its copy.
- **The policy key, its loader test, the setup template and this repo's
  declaration.** Each lands by hand in this spec's own pull request.
- **`CONTEXT.md`'s Policy entry.** It already omits `witness:`. Naming the
  new block there is vocabulary work for the operator.

## Notes for the agent

**The change is new code, so no criterion declares a mutant.** Each
witness tests code that does not exist at base. The `witness` gate reports
`skip` for each, and that is expected. The last two criteria are
`preserves` and name tests at base.

**What the rule cannot see, by design.** A drift that stays inside the
named construct passes, such as a line inside a long `main`. A clause
naming no construct the file holds passes, such as `predecessor.spec.id`.
A table in a SQL string is no construct, so the item's own `stack_finishes`
example still passes. A bare number after the wrong path passes when its
clause names nothing in that file. Measured over the 286 citations of six
refresh pull requests (#892, #897, #931, #933, #940, #942), a prototype
refused three. All three are real drifts the current check passes, and they
are the fixtures below. Over the 276 specs in `done/`, each at the commit
that added it, today's check reports 663 moved citations and the prototype
151. Of 12 of those 151 read at their commits, 10 were real drift. One cited
a call inside another function than the one its sentence names. One was
unclear.

**Import new names inside each test body.** A module-scope import of
`citation_count_and_defects` makes the reverted run a collection error,
which `revert` reads as `skip`.

**The `dead` gate.** Nothing in `saffron/` reads `definitions` until this
change does, so `pending_symbols` defers it while the spec is open.

**One old test keeps its name.** `census` fails a removed test name, so keep
`test_citation_defects_report_quoted_text_that_sits_on_other_lines`
(`tests/test_spec_citations.py:118`). Commit the policy below in its fixture
and assert `== []`, since no clause there names a construct. Its docstring
says so.

**The shared fixture.** Write one `mod/lib.py` holding these 57 lines, with
`pkg/other.py` holding three lines. Commit `.saffron/policy.yaml` holding
this block.

```yaml
citations:
  definitions:
    - '\s*(?:async\s+)?def\s+{name}\b'
    - '\s*class\s+{name}\b'
```

```python
LIB = [
    "import os",
    "",
    "",
    "def _diff(mirror, head):",
    '    """One layer\'s own commit."""',
    "    return run(mirror, head)",
    "",
    "",
    "def _review_one_layer(",
    "    ledger,",
    "    task_key,",
    "):",
    "    fields = layer_fields(ledger, task_key)",
    "",
    "    diff = _diff(fields.mirror, fields.head)",
    "    return review(diff)",
    "",
    "",
    "def export_saffron_dir(mirror, sha, dest):",
    '    """`.saffron/` under `dest`."""',
    '    archive = dest / "a.tar"',
    "    extract(archive, dest)",
    "    return dest",
    "",
    "",
    "class Ledger:",
    "    def create_batch(self):",
    "        return 1",
    "",
    "",
    "async def run_stack_batch(ledger):",
    "    batch = ledger.create_batch()",
    "    end_review(batch)",
    "    _print_summary(batch)",
    "    return batch",
    "",
    "# def _print_summary sits below",
    "def _print_summary(batch):",
    "    print(batch)",
    "",
    "",
    "def main():",
    "    _print_summary(None)",
    "    # IF NOT EXISTS",
    "",
    "",
    "def _rows(x=[",
    "    1,",
    "]):",
    "    return x",
    "",
    "",
    "def _shape(x={",
    '    "a": 1,',
    "}):",
    "    return x",
    "_diff_cache = {}",
]
```

The three real drifts are cut down from three citations. At `a0ef5401`,
lines 249 to 283 of `saffron/end_review.py` missed `_review_one_layer` at
257. At the same commit, lines 469 to 494 of `saffron/cli.py` missed
`_pushed_landed` at 490. At `5afa3c84`, lines 182 to 227 of
`saffron/repos/mirror.py` missed `export_saffron_dir` at 186. The last
passes today because `dest` sits in range.

**Fixture text.** In each block below, write «x» as x between backticks. The spec spells them so, or its own citation check reads the fixture paths.

**Criterion 1's text**, one paragraph per line with a blank line between, and its defects in order.

```text
«_review_one_layer» reads those fields («mod/lib.py:4-15»).
«_review_one_layer» reads them too («mod/lib.py:10-16»).
«export_saffron_dir» writes «.saffron/» under its «dest» («mod/lib.py:17-22»).
«export_saffron_dir» writes the archive («mod/lib.py:18-24»).
«run_stack_batch» creates its row at «mod/lib.py:32».
«Ledger» holds the writer («mod/lib.py:27-28»).
«Ledger» holds the writer («mod/lib.py:30-32»).
The module prints through «_print_summary» («mod/lib.py:43»).
After «_review_one_layer» returns, it calls «end_review» («mod/lib.py:33»).
«_print_summary» checks «IF NOT EXISTS» («mod/lib.py:44»).
«os» is read at «mod/lib.py:20».
«_review_one_layer» builds its diff («mod/lib.py:15»).
Both «_diff» and «_print_summary» matter («mod/lib.py:21»).
«git_mirror.export_saffron_dir(mirror, sha, dest)» writes it («mod/lib.py:17-22»).
«Ledger.create_batch» returns one («mod/lib.py:33»).
«_diff()» builds the patch («mod/lib.py:20»).
«_rows» returns them («mod/lib.py:50»).
«_shape» returns it («mod/lib.py:56»).
«_diff» is cached at «mod/lib.py:57».
«run_stack_batch» returns it («mod/lib.py:38»).
```

```text
mod/lib.py:4-15: the construct it names sits at mod/lib.py:9-16
mod/lib.py:17-22: the construct it names sits at mod/lib.py:19-23
mod/lib.py:30-32: the construct it names sits at mod/lib.py:26-28
mod/lib.py:44: the construct it names sits at mod/lib.py:38-39
mod/lib.py:21: the construct it names sits at mod/lib.py:4-6, 38-39
mod/lib.py:17-22: the construct it names sits at mod/lib.py:19-23
mod/lib.py:33: the construct it names sits at mod/lib.py:27-28
mod/lib.py:20: the construct it names sits at mod/lib.py:4-6
mod/lib.py:57: the construct it names sits at mod/lib.py:4-6
mod/lib.py:38: the construct it names sits at mod/lib.py:31-35
```

**Criterion 2's text.** Paragraphs are split by blank lines. Each list
paragraph is two lines.

```text
Every «qualifications» entry carries it («mod/lib.py:21»), and «_diff» sits at «mod/lib.py:4-6».

«_print_summary» prints the batch («mod/lib.py:39», «:43»).

«_diff» returns the patch («mod/lib.py:5», «:21»).

- «_diff» is the helper
- the import sits at «mod/lib.py:1»

* «_diff» is the helper
* the import sits at «mod/lib.py:1»

1. «_diff» is the helper
2. the import sits at «mod/lib.py:1»

**«_diff» is the helper.** The import sits at «mod/lib.py:1».

**«_diff» is the helper.** «mod/lib.py:1» holds the import.

**«_diff» is the helper.** 1 import sits at «mod/lib.py:1».

**«_diff» is the helper.** "The import" sits at «mod/lib.py:1».

**«_diff» is the helper.** *The import* sits at «mod/lib.py:1».

- the module is «mod/lib.py»
- «_diff» sits at «:4-6»

The helpers live in «pkg/other.py» and «mod/lib.py». «_diff» returns the patch («:4-6»).

The helpers live in «pkg/other.py». «_diff» in «mod/lib.py» returns the patch («:4-6»).

See «pkg/other.py:1» and «mod/lib.py:4-6». «_diff» returns it («:5»).
```

Its one defect is `mod/lib.py:21: the construct it names sits at mod/lib.py:4-6`.

**Criterion 3** checks two paragraphs, criterion 1's first and its
seventh, the `4-15` and `30-32` ones. It checks them at four
commits of one repository. The first has no policy file, and the second
holds `gates: {}`. Both return `[]`. The third declares only
`'\s*def\s+{name}\b'`. Before checking it, write the full two-pattern policy
into the working tree. It returns the `4-15` line alone. The fourth declares
`'def foo'` and raises `PolicyError`.

**Criterion 4's text** and its count of 8.

```text
See «mod/lib.py:0», «mod/lib.py:0-3» and «mod/lib.py:6-2». Then «mod/lib.py:1», «missing.py:0» and «missing.py:3-1».

The module «mod/lib.py» starts at «:0» and runs «:9-4».
```

```text
mod/lib.py:0: starts before line 1
mod/lib.py:0-3: starts before line 1
mod/lib.py:6-2: ends before it starts
missing.py:0: starts before line 1
missing.py:3-1: ends before it starts
mod/lib.py:0: starts before line 1
mod/lib.py:9-4: ends before it starts
```

Assert `citation_defects` returns the same list.

**Measured on a prototype at `af2831e8`.** The prototype passed each
witness above and failed each at base. It killed every wrong version
listed. It also passed both `preserves` witnesses. `size_gate`'s counter put
`saffron/spec_citations.py` at 802 changed tokens. The policy key is no
longer the cell's, so its 156 tokens are left out.
Tests are not counted. `estimated_lines` is that count over four.

**The `prose` gate** counts every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words. Keep each docstring within ten lines.
