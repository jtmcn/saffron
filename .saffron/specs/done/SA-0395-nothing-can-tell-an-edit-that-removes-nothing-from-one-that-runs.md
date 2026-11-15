---
id: SA-0395
title: "Nothing host-side can tell an edit that keeps its find and adds only lines the repo calls inert from one that changes what the file runs"
type: feature
priority: 3
risk: standard
estimated_lines: 164
estimate_measured: true
touches:
  - saffron/probe.py
  - tests/test_probe_check.py
pending_symbols:
  - saffron/probe.py::inert_edit
  - saffron/repos/policy.py::inert
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
  - saffron/cell/**
  - saffron/repos/**
  - saffron/phases/**
  - saffron/gates/**
  - saffron/qualify.py
  - saffron/intake.py
  - saffron/task.py
  - saffron/cli.py
  - tests/test_policy.py
  - tests/test_setup_saffron.py
  - tests/test_session.py
  - tests/test_review.py
  - tests/test_queued_specs.py
  - tests/test_scheduler.py
budget_usd: 26
max_attempts: 3
max_turns: 150
acceptance:
  - claim: >-
      `saffron/probe.py` gains `inert_edit(before, edit, patterns)`. It
      returns a reason when the edit adds only lines the repo declares
      inert, and `None` otherwise. `before` is the edited file's text and
      `patterns` is a policy's `probes.inert` list. The reason starts with
      the edit's file and says the edit removed nothing of its find. It is
      returned only when all of these hold. `patterns` is not empty. The
      edit's `replace` holds its `find` whole. The `find` occurs exactly once
      in `before`. The added text is `replace` with that `find` taken out
      once, the text before it and the text after it. Every non-blank added
      line fully matches some pattern, with `{name}` filled by `INERT_NAME`.
      Every name any added line binds through `{name}` is spelled by no word
      of `before`, a word inside a string included. Text added after the
      find is followed by a first non-blank kept line of `before`. Text added
      before it is followed by the find's own first line. Neither line sits
      deeper than the least indented added line. The witness declares four
      patterns: a parameterless `def` of a name starting with one
      underscore, an indented `pass`, an indented one-line docstring, and a
      comment line whose pattern holds a quantifier's braces. It drives seven
      refused edits. The `SA-0390` edit is refused at the end of a file, and
      before a blank line and a line of lesser indent. Others add a `def`
      holding a docstring, a `def` whose name a longer word of the file only
      contains, and a comment before the find at its own indent. One adds
      nothing, and one adds a comment. It drives sixteen edits that return
      `None`. Three bind a name the file calls, a name only a string spells,
      and a second name the file spells after a first it does not. Six add a
      line no pattern matches. They are an early `return`, a call, a matching
      line with a call after it, a call with a trailing comment, a decorator
      above a `def` and a `pass`, and a call default. Three let added lines
      adopt kept ones. A bare `def` line is added above a deeper line, the
      `SA-0390` edit lands mid-block with a blank line after it, and a `def`
      line is added before an indented find. Three fail the find rules: a
      find that occurs twice, one that is absent, and one dropped for an
      indented `pass`. Last, the edit that adds nothing returns `None` under
      no patterns.
    witness: tests/test_probe_check.py::test_an_edit_that_keeps_its_find_and_adds_only_inert_lines_is_refused
    wrong_versions:
      - An empty pattern list never checked, so an edit that adds nothing is refused with no patterns declared.
      - The find never looked for in the replace, so an edit that swaps its find for an indented `pass` is refused.
      - The find's count never checked, so an edit whose find occurs twice is judged and refused.
      - Only a find that occurs more than once turned away, so an absent find is judged.
      - A pattern matched at a line's start only, so `pass` followed by a call on the same line is refused.
      - A pattern searched anywhere in a line, so a line holding a call after a match is refused.
      - An end-anchored search, not a full match, so a call with a trailing comment is refused.
      - The pattern filled with `str.format`, so a pattern holding a quantifier's braces raises.
      - Blank added lines judged, so the `SA-0390` edit is not refused.
      - One matching added line enough, so a decorator above a matching `def` and `pass` is refused.
      - Every pattern required to match each line, so the `SA-0390` edit is not refused.
      - The bound name never checked, so a `def` named after a function the file calls is refused.
      - Only the first bound name checked, so a second name the file spells is refused.
      - The bound name looked for as a substring, so a name a longer word only contains is not refused.
      - The bound name looked for among the file's definitions only, so a name the file only calls is refused.
      - Strings left out of the name check, so a name only a string spells is refused.
      - Only text after the find judged, so a comment put before the find is not refused.
      - No indent guard, so a bare `def` line that adopts the deeper line after it is refused.
      - The guard applied to text after the find alone, so a `def` line before an indented find is refused.
      - The guard applied to text before the find alone, so the `SA-0390` edit mid-block is refused.
      - An equal indent taken as deeper, so a comment before the find at its own indent is not refused.
      - The kept line read as the next line even when blank, so the `SA-0390` edit mid-block is refused.
---

## Context

Backlog item **b-7fc792**, filed from spec loop run 70 while reviewing
#1203 (`SA-0390`). It cites `DESIGN.md` §5.4.1 and §5.5. Every line number
below was read at `dffa5474`.

**What happened**. `SA-0390` declared a wrong version for its queue line.
It reads "`risk` is left out, so it reads `standard`." REVIEW's
wrong-version session gave a reason that names deleting the `risk=`
keyword from `queue_line`. Its edit kept the whole `find` and appended
`def _risk_placeholder_removed_marker():` with an indented `pass`. The
witness passed under an edit that changed nothing, and the host filed the
version `survived` as an adequacy blocker. The task's `wrong-versions.json`
under `~/.saffron/batches/v0/SA-0390/` holds the edit and its outcome.

**What judges an edit today**. The REVIEW block puts each criterion probe
and each wrong version into one list of pairs
(`saffron/cell/session.py:3514`). `_apply_criterion_probes` takes that list
(`saffron/cell/session.py:2072`). It refuses a pair host-side when
`probe.probe_refusal` names a reason (`saffron/cell/session.py:2109-2120`).
`probe_refusal` reads only the path (`saffron/probe.py:154`). In the cell,
`worktree.source_mutated` yields a reason for six edits that apply nothing
(`saffron/cell/worktree.py:752-877`). Nothing judges an edit that applies
and changes nothing.

**Why the repo declares the shape**. Core knows nothing about languages
(`DESIGN.md:140`, §2.1). Where a core check needs a language's shape, the
repo declares it as patterns, as `integrity` and `witness` do
(`DESIGN.md:154`). The nearest model is the citation check's definitions.
`CitationPatterns` holds a list of `re` patterns, each with a `{name}`
placeholder, and its validator compiles each with the placeholder filled in
(`saffron/repos/policy.py:165-189`).

**What this pull request lands by hand**. `Policy` refuses an unknown key
(`saffron/repos/policy.py:225`), and the setup template must name every
`Policy` field (`tests/test_setup_saffron.py:158-166`). The template sits
under `.claude/`, where a cell cannot write. So the block, its loader test,
the template and this repo's declaration land together in this spec's own
pull request, as `SA-0314`'s citations block did. They are already in the
tree this spec runs on:

- `saffron/repos/policy.py` holds `INERT_NAME`, the fill for `{name}`: a
  named group `name` capturing one word. Beside `CitationPatterns` it holds
  `ProbePatterns`, whose one field `inert` is a list of `re` patterns. Its
  validator refuses a pattern holding `{name}` more than once, and one that
  does not compile once `INERT_NAME` fills it. `Policy.probes` defaults to
  an empty block.
- `tests/test_policy.py` holds
  `test_a_probes_block_is_checked_when_the_policy_loads`.
- The setup template declares an empty `probes:` block after `citations:`.
- `.saffron/policy.yaml` declares four `inert` patterns after `citations:`.
  They are a parameterless `def` of a name starting with one underscore, an
  indented `pass`, an indented one-line docstring and a comment line. Under
  them the `SA-0390` edit is refused.

## Problem

Add `inert_edit(before: str, edit: Mutant, patterns: Sequence[str]) -> str
| None` to `saffron/probe.py`, beside `probe_refusal`. It reads text, runs
nothing and knows no language. The rule is the criterion's claim.

Fill `{name}` with `INERT_NAME`, imported from `saffron.repos.policy`, by
plain string replacement. Never use `str.format`, since a pattern's braces
are regex. The validator uses the same fill, so a pattern that loads always
compiles here. Look for a bound name in `before` as a whole word. A `find`
that does not occur exactly once returns `None`, and `source_mutated` then
judges the edit in the cell, as at base.

The indent guard counts a line's leading whitespace and knows no language.
It stops one shape the line patterns cannot see. A `def` line added with no
body of its own takes the deeper lines after it as its body, so the kept
code moves. Measure each side the edit adds to on its own. Text after the
find meets the first non-blank line of `before` after the find. Text before
the find meets the line the find starts on, read from that line's start.

## Out of scope

- **The call**. `SA-0396` wires `inert_edit` into `_apply_criterion_probes`,
  passing the policy's `probes.inert`. The host-side read through
  `SA-0394`'s `files_after` lands there. So do the handling of an empty read
  and of a `GitError`, and the `unproven` record with its `refusal` key.
  The reworded docstrings that name `probe_refusal` as the only refusal
  land there too.
- **The policy block, its test, the template and this repo's patterns**.
  Each lands by hand in this spec's pull request, as the Context says.
- **Hand edits to `DESIGN.md` §5.4.1 and `CONTEXT.md`'s Wrong version
  entry**. They change with `SA-0396`, when the host starts declining such
  an edit. The §2.1 table's row for the inert patterns lands with
  `SA-0396` too, which wires the rule into REVIEW.
- **What the indent guard cannot see**. It compares one kept line with the
  added lines. An added comment line inside a multi-line string changes the
  string's value, and the guard does not cover it. An added docstring line
  inside an open call becomes an argument, and the guard does not cover
  that either. Nor can the rule see a method name a base class defines in
  another file. Each stays a stated limit of a line-wise rule.
- **A lens's own adequacy probe** (`saffron/cell/session.py:1877`). A later
  spec can call `inert_edit` there.
- **A `retired_first`**. Nothing calls the rule until `SA-0396`, and it
  refuses edits REVIEW names, never a spec.

## Notes for the agent

**The rule is new code**, so the criterion declares a witness and no
mutant, and `witness` will report `skip`.

**At base the witness fails in its body**. `probe.inert_edit` does not
exist there. `tests/test_probe_check.py` imports the module as
`probe_check` (`tests/test_probe_check.py:18`). Call the function through
it, and import nothing new at module scope.

**The witness** is one plain `def`. It declares its own four patterns, so
this repo's policy can change without moving it. Give the comment pattern a
quantifier's braces, such as `.{0,80}`. Hold one `before` text with a
private function. Its return calls a private name the file does not define,
and passes a string holding another private name. Hold a second `before`
with two functions, whose first has a blank line inside its body. Keep a
dict of refused edits and one of edits that return `None`, keyed by a case
name. Some cases pair an edit with their own `before`. Pass the name as each
assertion's message. For the find that occurs twice, pick a word the text
holds twice and make the `replace` that same word. For the absent find,
let the `replace` hold it and add a comment. For the adopting `def` line,
use `def g():`, an indented `x = 1` and an indented `return x`, with the
find `    x = 1` and the `replace` adding `def _f():` after it.

**The `dead` gate** reads `pending_symbols` while this spec is open. A
prototype measured vulture calling both `inert_edit` and the `inert` field
unused until `SA-0396` reads them.

**The `prose` gate** counts each new comment and docstring. Write none
with an em dash, a semicolon, a contraction, a hedge, the perfect tense or
a sentence over 25 words.

**Size**. A prototype measured 276 counted tokens in `saffron/probe.py`
and 380 in the witness, about 164 changed lines.
