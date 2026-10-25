---
id: SA-0319
title: "`factory:claim` carries two `rdfs:domain` triples, so a reasoner reads every finding as a principle"
type: bug
priority: 3
depends_on: [SA-0318]
estimated_lines: 89
estimate_measured: true
touches:
  - ontology/factory.ttl
  - ontology/shapes/factory-shapes.ttl
  - ontology/design_record.py
  - tests/ontology/fixtures/negative/PrincipleShape.ttl
  - tests/ontology/test_vocabulary.py
  - tests/ontology/test_design_record.py
  - tests/ontology/test_shapes.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
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
  - ontology/queries/**
  - ontology/vendor/**
  - ontology/render.py
  - ontology/spans.py
  - ontology/RATIONALE.md
  - tests/ontology/fixtures/lifecycle.ttl
  - tests/ontology/test_no_dead_terms.py
  - tests/ontology/test_generated_surfaces_are_current.py
  - tests/ontology/test_queries.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 22
max_attempts: 3
max_turns: 150
risk: standard
acceptance:
  - claim: >-
      No property in the `factory:` namespace carries more than one
      `rdfs:domain` triple in `ontology/factory.ttl`. `factory:claim` keeps
      the one domain `factory:Finding`. The new `factory:principleClaim` is
      an `owl:DatatypeProperty` with domain `factory:Principle` and range
      `xsd:string`. The witness asserts both declarations and that the
      real vocabulary has no property with two domains. The check counts
      `rdfs:domain` triples per subject in the namespace, whatever the
      subject's type. Through the same check, the witness then adds a second
      domain to one datatype property and to one object property in a copy
      of the vocabulary. It also gives two domains to a new subject typed as
      neither. It asserts the check names exactly those three.
    witness: tests/ontology/test_vocabulary.py::test_no_factory_property_carries_two_domains
    mutant:
      file: ontology/factory.ttl
      find: "factory:claim        a owl:DatatypeProperty ; rdfs:domain factory:Finding ;"
      replace: "factory:claim        a owl:DatatypeProperty ; rdfs:domain factory:Finding, factory:Principle ;"
    wrong_versions:
      - "The check names `factory:claim` and asserts its domains alone, so a second property given two domains passes."
      - "The check reads only subjects typed `owl:DatatypeProperty`, so an object property with two domains passes."
      - "The check reads only subjects typed `owl:DatatypeProperty` or `owl:ObjectProperty`, so the untyped subject with two domains passes."
      - "The check counts `rdfs:domain` occurrences per text line of the file, so a domain declared in a second statement block passes."
      - "The check reads one domain per property with `Graph.value`, which returns one of the two and never sees the second."
      - "`factory:principleClaim` is declared with no `rdfs:range`, or with `factory:Principle` as an extra domain of `factory:claim` kept beside it."
  - claim: >-
      `ontology/design_record.py` states each principle's claim under
      `factory:principleClaim`, and `principles` reads it from there. The
      parsed design record holds no `factory:claim` triple at all. The
      witness parses the real appendix records and asserts three things.
      Every `factory:Principle` node has exactly one `factory:principleClaim`
      value. No triple in the graph has `factory:claim` as its predicate.
      The claims `principles` returns equal those values, number for number.
    witness: tests/ontology/test_design_record.py::test_a_principles_claim_is_stated_under_its_own_property
    mutant:
      file: ontology/design_record.py
      find: "graph.add((node, FACTORY.contributedBy, appendix))"
      replace: "graph.add((node, FACTORY.contributedBy, appendix)); graph.add((node, FACTORY.claim, rdflib.Literal('a claim kept for compatibility')))"
    wrong_versions:
      - "`parse` writes the claim under both properties, for compatibility."
      - "`parse` writes `factory:principleClaim` and `principles` still reads `factory:claim`, so `_one` raises on every principle."
      - "The witness checks one principle node rather than every one."
  - claim: >-
      `factory:PrincipleShape` constrains `factory:principleClaim` with the
      four constraints it held on `factory:claim`: at least one value, at
      most one, datatype `xsd:string`, and a minimum length of 12. It no
      longer names `factory:claim`. The witness validates five one-principle
      graphs against the committed shapes, each with a typed revision
      appendix that conforms. A principle with one 12-character
      `factory:principleClaim` conforms. Four are refused, and the only
      shape any of them violates is `factory:PrincipleShape`. One states its
      claim under `factory:claim` alone. One has an 11-character
      `factory:principleClaim`. One has two distinct 12-character values.
      One has a 14-digit `xsd:integer` value. The witness then validates
      the committed negative fixture
      `tests/ontology/fixtures/negative/PrincipleShape.ttl` and asserts the
      set of its results' `sh:resultPath` values is exactly
      `factory:contributedBy`.
    witness: tests/ontology/test_shapes.py::test_the_principle_shape_constrains_the_principle_claim_property
    mutant:
      file: ontology/shapes/factory-shapes.ttl
      find: "sh:datatype xsd:string ; sh:minLength 12 ]"
      replace: "sh:datatype xsd:string ]"
    wrong_versions:
      - "`PrincipleShape` keeps a property shape on `factory:claim` beside the new one, so a principle stating only `factory:principleClaim` is refused."
      - "The new property shape carries `sh:minCount 1` alone, so an 11-character claim, two claims and an integer claim all conform."
      - "The new property shape drops `sh:datatype`, so the integer claim conforms."
      - "The new property shape drops `sh:maxCount`, so two claims conform."
      - "The witness asserts only that each refused graph fails to conform, so a refusal by `RevisionAppendixShape` over a malformed appendix passes it."
      - "The negative fixture keeps its claim under `factory:claim`, so it also trips the new property's minimum count."
  - claim: >-
      `DESIGN.md`'s principle index renders byte-identical from the appendix
      records after the change.
    witness: tests/ontology/test_design_record.py::test_the_committed_index_is_current_with_the_appendices
    preserves: true
  - claim: >-
      `DESIGN.md`'s appendix index, whose last column `principles` fills,
      renders byte-identical from the appendix records after the change.
    witness: tests/ontology/test_design_record.py::test_the_committed_appendix_index_is_current_with_the_records
    preserves: true
  - claim: >-
      Every term in the `factory:` namespace still has a reader in a query
      or a shape, `factory:principleClaim` included.
    witness: tests/ontology/test_no_dead_terms.py::test_no_term_exists_without_a_reader
    preserves: true
---

## Context

Backlog item **b-7aefb8**, under `DESIGN.md` §4.6. Every line cited below
was read at `f933aa01`, which stacks this spec on `SA-0317` and `SA-0318`.
Neither of those specs edits a property declaration. `SA-0318` adds class
labels to `ontology/factory.ttl`, so its line numbers can move when it
lands. Each declaration below is named by its text as well.

`ontology/factory.ttl` declares `factory:claim` twice. Line 141 gives it
`rdfs:domain factory:Finding`, and line 263, in the design-record block,
gives it `rdfs:domain factory:Principle`. RDFS reads two domains as an
intersection, so a reasoner infers that every node with a claim is both a
finding and a principle. Nothing in the repo runs a reasoner. The `shacl`
gate validates with shapes, and `pyshacl` is called with no inference at
`tests/ontology/test_shapes.py:46`. So the defect reaches only an external
reader of the graph. The vocabulary's alignment with PROV-O and EARL exists
for that reader (§4.6 rule 2).

The vocabulary holds 33 `rdfs:domain` triples at base, by a graph parse.
`factory:claim` is the only `factory:` property with more than one. No property has two `rdfs:range` triples. Both declarations
of `factory:claim` give the range `xsd:string`, and the graph holds that
triple once.

Every reader and writer of `factory:claim` at base, by `git grep` for
`factory:claim`, `FACTORY.claim` and `factory.claim`, the finding side
first:

- `ontology/factory.ttl:141` declares the Finding domain.
- `ontology/shapes/factory-shapes.ttl:210` is the finding shape's reader.
- `ontology/queries/view/V4-task-findings.rq:13` is the view's findings
  query reading it.
- `saffron/view/graph.py:357` is the view's graph writing it for a finding.
- `tests/ontology/fixtures/lifecycle.ttl:204` is one finding stating it.
- `ontology/factory.ttl:263` declares the Principle domain.
- `ontology/shapes/factory-shapes.ttl:339-340` is the principle shape's
  reader.
- `ontology/design_record.py:93` writes it for a principle, inside `parse`.
- `ontology/design_record.py:117` reads it through `_one`, inside
  `principles`.
- `tests/ontology/fixtures/negative/PrincipleShape.ttl:8` is the negative
  fixture's principle stating it.

No expected output under `ontology/queries/expected/` names the property.
`V4-task-findings.csv` carries the bound `claim` column of the view's
query, which the finding side keeps. `docs/superpowers/plans/` quotes the property in two plans,
which are history and stay as written.
`docs/superpowers/specs/2026-10-05-run-record-view-design.md:93` names
`factory:claim` on `Finding` alone, which stays true.

## Problem

The operator settled the split. The finding keeps `factory:claim`,
because it matches the `findings.claim` column of §4.1 and the view's
query. The principle moves to a new property, `factory:principleClaim`,
with domain `factory:Principle` and range `xsd:string`. Every reader and
writer on the principle side of the list above moves to it. The finding
side stays as it is.

That leaves four edits and three tests.

1. `ontology/factory.ttl:263` declares `factory:principleClaim` in place
   of the second `factory:claim` declaration. The finding declaration at
   line 141 is unchanged.
2. `ontology/shapes/factory-shapes.ttl:339-340` moves the claim property
   shape inside `PrincipleShape` to the new path and keeps its four
   constraints. `FindingShape` at line 210 is unchanged.
3. `ontology/design_record.py:93` and `:117` move to the new property.
   `FACTORY` is the namespace object at `ontology/design_record.py:31`, so
   the new name is an attribute on it like the others.
4. `tests/ontology/fixtures/negative/PrincipleShape.ttl:8` states its
   claim under the new property. That fixture exists to show a principle
   with no contributing appendix refused, per its comment at lines 4 to 5.
   Left on the old property, it would also trip the new property's
   minimum count. `test_each_shape_rejects_its_negative_fixture` at
   `tests/ontology/test_shapes.py:51` still passes either way, because
   both violations belong to `PrincipleShape`. So criterion 3's witness
   holds this edit by the fixture's result paths.

A test fails when one `factory:` property carries two domains (criterion
1). It sits beside the other vocabulary tests in
`tests/ontology/test_vocabulary.py`.

The dead-term test reads only queries and shapes
(`tests/ontology/test_no_dead_terms.py:45-49`). The new property's reader
is `PrincipleShape`, so that test holds without change (criterion 6).
`factory:claim` keeps its readers in `FindingShape` and the view's query.

`DESIGN.md`'s principle and appendix indexes are rendered by
`uv run python -m ontology.render`. That render reads principle claims
through `design_record.principles`, at `ontology/design_record.py:140`
for the principle index and `:172` for the appendix index. The ADR index
(`render_adr_index`, `ontology/design_record.py:214`) reads no principle
claim. After the change the render leaves `DESIGN.md` byte-identical, and
criteria 4 and 5 hold it. `CONTEXT.md` and the shapes file's generated
`sh:in` lists render from closed sets alone
(`tests/ontology/test_generated_surfaces_are_current.py`). A new datatype
property joins no closed set, so neither moves.

## Out of scope

- The finding side: `FindingShape`, the view's query, `saffron/view/graph.py`
  and the lifecycle fixture all keep `factory:claim`.
- Running a reasoner, or adding an inference test. The domain count is the
  defect's whole cause, and criterion 1 holds it.
- `rdfs:comment` and `rdfs:label` lines in `ontology/factory.ttl`.
  `SA-0318` edits those, and this spec depends on it.
- A `CONTEXT.md` entry for the new property. `factory:principleNumber` and
  the other design-record properties have none either, and `CONTEXT.md`
  is `protected`.
- `docs/superpowers/plans/`, which records what was planned at the time.

## Notes for the agent

`SA-0318` lands first and edits comment and label lines in
`ontology/factory.ttl`. Write against the tree you are given and leave
every `rdfs:comment` and `rdfs:label` as you find it.

`ontology/shapes/**` and `ontology/*.py` are in `integrity.gate_config` in
`.saffron/policy.yaml`. This spec's `touches` declares
`ontology/shapes/factory-shapes.ttl` and `ontology/design_record.py`,
which exempts those two files (§5.4). Edit no other file under either
glob.

Each criterion with a mutant edits existing code, so its mutant pins text
the code already holds. Criteria 4 to 6 are `preserves` and name tests
that exist at base.

Criterion 1's witness reads the committed vocabulary with `rdflib`, as
`tests/ontology/test_vocabulary_agrees_with_code.py:46-51` does. Count the
`rdfs:domain` triples per subject in the namespace rather than per line of
text. Put the real-vocabulary assertion first, so the witness fails at
base. For the mutated copy, parse the vocabulary into a fresh graph and add
the extra triples there: a second domain on each of the two properties
below, and two domains on one new untyped local name. `factory:verdict` and
`factory:contributedBy`
are one datatype and one object property that carry one domain each today.

Criterion 2's witness builds its graph the way `_graph` does at
`tests/ontology/test_design_record.py:36-39`.

Criterion 3's witness follows the inline-graph pattern of
`tests/ontology/test_shapes.py:142-160`. A principle needs a
`factory:principleNumber` and a `factory:contributedBy` naming a node
typed `factory:RevisionAppendix`. That appendix needs an
`factory:appendixLetter` matching the pattern at
`ontology/shapes/factory-shapes.ttl:350` and one `factory:coversRevision`
(`:351-352`). Name the shape each refused graph violated with
`_named_shape_of` (`tests/ontology/test_shapes.py:12`), and assert that
set equals `PrincipleShape` alone, as lines 60-63 do for the negative
fixtures. A plain witness is one `def` driving all five graphs and the
fixture, never a parametrised test. `FIXTURES` in
`tests/ontology/ontology_paths.py:6` locates the fixture directory, and a
result's path is its `sh:resultPath` triple in the results graph.

Criterion 1's untyped subject is a new local name added only to the
copied graph, never to the committed vocabulary.

New docstrings and comments meet the `prose` ratchet at zero hits: no
em-dash, semicolon, contraction, perfect tense, hedge, or sentence over 25
words. Commit as each witness passes. `uv run python -m ontology.render`
must leave the tree unchanged when you run it at the end.
