---
id: SA-0318
title: "No test holds a `factory:` class to its `CONTEXT.md` entry, and class comments restate the entries they drift from"
type: feature
priority: 3
depends_on: [SA-0317]
estimated_lines: 80
estimate_measured: true
touches:
  - tests/ontology/**
  - ontology/factory.ttl
forbidden:
  - CONTEXT.md
  - DESIGN.md
  - CLAUDE.md
  - README.md
  - pyproject.toml
  - uv.lock
  - .saffron/**
  - .claude/**
  - docs/**
  - saffron/**
  - harness/**
  - records/**
  - hooks/**
  - images/**
  - ontology/shapes/**
  - ontology/queries/**
  - ontology/*.py
  - ontology/RATIONALE.md
  - tests/ontology/conftest.py
  - tests/ontology/fixtures/**
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 28
max_attempts: 3
max_turns: 120
risk: standard
acceptance:
  - claim: >-
      Every `owl:Class` in the `factory:` namespace of `ontology/factory.ttl`
      has an `rdfs:label` that equals exactly one `CONTEXT.md` headword after
      casefolding, or is a key of the test's exclusion mapping. A headword is
      a line that opens with a bold term and a colon. The check reports a
      class with no label, a label equal to no headword, and a label equal
      to two. It reads no class outside the namespace. It counts no bullet
      and no bold term without its colon as a headword, and no label matches
      a headword it is only a prefix of.
      It also reports an exclusion that names no `factory:` class, one whose
      reason is blank, and one whose class has a label equal to a headword.
    witness: tests/ontology/test_vocabulary_agrees_with_context.py::test_every_factory_class_has_one_context_entry_or_a_stated_exclusion
    mutant:
      file: ontology/factory.ttl
      find: rdfs:label "diff"
      replace: rdfs:label "change"
    wrong_versions:
      - "A label matches a headword it is a substring of, so a label of plan passes on the Plan checkpoint entry."
      - "A label matches a headword it is a prefix of."
      - "A label and a headword are compared case-sensitively, so no lowercase label matches its capitalised headword."
      - "A headword is any line opening with a bold term, colon or not, so a paragraph opening with a bold phrase counts."
      - "A bullet such as the Core gates line counts as a headword."
      - "The headword pattern is not anchored at a line start, so a bold term with a colon mid-line counts."
      - "A class with no label is skipped rather than reported."
      - "A label equal to two headwords passes, because the check asks for at least one."
      - "Every owl:Class in the graph is read, so a class in another namespace is reported."
      - "An exclusion whose class has a label equal to a headword is accepted."
      - "An exclusion with a blank reason is accepted."
      - "An exclusion that names no declared class is accepted."
      - "The check iterates CLOSED_SETS rather than the graph's classes."
  - claim: >-
      The seven classes that have a `CONTEXT.md` entry and no label at base
      each carry a label equal to that entry's headword after casefolding:
      `TerminalState`, `RiskTier`, `BatchStopReason`, `PreflightOutcome`,
      `EventKind`, `FactKind` and `Severity`.
    witness: tests/ontology/test_vocabulary_agrees_with_context.py::test_the_seven_classes_with_an_entry_carry_its_headword_as_label
    wrong_versions:
      - "The seven are added to the exclusion mapping instead of labelled."
      - "Each is labelled with its local name, such as TerminalState, which equals no headword."
      - "Only TerminalState is labelled, since its entry is the one the item quotes."
  - claim: >-
      No `factory:` class whose label equals a `CONTEXT.md` headword carries
      an `rdfs:comment`.
    witness: tests/ontology/test_vocabulary_agrees_with_context.py::test_no_class_with_an_entry_restates_it_in_a_comment
    mutant:
      file: ontology/factory.ttl
      find: rdfs:label "spec" .
      replace: 'rdfs:label "spec" ; rdfs:comment "A markdown file." .'
    wrong_versions:
      - "Only the classes CLOSED_SETS names are checked, so a comment on the Plan or the Spec class passes."
      - "Only TerminalState's comment is deleted, since its count is the one the item quotes."
      - "The check reads comments on classes the exclusion mapping names and skips the matched ones."
---

## Context

Backlog item **b-c16c6c**, under `DESIGN.md` §4.6. The parked record
**b-2227b0** says why the entries stay in `CONTEXT.md` and are not moved into
the graph: a cross-check test closes every measured gap at less cost. This spec
is that test for the classes, and the comment cleanup the item asks for.

Every line cited below was read at `b2acd68f`. `SA-0317` (b-545741) edits
`tests/ontology/test_vocabulary_agrees_with_context.py` before this spec runs.
It makes `context_enumeration` import `definition_sentence` from
`ontology/spans.py`. So find each function in that file by name, not by line.

**The test checks the closed sets and nothing else.**
`tests/ontology/test_vocabulary_agrees_with_context.py:22-34` maps 11
`CONTEXT.md` terms to classes in `CLOSED_SETS`. Its one parametrised test compares
each set's members (`:70-79`). No test reads a class's `rdfs:label` against
`CONTEXT.md`. Its module docstring says "This checks the overlap alone"
(`:5`).

**The graph's classes and their labels.** `ontology/factory.ttl` declares 44
`owl:Class` subjects in the `factory:` namespace, measured with rdflib at
base. They fall into four groups.

- 26 carry a label that equals one headword after casefolding.
- 7 have an entry and no label. They are `TerminalState`
  (`ontology/factory.ttl:153-154`), `RiskTier` (`:177`), `BatchStopReason`
  (`:187`), `PreflightOutcome` (`:193`), `EventKind` (`:198`), `FactKind`
  (`:207`) and `Severity` (`:230`). Their headwords are at `CONTEXT.md:679`, `:332`, `:150`, `:241`,
  `:853`, `:860` and `:615`.
- 5 carry a label and had no entry at base: `AcceptanceCriterion`
  (`ontology/factory.ttl:37-40`), `Plan` (`:41-42`), `ScopeProposal` (`:43`), `Diff`
  (`:44`) and `PullRequest` (`:45`). Their entries are written by hand in this
  spec's own pull request, because `CONTEXT.md` is `protected`
  (`.saffron/policy.yaml:59-61`). **This spec assumes the five present at its
  base**, headed Acceptance criterion, Diff, Plan, Pull request and Scope
  proposal.
- 6 have no headword of their own. `CoreGate`, `ContractGate` and
  `RepoDefinedGate` (`ontology/factory.ttl:70-72`) are bullets inside the Gate entry
  (`CONTEXT.md:363-374`). `BlockingLevel` (`ontology/factory.ttl:233-236`) has three
  members, and the Blocking / advisory entry defines two
  (`CONTEXT.md:418-421`). `Role` (`ontology/factory.ttl:238-244`) carries the three
  judgements on a rebuttal, whose terms are the Verdict, Adjudication and
  Rebuttal entries (`CONTEXT.md:640`, `:646`, `:652`). `SpecType`
  (`ontology/factory.ttl:227-228`) holds the frontmatter `type` values, and no entry
  defines them.

**A headword.** `CONTEXT.md` writes an entry as a line that opens with a bold
term and a colon. ADR 11 counts 134 of them (`docs/adr/0011-an-avoided-phrase-is-banned-or-confusable.md:17`),
and so does a line-anchored match at base, with no two equal after casefolding.
Two bold phrases open a line with no colon, at `CONTEXT.md:137` and `:232`. The
second is a lowercase preflight outcome, which a pattern without the colon
reads as a second headword for that class.

**The comments.** `factory.ttl` holds 21 `rdfs:comment` values, measured with
rdflib. A 22nd text match, at `ontology/factory.ttl:255`, sits inside a `##`
Turtle comment. Ten are on classes, ten on properties, and one on the ontology
itself (`:12`).
`DESIGN.md` §4.6 says `rdfs:comment` prose "is the part that is cheap to fake"
(`DESIGN.md:618`). The comment on `TerminalState` says `CONTEXT.md` §6 lists
six terminal states (`ontology/factory.ttl:154`), and the entry lists 14
(`CONTEXT.md:679-683`).

## Problem

1. **The class check.** Add to
   `tests/ontology/test_vocabulary_agrees_with_context.py` a check that reads
   `factory.ttl` and `CONTEXT.md` as text. It returns one problem per class,
   per the first criterion, and passes on the real tree. Keep the exclusion
   mapping in the test file, keyed by local class name, with a reason per
   entry. It names the six classes of the last group above, and no other.
   Write the check as functions over the two texts and the mapping. The
   witness can then drive the same functions over a small inline graph and
   a few lines of `CONTEXT.md`. A headword is a line in `CONTEXT.md` that
   opens with a bold term and a colon, as ADR 11 counts them. Define no rule
   for where a first sentence ends. `SA-0317` owns that rule.
2. **The seven labels.** In `factory.ttl`, give each class of the second group
   an `rdfs:label`: its headword in lower case, as the existing labels are.
3. **The class comments.** Apply the table in the notes to the ten class
   comments. Leave the ten property comments and the ontology's own comment
   as they are.
4. **The module docstring.** It says the file checks the closed-set overlap
   alone (`tests/ontology/test_vocabulary_agrees_with_context.py:5`). Make it
   name the class check too, within ten lines.

## Out of scope

- The closed-set members. `CLOSED_SETS` holds 11 sets, and this spec does not
  widen it. The members of `SpecType`, `BlockingLevel` and `Role` are held to
  no entry, and no test names them. The origin item asks for every
  closed-set member to be held to an entry or to its set's entry. That half
  is left for a later item.
- The five `CONTEXT.md` entries. They are written by hand in this spec's
  pull request, before any cell runs.
- The property declarations in `factory.ttl`, including their comments.
  `SA-0319` (b-7aefb8), stacked above this spec, renames a `factory:claim`
  property there.
- `ontology/RATIONALE.md:32-36` still says `CONTEXT.md` §6 lists six terminal
  states. It is a dated verdict, and it stays as written.
- The rendered spans and `ontology/spans.py`. Adding a label changes no
  member a closed set renders.

## Notes for the agent

**The comment rule.** A comment is definitional when it says what the term is
or does in the factory. That is what a `CONTEXT.md` entry says, so it is
deleted. A comment records a modelling choice when it says why the graph
declares the term as it does: a class rather than a literal, or a property
rather than an order. That kind becomes a `#` comment directly above the
declaration. A comment holding both is split. The ten class comments are
decided here, and you judge none.

| line | class | kind | do |
|---|---|---|---|
| `ontology/factory.ttl:40` | `AcceptanceCriterion` | modelling: why it is a class | move it to a `#` line above the declaration, text unchanged |
| `ontology/factory.ttl:42` | `Plan` | definitional, as the hand-written Plan entry | delete |
| `ontology/factory.ttl:61` | `CriticLens` | definitional, as `CONTEXT.md:569-574` | delete |
| `ontology/factory.ttl:96` | `GateRole` | definitional, as `CONTEXT.md:356-358` | delete |
| `ontology/factory.ttl:148` | `TaskState` | definitional, as `CONTEXT.md:661-663` | delete |
| `ontology/factory.ttl:150` | `InFlightState` | definitional, as `CONTEXT.md:674-677` | delete |
| `ontology/factory.ttl:152` | `EndState` | definitional, as `CONTEXT.md:665-672` | delete |
| `ontology/factory.ttl:154` | `TerminalState` | definitional, with a stale count | delete, and add the label in its place |
| `ontology/factory.ttl:259` | `Principle` | both | delete the first sentence and move the second to a `#` comment |
| `ontology/factory.ttl:271` | `ADR` | definitional, as `CONTEXT.md:1001-1007` | delete |

For `Principle`, write the `#` comment as these two lines, with no dash.

```
# Its number is an address. DESIGN.md, CONTEXT.md, the backlog and
# docs/evidence/ all cite it, so it is a property here rather than an ordering.
```

Place it below the
`##` block that opens the design record
(`ontology/factory.ttl:246-256`). No criterion witnesses
the two `#` comments, because a test of comment text guards nothing.

The comments at `ontology/factory.ttl:12`, `:113`, `:119`, `:122`, `:127`, `:130`, `:132`,
`:135`, `:139`, `:265` and `:268` stay. The first is on the ontology, and the
rest are on properties.

**The witnesses.** The first criterion edits `factory.ttl` text that exists at
base, so it declares a mutant. So does the third. The second adds new labels,
so it declares a witness alone, and `witness` will report `skip` for it.

- The first witness asserts the real tree has no problem and no stale
  exclusion. In the same test, drive the functions over an inline Turtle
  graph and inline `CONTEXT.md` text, and assert the exact problem list.
  Drive six cases in that graph. One label is only a prefix of a headword.
  One class has no label. One label equals two headwords that differ only in
  case. One label equals a bullet's bold term, and one a bold term with no
  colon. One class lies outside the namespace. Drive one headword in a
  different case, which must match. Then drive the exclusion check with three
  entries: a name that is no class, a class with a blank reason, and a class
  whose label equals a headword. Keep the inline cases in this test and not
  in a test of their own. A test of the functions alone stays green with
  `factory.ttl` reverted, and `revert` blocks it.
- The second witness reads the real tree and asserts each of the seven
  matches exactly its own headword.
- The third witness reads the real tree. It checks every class whose label
  equals a headword, not only those `CLOSED_SETS` names.

Parse the graph with rdflib, as `ontology_members` does. Run
`uv run pytest tests/ontology` and `uv run .saffron/gates/shacl` before you
commit. Commit as each witness passes.

A prototype of this change passed the whole of `tests/ontology` and the
`shacl` gate. With `factory.ttl` reverted, all three witnesses failed. Twelve of the
wrong versions under the first criterion were run against its witness, and
each failed it. The one left, iterating `CLOSED_SETS`, fails on the real
tree's `Plan` class. Both mutants failed their witnesses.
