# The appendices as records

Written 2026-09-18. The backlog design named this as a follow-on
(`2026-09-14-backlog-as-records-design.md`, "Appendices as decision records") and
left it as a vocabulary decision to record when it was made. This is that
decision. `DESIGN.md`'s twenty appendices, A to T, become one file each under
`records/`'s second kind, `appendix`. They keep their letters, so no citation
moves. The move is the first step toward recording decisions as their own
records, and it is written down as that intent in a new appendix, U.

## The problem, measured

`DESIGN.md` is 3,057 lines. Lines 1,658 to the end are the appendices, so more
than 45% of the file is revision narrative that no reader wants whole.

The appendices record decisions as a timeline, not one record per decision. Each
is "what rev N found". Finding where one decision stands today means reading
several. The emitter is the plain case: `ontology/RATIONALE.md` closed it,
Appendix O reopened the question around it, Appendix P deferred it, and Appendix
T reopened it. `DESIGN.md` mentions it about twenty times.

Nothing marks a decision as replaced. Appendix P still says the emitter is
"Deferred" (`DESIGN.md:2792`), and no field or test connects that sentence to
Appendix T.

Three sessions asked whether the appendices should be ADRs, and the answer
stayed no (`DESIGN.md:2748`). `CONTEXT.md:641` gives the reason: a `docs/adr/`
tree would be a second address space for what §-numbers already address, and
the first two records to disagree would do it undetectably. That reason holds
against a *parallel* tree. It does not hold against moving the appendices
themselves into records, which is one address space with the same letters.

What records give that prose in one file does not, measured by the backlog
move: a record per file, typed frontmatter, and integrity tests that run under
`make check`. `records/kinds.py:137` already has a `KINDS` registry built for
more than one kind.

## Approach

Move each appendix, verbatim, into `docs/appendices/<letter>-<slug>.md`, and
register `appendix` as a second kind. Letters are permanent ids. `DESIGN.md`
keeps §0 to §11 and both indexes, and both indexes render from the records.

Two alternatives were set aside:

- **Keep the appendices in `DESIGN.md` and add status and supersession to
  `factory:RevisionAppendix`.** It fixes the missing supersession link, but
  every check would be built inside the ontology parser, and the file stays
  3,057 lines. The records package already has the checks.
- **A `docs/adr/` tree for new decisions only.** This is the parallel address
  space `CONTEXT.md:641` refuses, and the refusal is right for it.

## The record

### Location

```
docs/appendices/P-the-vocabulary-covers-the-design-record.md
```

The letter, then a slug cut from the heading's title less any `rev N:`. The
`Kind.pattern` is `^([A-Z]{1,2})-[a-z0-9-]+\.md$`, with the capture group
`records/load.py:158` reads as the id. Two letters because U is the
twenty-first and Z is the twenty-sixth: six appendices remain in one letter.
After Z comes AA. Every reader of an appendix letter that survives the move
widens with the pattern, or a citation of AA is one nothing checks:

- `ontology/shapes/factory-shapes.ttl:282`, `sh:pattern "^[A-Z]$"`, which is
  hand-maintained.
- `tests/test_citations.py:95`, `_APPENDIX_CITATION`, which matches `[A-Z]\b`,
  and `:174`, which splits the matched run with `re.findall(r"[A-Z]", …)`.
  Widening `:95` alone would read AA as two citations of A and pass it.
- `records/load.py:166`, `order()`, which sorts string ids lexically, so `AA`
  would sort before `B`. The appendix kind sorts by length, then letter.

`ontology/design_record.py`'s `APPENDIX` (`:36`) and `_INDEX_ROW` (`:47`) have
no reader after the move: letters come from record ids and revisions from
frontmatter. They are deleted, not widened. `APPENDIX_OPENS` (`:40`) stays, for
the guard under Validation.

### Frontmatter

```yaml
---
id: P
title: "rev 20: the vocabulary covers the design record"
revisions: [20]
question: >-
  Should the appendices have been ADRs? No — and the phrase that kept the
  question alive was a summary of two verdicts that nobody decided
---
```

- `title` is the heading after its em dash, verbatim. The headings are not
  uniform (`Appendix A — What changed in rev 2, and why`), so it is not parsed
  further.
- `revisions` is the appendix index's `Rev` column (`DESIGN.md:1539`). It keeps
  a second reading to agree with: the `rev N` in `title`. The check at
  `ontology/design_record.py:92`, which compares a heading's rev with its index
  row, becomes a check that the title's rev appears in `revisions`, and
  `tests/ontology/test_design_record.py:174` is re-aimed at it.
- `question` is the index's third column, and it stays navigation. The index
  calls itself "navigation, not authority" (`DESIGN.md:1536`), and principle 57
  says a summary is lossy toward the general. Moving it into frontmatter does
  not promote it: the body is the record, and where `question` disagrees with
  the body, the body is right.

There is no `status` and no `superseded_by`. An appendix is a permanent record
of what a revision found, and it is never replaced. Supersession belongs to the
decision records that come later. `Identified.status` (`records/kinds.py:57`)
moves onto `BacklogItem`. Its readers outside `BacklogItem`'s own validators
are `records/check.py:115`, `:248`, `:282`, `:311` and `:316`, and
`records/load.py:131`, all on backlog records, so each narrows to
`BacklogItem`. `tests/records/test_records_check.py:292` and `:299` build
`Identified(..., status="open")` and change with it.

`records/__main__.py` changes in two places. Only `list` takes a kind
(`choices=sorted(KINDS)`, `:119`), and `cmd_list` narrows every record through
`_item` (`:55`), which raises "not a backlog item" (`:30`). So `records list
appendix` would exit 2 on its first record. `list` gains a line format per
kind. `show` (`:65`) loads only the backlog, and an id that is neither a number
nor a random id falls to the spec-id lookup (`:82`), so `records show P` prints
"no backlog item names P". `show` resolves a letter against the appendix kind
first. `grep` (`:99`) and `new-id` (`:110`) stay backlog-only.

Principles are not declared in frontmatter. They stay numbered lines in the
body, and `design_record.py` keeps reading them there, so a principle is
written once.

### Body

The appendix's prose, verbatim, without its `## Appendix <letter> —` heading. The
appendices use `###` subheadings (49 of them) and no `##`, so the body has no
`## ` sections.

Four loader rules are backlog rules that run on every kind today, and all four
move onto `Kind`:

- the refusal of prose before the first `## ` heading (`records/load.py:105`),
  which would refuse every appendix body whole;
- `REQUIRED_SECTIONS` (`:23`) and the unknown-section check (`:109`);
- the section order check (`:114`);
- `_check_sections` (`:126`), which requires `## Problem` and reads `status`.

`appendix` declares none of them. The backlog design planned this move for when
specs join as a kind (its lines 297–298). It happens here instead.

## What reads the records

- **`ontology/design_record.py`** parses principles and appendices from the
  records instead of from `DESIGN.md`. `render_principles` still writes the
  principle index into `DESIGN.md`, and the direction is unchanged: the
  appendices are authoritative and the index is their render. Its module
  docstring ("parsed from `DESIGN.md`") and `ontology/render.py:200`'s comment
  ("`DESIGN.md` renders from itself") change with it.
- **The appendix index** (`DESIGN.md:1533`) becomes a render too, from `id`,
  `revisions`, `question` and the principle numbers. That needs its own span:
  an anchor and locator in `ontology/spans.py` beside `PRINCIPLE_ANCHOR`
  (`:27`) and `principle_index` (`:48`), a call in `ontology/render.py` beside
  the principle render (`:204`), and tests in `tests/ontology/test_spans.py`.
  `tests/test_citations.py:341`'s test that the index lists every appendix is
  replaced by a currency test like the principle index's
  (`tests/ontology/test_design_record.py:86`). An appendix with no principle
  renders an empty cell.
- **`.saffron/gates/prose.py:314`**, `_rendered`, exempts the principle index
  in `DESIGN.md`, because each claim is checked where it is written, in its
  appendix body. It does **not** exempt the appendix index. The gate strips
  frontmatter, so the rendered row is the only copy of `question` any rule
  reads, and principle 59 says no file can gain hits of any rule. A new
  `question` that breaks a rule fails the `DESIGN.md` hook, and the fix is made
  in the record's frontmatter. `prose.py` therefore needs no change for the
  appendix index.
- **`tests/test_citations.py`** takes `APPENDICES` from the records directory,
  not from `APPENDIX` over `DESIGN.md` (`:36`, `:179`). Every appendix
  citation still has to resolve.
- **`records/check.py`** scans `DESIGN.md` for `item N` citations (`CITING`,
  `:18`) and for the old backlog path (`LIVE_SURFACES`, `:228`). Twenty lines
  in the appendix range cite an item, among them Appendix N's "backlog items 11
  and 12". Both tuples gain `docs/appendices`.

## Validation

In `tests/records/`, against the live directory, beside the backlog's:

- Ids unique, the filename prefix equals `id`, and the letters run
  contiguously from A to the last one, in the kind's own order.
- Every appendix citation resolves, as above.

`tests/ontology/test_design_record.py` holds the principles to one global
sequence, a contiguous block per appendix, and every appendix reached. Those
properties stay. The tests do not run unchanged, and each rewrite is named:

- `_graph()` (`:26`) parses the records, not `DESIGN.md`.
- `test_the_index_reaches_every_appendix` (`:112`) takes its letters from
  record ids, not from `APPENDIX` over `DESIGN.md` (`:121`).
- Four mutant tests replace text that leaves `DESIGN.md`: the Appendix P
  heading (`:148`), the Appendix G heading (`:162`), Appendix G's index row
  (`:180`) and principle 57's claim (`:190`). Each moves onto the record text
  it names. `test_a_heading_it_cannot_read_is_refused` (`:138`) tests a heading
  the parser no longer reads, and is replaced by the guard below.
- **No appendix heading in `DESIGN.md`.** After the move, an appendix written
  into `DESIGN.md` the old way is read by nothing: its principles never reach
  the index, and the contiguity and currency tests stay green. A test asserts
  no line of `DESIGN.md` matches `APPENDIX_OPENS` (`design_record.py:40`), and
  is run against a mutant that adds one.
- `CONTRIBUTES_NO_PRINCIPLE` (`:109`) gains `"U"` if U contributes no
  principle.

## Protection

`.saffron/policy.yaml:57` protects `DESIGN.md`, `CONTEXT.md` and `.saffron/**`.
Moving the appendices out of `DESIGN.md` would take the authoritative design
record out of `protected`, so the move adds `docs/appendices/**`. Without it, a
cell that edited a principle line would also be trapped: the principle index's
currency test would then need a `DESIGN.md` re-render the cell cannot write.

## Migration

**Pass 1, mechanical.** A throwaway script splits `DESIGN.md` from line 1,658
on `^## Appendix ([A-Z]) — (.*)$`. `id` and `title` come from the heading, and
`revisions` and `question` from the index row with the same letter. The body is
everything up to the next heading, including its trailing `---` rule and
Appendix D's closing paragraph after its rule (`DESIGN.md:1732`). Done when the
twenty bodies, rejoined with their headings, are byte-identical to the removed
range.

**Prose scope, in its own commit.** `.saffron/gates/prose.py:35` covers
`DESIGN.md` as a root file, and `INCLUDED_DIRS` (`:36`) does not include
`docs/appendices/`. `hooks/prose_limit.py` compares a new file against zero
hits (`:5`), so adding the directory in the same commit as the move would fail
the hook on text that moved and did not change. The move commits first. The
hook loads the gate from the working tree (`:24`), so the `INCLUDED_DIRS` edit
is not made until the move has committed. The scope change then commits with
no appendix file staged, and the moved prose is the baseline.

**No commit that removes prose hits from `DESIGN.md` carries a prose edit to
it.** The hook counts hits per rule (`hooks/prose_limit.py:85`), so a commit
that removes hundreds, as the move does, would hide any new ones added in the
same file. The move commit is a pure move. The appendix index render reproduces
the committed rows byte for byte when it first lands, so it removes and adds
nothing. Every `DESIGN.md` prose edit, including U's status line and pass 3,
is in a later commit of its own.

**Pass 2, appendix U, after the scope commit.** Principle 59 says no file can
gain hits of any rule, and U is new prose, not moved prose. Written before the
scope commit, it would become baseline unchecked. Written after, the hook
compares it against zero like any new file.

U is written by hand as `rev 25`. It records three things: that `CONTEXT.md`
§11's refusal of ADRs is narrowed to a parallel tree and does not reach this
move; that naming decision 4 in `CONTEXT.md` is amended; and the intent to
record decisions as their own records and migrate them out of the appendices.
It contributes a principle only if writing it finds one. `DESIGN.md`'s status
line gains rev 25.

**Pass 3, the surfaces that say otherwise.**

- `CONTEXT.md` §11: **Revision appendix** is a record under `docs/appendices/`,
  and the **ADR** entry keeps its point about prior art's `ADR-NNNN` but drops
  "Saffron keeps no ADRs" for what U says. Naming decision 4 gains the
  reversal.
- `DESIGN.md:1536`: the appendix index is rendered, so "where it disagrees with
  an appendix, the appendix is right" becomes a statement about `question`
  alone.
- `DESIGN.md:1582`: "rewrites it from the appendices below". They are no
  longer below.
- `DESIGN.md`'s §10 tree (`:1424`) gains `docs/appendices/`.
- `DESIGN.md:1571`'s paragraph on why an appendix is coarse stays. It states
  the constraint the decision kind has to meet.
- `docs/agents/domain.md:8` ("the appendices that carry the design record"),
  `:11` (the refusal of `docs/adr/`), and its tree at `:18`.
- `CLAUDE.md:15`–`17`, on where a new principle is written.
- `tests/test_citations.py:232`, "only `DESIGN.md` has appendices", and the
  module docstring at `:23`, written "while deciding *against* splitting
  `DESIGN.md` into per-decision files".
- `tests/test_citations.py:298`, `test_saffron_keeps_no_adrs`, which holds
  `CONTEXT.md` §11's refusal and changes with it.
- `records/kinds.py:3` ("never prose", which `question` now is),
  `records/kinds.py:52` ("an id the filename repeats, and a status"), and
  `records/check.py:50` ("the only registered kind today").
- **The `DESIGN.md` qualifier.** Twenty lines outside `docs/evidence/`, done
  specs and design docs cite "`DESIGN.md` Appendix <letter>" or "`DESIGN.md` §N,
  Appendix <letter>", among them `CONTEXT.md:67`, `saffron/cell/runtime.py:1` and
  `saffron/gates/contract.py:68`. The letter still resolves, and the file named
  is wrong. They are swept to the bare "Appendix <letter>" form, as the backlog move
  swept `docs/BACKLOG.md` paths. Found with
  `grep -rnE "DESIGN\.md\`? (§[0-9.]+, )?Appendi"`.

## Delivery

A two-pull-request stack with `gh stack`, as the backlog was:

1. **`records/`**: the `appendix` kind, the four loader rules onto `Kind`,
   `status` onto `BacklogItem` and its readers narrowed, the per-kind order,
   `records/__main__.py`'s `list` and `show`, loader tests on a fixture
   directory.
2. **The move**: pass 1, the prose scope commit, pass 2, pass 3, the readers
   switched to the records, the appendix index render, `protected`, and the
   backlog item below.

Both are by hand. `DESIGN.md`, `CONTEXT.md` and `.saffron/**` are `protected`
(`.saffron/policy.yaml:57`), so no cell can run this.

## Follow-on, filed with the move

A `by_hand: true` backlog item for a kind that records one decision per file.
What it has to answer, stated now so it is not rediscovered:

- **Numbering.** Principles are one sequence that each appendix claims a block
  of when it is written, which is why per-decision documents written in
  parallel were refused (`DESIGN.md:1571`). The backlog met the same problem
  with random ids after item 177 (`records/kinds.py:34`), and that answer is
  the one to try first.
- **Supersession.** `BacklogItem.superseded_by` holds one id. A decision split
  into several, or replaced by several, needs a list.
- **The name.** "ADR" is on `CONTEXT.md`'s _Avoid_ list because every
  `ADR-NNNN` in `DESIGN.md` cites prior art. "Decision record" collides too:
  `CONTEXT.md:639` uses it for prior art's records, and §11's own title is
  "Design record". The name is chosen when the kind is designed, and it goes
  into `ontology/factory.ttl` then.
- **The first record.** The reversal U records, migrated out of U. It is short,
  self-contained and states its own reason, so it tests the kind and the
  migration path on the smallest case.
