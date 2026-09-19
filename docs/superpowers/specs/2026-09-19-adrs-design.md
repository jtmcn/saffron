# ADRs: one decision per file

Backlog item b-9ff0fd, designed. Stacked on the appendices move
(`docs/superpowers/specs/2026-09-18-appendices-as-records-design.md`), which made
the appendices records and left one decision's current state spread across the
appendices that touched it.

In this document an example id in braces, "ADR {4}", is a placeholder.
`tests/test_citations.py` scans `docs/` and resolves every "ADR N" once the
reader lands, so only "ADR 1" is spelled plainly.

## The problem

A revision records several decisions, and an appendix is never edited. So where a
decision stands today means reading every appendix that touched it: the emitter
spans `ontology/RATIONALE.md` and Appendices O, P and T. Nothing marks a decision
replaced. Appendix U narrowed Saffron's refusal of ADRs to a parallel tree, and
recorded the intent to keep decisions as their own records.

## Decisions taken in design

- **The name is ADR.** It reverses `CONTEXT.md` §11's _Avoid_ entry and Appendix
  U's "ADR still means prior art's records". Appendices are never edited, so ADR 1
  records the reversal and cites U.
- **Scope.** The kind, its checks and readers, the reviewer agent, and ADR 1.
  Other decisions migrate later, one ADR each.
- **No new appendix and no rev 26.** The decision's record is ADR 1. An appendix
  beside it would hold the same decision twice.

## The record

### Location and id

`docs/adr/0001-<slug>.md`, loaded as `records/`' third kind, `KINDS["adr"]`, with
pattern `^(\d{4})-[a-z0-9-]+\.md$`. The id is an integer. The filename prefix is
the id zero-padded to four digits, and `load` compares them as integers.

Ids run 1, 2, 3 with no gap or repeat, and prose cites "ADR 1". Prior art's
records keep the dashed, zero-padded `ADR-NNNN` form, which Appendix D cites
(`ADR-0008`, `ADR-0019`, `ADR-0020`) and which cannot change. The two forms differ
by the dash, so a citation reader tells them apart.

Two branches can claim the same next number. `check_adr_ids` refuses the
duplicate before either merges, and renumbering an unmerged ADR is cheap because
nothing cites it yet.

### Frontmatter

```yaml
id: 1
title: "Decisions are recorded one per file as ADRs"
status: accepted
date: 2026-09-19
supersedes: []
superseded_by: []
appendices: [P, U]
principles: [62]
```

Unknown keys are refused. `status` is `accepted`, `superseded` or `deprecated`.
There is no `proposed`: a proposed ADR is its open pull request. `deprecated`
means withdrawn with nothing replacing it. `appendices` names the appendices that
argued the decision, and may be empty. `principles` lists every principle the
decision rests on or departs from.

### Supersession

It is recorded on both sides. When ADR {4} replaces ADR 1 and ADR {3}, ADR {4}
lists `supersedes: [1, 3]`. ADR 1 and ADR {3} each get `status: superseded` and
`superseded_by: [4]` in the same pull request. These are the only edits an
accepted ADR receives.

`check_adr_supersession` holds that:

- every id named on either side exists;
- every id in `supersedes` is lower than the ADR naming it;
- the two sides agree: `a` in `b.supersedes` if and only if `b` in `a.superseded_by`;
- `status` is `superseded` if and only if `superseded_by` is non-empty;
- a `deprecated` ADR has an empty `superseded_by`.

### Body

The body has `## Context`, `## Decision`, an optional `## Options considered`,
`## Principles`, then `## Consequences`, in that order. Today `Kind.sections`
names allowed headings and their order, and presence is checked only for the
backlog, by `_check_sections`. The ADR kind needs presence too. `Kind` gains
`required: tuple[str, ...]`, the subset that must appear, and `_sectioned`
refuses a missing one. The backlog's `required` is `("Problem",)`. Its
status-dependent rules stay in `_check_sections`.

## Validation against the principles

Validation has two halves. The declaration is checked mechanically, and a reviewer
judges the ADR.

### Declared

`## Principles` has one bullet per listed principle:

```markdown
- **62** upholds. <why>
- **57** departs. <why the departure is worth it>
```

`check_adr_principles` holds that:

- every number in `principles` exists in the principle sequence, read from the
  appendix records through `ontology.design_record`'s parse;
- the bullets name exactly the `principles` set, each once;
- each bullet's verb is `upholds` or `departs`;
- with an empty `principles`, the section is one line that begins
  `Judged against no principle.`, so "none" is written down, not omitted.

The integrity checks live in `tests/records/check.py`, since `1fb6c55` moved
them out of `records/`. The principle numbers reach `check_all` as an argument,
the way `sections` already does, so a fixture passes its own set. The live test
passes them in from `ontology.design_record`.

### Reviewed

A new agent, `.claude/agents/adr-reviewer.md`, modeled on
`.claude/agents/spec-reviewer.md`: read-only, run by hand on an ADR's pull request
before it merges. It reads the ADR, `DESIGN.md`'s principle index, the appendix
bodies whose principles the ADR names or should, and every accepted ADR. It
reports, with severities:

1. principles the ADR should have named and did not;
2. an `upholds` that is a departure, or a `departs` whose reason does not answer
   the principle's case;
3. a conflict with an accepted ADR that this one does not supersede;
4. a claim in `## Context` that the cited appendices do not support.

It is not a gate. ADRs are `protected`, so no cell writes one, and a gate would
run on work no cell produces.

## What reads the records

- **`records/`.** `records list adr` prints `id  status  title`.
  `records show --kind adr 1` prints one ADR, and a bare `records show 1` stays
  backlog item 1. `check_all` in `tests/records/check.py` gains `check_adr_ids`, `check_adr_supersession`,
  `check_adr_principles`, and a check that every `appendices` letter exists.
  `CITING` and `LIVE_SURFACES` gain `docs/adr`.
- **`ontology/`.** `factory.ttl` gains `factory:ADR` (`rdfs:label "ADR"`) with
  `adrNumber`, `adrStatus`, `supersedes` and `restsOn` (to `factory:Principle`),
  and `factory-shapes.ttl` gains its shape. `design_record.py` parses ADRs into
  the graph. `render.py` writes a third index into `DESIGN.md`, "ADRs — an
  index", with columns ADR, title, status and principles, located by a new anchor
  and header in `ontology/spans.py`. A currency test and its dropped-row mutant
  follow the appendix index's pattern.
- **`tests/test_citations.py`.** Every `ADR <n>` resolves to a record. `ADR-NNNN`
  is not read as a citation. `test_saffron_keeps_no_adrs` is replaced by one that
  asserts every file under `docs/adr/` loads as an ADR record.
- **Protection and prose.** `docs/adr/**` joins `protected` in
  `.saffron/policy.yaml` and the `prose` gate's `INCLUDED_DIRS`.

## ADR 1

`docs/adr/0001-decisions-are-recorded-one-per-file-as-adrs.md`, with
`appendices: [P, U]`.

- **Context.** Appendix P refused ADRs three times, and `CONTEXT.md` §11 gave the
  reason: a parallel tree is a second address space. Appendix U found that the
  reason covered only a parallel tree and moved the appendices into records. U
  still said "ADR" means prior art's records, and nothing held one decision's
  current state.
- **Decision.** Saffron records each decision as one ADR under `docs/adr/`, cited
  as "ADR N". An appendix records what a revision found. An ADR records one
  decision as it stands today and cites the appendices that argued it. Prior
  art's records keep the `ADR-NNNN` form.
- **Principles.** 62 upholds. Whatever else `adr-reviewer` finds is added before
  merge.
- **Consequences.** The surfaces below change. The last sentence of U's "What did
  not change" paragraph is superseded in substance, and this ADR's Context says so.

## Surfaces that say otherwise

- `CONTEXT.md` §11: the **ADR** entry is rewritten to define Saffron's ADR (one
  decision per file, "ADR N", supersession, the principle rule) and prior art's
  `ADR-NNNN`. Naming decision 4 gains a sentence citing ADR 1. The spike
  verdict's _Avoid_ entry for "ADR" stays, because a spike verdict is not an ADR.
- `docs/agents/domain.md`: drop "creating one would be a defect", and add
  `docs/adr/` to the file tree.
- `CLAUDE.md`: the last line's "(no ADRs, `CONTEXT.md` §11)" names `docs/adr/`
  instead.
- `DESIGN.md` §10's repository layout gains `docs/adr/`.
- Backlog item b-9ff0fd closes in the same pull request.

## Delivery

By hand, because `CONTEXT.md`, `DESIGN.md` and `.saffron/**` are `protected`. The
third layer of stack #357, branch `joel/adrs`, on `joel/appendices-move`. Commits
land in dependency order:

1. The kind, its checks, and the CLI, tested on a fixture.
2. The ontology terms, the readers, the index, and the citation reader.
3. `adr-reviewer`.
4. ADR 1 and the surfaces, then `adr-reviewer` run on the pull request, with its
   findings resolved before merge.

ADR 1 is written after the `prose` scope widens to `docs/adr/`, so the hook
compares it against zero, as Appendix U was.
