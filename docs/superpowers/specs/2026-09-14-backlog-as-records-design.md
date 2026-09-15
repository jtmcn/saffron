# The backlog as records

Written 2026-09-14. The first of three related moves, and the one that sets the
pattern the other two follow: `docs/BACKLOG.md` — 6,858 lines, 403 KB, 122 items —
becomes one file per item with typed frontmatter, a loader and query command over
the directory, and integrity tests that hold what an item claims against what
the specs and code say. Specs join as a second record kind soon after
(`saffron/intake.py` already parses them into the same shape); the ledger and
batch tree moving into a git store shared between hosts is a separate design
with its own hard problem, and is not this one.

## The problem, measured

Two readers, one corpus. A Claude Code session reads through `Read`/`Grep` and
pays per token; to answer "what does item 118 say is left" it reads a 400 KB
file or greps for a heading and guesses a line range. A human on GitHub gets a
page the browser struggles to scroll. Neither can answer "what is open in tier
1" without reading the hand-sorted index at the top *and* trusting it — and
the index has drifted from the items before (its own header line admitted it,
2026-09-04).

What the file already has is more structure than it looks: items are numbered
in filing order and the numbers are an API — 27 comments under `saffron/` cite
`backlog item 33`, and every spec's `## Context` opens by naming
the item it came from. What it lacks is any field a program can read. Only 24
of 122 items carry a `**Status:**` line, and "done" is spelled eighteen ways
across them (`done, in <sha>`, `done, by hand, on <branch>`, `merged, via
SA-0085 PR #250`, `the runtime half is done`, `partly met`). Filed dates
appear on three.

The three questions this has to make cheap:

- **Retrieval** — item 118, and only item 118, in one read.
- **Comprehension** — the open tier-1 set on one screen; for one item, what is
  owed and what shipped, without reading the narrative that explains why.
- **Integrity** — an item that says `done` names what closed it, and the thing
  it names agrees.

## Approach

Files with YAML frontmatter and a Markdown body, exactly the shape
`.saffron/specs/` already has, so an agent that can write a spec can write an
item. A small dev-only package loads a directory of such files into pydantic
models and answers queries from the command line. Validation is pytest against
the live directory, the way `tests/test_citations.py` runs against the live
`DESIGN.md`.

Two alternatives were considered and set aside, with the reasons recorded so
they are not re-argued from scratch:

- **Lift the records into the ontology graph** (`ontology/design_record.py`
  already lifts principles and revision appendices out of `DESIGN.md`; SHACL
  would validate links, SPARQL would answer cross-record queries). A graph
  earns its weight when a question traverses records of different kinds joined
  by shared ids — item → spec → task → PR. With backlog items as the only new
  kind, every question is a filter on one record type plus a lookup, which a
  list of dicts answers as well. This is the right follow-on when specs are a
  kind; the record format below is chosen so the lift is mechanical (every
  field a scalar or a list of ids), and the graph libraries stay test-only.
- **A tabular store (CSV, DuckDB) with Markdown rendered from it.** Prose in
  cells diffs badly and reads worse, the dependency buys nothing over
  `yaml.safe_load` at 122 rows, and it is the wrong shape for a store a git
  merge has to reason about — which the ledger design will need.

## The record

### Location

`docs/backlog/` replaces `docs/BACKLOG.md`. One item per file:

```
docs/backlog/118-the-verdict-of-record-is-computed-in-the-implementers-container.md
```

Three-digit zero-padded id, then a slug cut from the title the way spec
filenames are. Two hand-written files sit beside the items:

- `docs/backlog/README.md` — today's preamble (filing order, the numbers are an
  API, where the evidence lives) and today's closing section, "What is *not*
  here, deliberately".
- `docs/backlog/PRIORITY.md` — today's "Priority — the order to work in", prose
  unchanged. It stays hand-sorted because the sort is an argument, not a
  function of the fields; what changes is that a test now holds it to the
  records (below).

### Frontmatter

Every field is a scalar or a list of ids. Nothing lives only in Markdown.

```yaml
---
id: 118
title: The verdict of record is computed inside the container the implementer controlled
status: done            # open | partial | done | superseded | wontfix
tier: 1                 # 0..3, or null when PRIORITY.md does not place it
filed: 2026-09-13       # optional; most existing items never recorded one
closed: 2026-09-14      # required for done | superseded | wontfix
by_hand: true           # cannot go through a cell — the tracker doc's own term
specs: [SA-0086, SA-0087, SA-0088]
prs: [255]
commits: [57b676c]      # a by-hand close with no pull request
cites: ["§5.4", "§5.5.1"]
related: [69, 117]
superseded_by: null     # required, and an item id, when status is superseded
---
```

`partial` is the honest value for "the runtime half is done": some of what the
item asked for shipped, and the body says which half. Unknown keys are refused,
not ignored, as `intake.py` does for a spec.

There is no `evidence:` field. `docs/evidence/` files are cited by path in
prose today; the field is added when it has a validator, not before.

### Body

Three headings, fixed, in this order — the spec body's convention applied here:

- `## Problem` — what the item says today above its "Done looks like".
- `## Done looks like` — verbatim where it exists. Required for `open` and
  `partial`; for `partial` it names what is still owed.
- `## Record` — the dated paragraphs ("Done, 2026-08-23.", "Stale by the
  evening it was written…"), chronological, newest last. For `partial` at
  least one dated entry, saying what shipped. The narrative goes here so
  `## Problem` stays readable.

Cross-references in prose (`item 33`, `SA-0087`, `§5.4`) stay as written. The
frontmatter lists are the *declared* links; prose mentions are not.

### Citation form

`docs/BACKLOG.md item **118**` is how a spec's `## Context`, a code comment and
`DESIGN.md` cite an item today, and the path is about to be wrong. The canonical
form becomes **`backlog item 118`** — path-free, since the path is the kind's
directory and may move again. Where a path is wanted, it is the file's:
`docs/backlog/118-….md`. The integrity test accepts `backlog item N`, `BACKLOG
item N` and `item N` alike and checks only that `N` exists; the *form* is
convention, not a gate.

## The loader and the command

### Package

`records/`, top-level and dev-only beside `ontology/` and `harness/`. Nothing
under `saffron/` imports it: this is Saffron's own project management, and
§2.1's boundary says Saffron knows nothing about a target repo's documents.
It does not import `saffron/` either, until specs join as a kind and it takes
`saffron.intake.Spec` as that kind's model.

- `records/kinds.py` — a `Kind` is a directory, a filename pattern, and the
  pydantic model for its frontmatter. `BacklogItem` is the first model. The
  status set, the tier range and the required-when rules (`closed` on a
  closed item, `superseded_by` on a superseded one) live on the model, so a
  file that breaks one is refused at load with the file and field named.
- `records/load.py` — `load(kind) -> list[Record]`; a `Record` is the parsed
  model plus the body split at its `## ` headings. The directory is read on
  every call. There is no index file, so there is nothing to go stale.
- `records/__main__.py` — the command.

### Command

`uv run python -m records …`, with `make backlog` for the bare listing.

```
records list backlog                          # id  status  tier  title — one line each
records list backlog --status open --tier 1   # any frontmatter field is a filter
records show 118                              # frontmatter and body, nothing else
records show 118 --section "Done looks like"  # one section
records show SA-0087                          # not a kind yet: the items whose specs: name it
records grep witness                          # id, title, matching line — across bodies
```

`show` is the retrieval fix: one read of about sixty lines. `list` is the
comprehension fix: the open tier-1 set on one screen. Output is plain text, one
record per line for `list`, so it composes with `grep` and reads cleanly in a
tool result.

Not a `saffron` subcommand, not a server, not a cache. If the ledger design
later wants this loader for task records, it moves into `saffron/` then, with
that argument made then.

## Validation

Pytest under `tests/records/`, run by `make check` and so by the `tests` gate —
nothing new in the gate set. The loader tests use a fixture directory; the
integrity tests run against the live `docs/backlog/`, `.saffron/specs/` and
`DESIGN.md`. Every failure names the file and the field.

### Record integrity

- Ids unique and contiguous `1..N`; the filename prefix equals `id`.
- Every `specs:` id resolves to a file in `.saffron/specs/` or
  `.saffron/specs/done/`.
- Every `cites:` resolves to a heading in `DESIGN.md`, through
  `tests/test_citations.py`'s existing parser, not a second copy of it.
- Every `related:` and `superseded_by:` resolves to an item; a
  `superseded_by` target is not itself `superseded`.
- Every `item N` citation in `saffron/`, `tests/`, `.saffron/specs/` (open and
  done) and `DESIGN.md` names an existing item. Not `docs/evidence/`: those are
  dated primary records, true on their date, and holding them to today's
  numbering would mean editing history or scrubbing it.

### Workflow

- `done`, `superseded`, `wontfix` ⇒ `closed` is set **and** at least one of
  `specs`, `prs`, `commits` is non-empty. A close names what closed it.
- `open`, `partial` ⇒ `## Done looks like` present and non-empty. `partial` ⇒
  at least one dated `## Record` entry as well.
- `done` ⇒ every spec in `specs:` is in `done/`. An item cannot claim closure by
  a spec still in the queue.
- The inverse: a spec whose `## Context` cites `item N` is listed in item N's
  `specs:`; and if that spec is in `done/`, item N is not `open`. Adding a spec
  is already a by-hand commit that updates the scheduler smoke test
  (`docs/agents/issue-tracker.md`); touching the item in the same commit is
  the same convention, not a new one.
- `PRIORITY.md` agrees with the records: every `**N**` it names exists; every
  `~~**N**~~` is `done` or `superseded`; every item with a `tier` is named
  under that tier's heading. The rule runs from the records to the index and
  not the other way, because the index's prose names ids under other tiers'
  headings when it narrates a move ("**80** moved to tier 1" sits under tier
  3). The index can no longer drift from the items without a test saying so.
- No live surface names the path `docs/BACKLOG.md`: `saffron/`, `tests/`,
  `.saffron/specs/` (open only), `CLAUDE.md`, `DESIGN.md`, `README.md`,
  `docs/agents/`. Done specs and evidence are history and are exempt.

### Not checked, deliberately

Whether a `prs:` entry is merged. That needs `gh`; it is `reconcile`'s job
and belongs to the ledger design.

### Cells

`docs/**` is `forbidden` in every current spec, so a cell cannot edit an item —
correctly, since closing one is the operator's assertion at ratification. The
only inputs to these tests a cell *can* edit are `item N` citations in
`saffron/` and `tests/`, and citing an item that does not exist is exactly
what should fail its `tests` gate.

## Migration

122 items, and the fields come out of prose. Three passes; the migration is
done when `make check` is green with the integrity tests pointed at the live
directory.

**Pass 1 — mechanical split.** A throwaway script splits `docs/BACKLOG.md` on
`^## N\. ` into 122 files: `id` and `title` from the heading, the whole body
under `## Problem`, `status: open`, `tier: null`. The preamble and the closing
section become `README.md`; the "Priority" section becomes `PRIORITY.md`.
Exact and reversible.

**Pass 2 — mechanical extraction, where a regex is trustworthy.**

- `tier`, and a first `status`, from `PRIORITY.md`: `**N**` under a tier
  heading gives the tier; `~~**N**~~` marks it done.
- `status` refined from the 24 `**Status:**` lines and 15 `**Done, 20xx-…**`
  paragraphs — ground truth where present.
- `cites` from `§\d+(\.\d+)*` — a mention *is* a citation.
- `specs`, `prs`, `commits`, `related` as **candidates only**, from `SA-\d{4}`,
  `PR #\d+` / `pull request #\d+`, seven hex characters in backticks, and
  `item \d+`. A mention is not a link: "not the same defect as item 13" is not
  `related`, and "lens #3" is not a pull request.

**Pass 3 — one agent per item, in parallel batches, on a narrow brief.** Split
the body into `Problem` / `Done looks like` / `Record` at the boundaries the
prose already has; confirm or prune each candidate link by reading the sentence
it sits in; set `closed` from the dated paragraph; choose `status`. The brief
forbids rewording — moves and frontmatter only, so a reviewer of the diff can
see nothing was lost. An item the agent cannot classify with confidence stays
`open` with a line in its report; the expected residue is ten to twenty items
for the operator's judgement, not 122.

**Afterwards.** `docs/BACKLOG.md` is deleted, not stubbed. Live surfaces that
name the path move to the new citation form: 17 modules under `saffron/`, 15
test files, every open spec's `## Context`, `DESIGN.md` (eight mentions),
`README.md`, `CLAUDE.md` (which also gains the command), `docs/agents/`. Done
specs and `docs/evidence/` are left as written. The 27 `item N` comments need
nothing. Per-file `git log --follow` will not reach into the old monolith; the
item's `## Record` carries its own dates and the old file stays in history.

## Delivery

A two-pull-request stack with `gh stack`, so the tooling is reviewable without
the 122-file diff:

1. **`records/`** — package, command, loader tests on a fixture directory,
   integrity tests written and pointed at the fixture. `make backlog` target.
2. **The migration** — split, extraction, agent pass, `README.md`,
   `PRIORITY.md`, the citation-form sweep, `CLAUDE.md`; integrity tests now
   pointed at the live directory. Ninety-five percent moves.

## Follow-ons, and what this design does for them

- **Specs as a kind.** `records/kinds.py` registers `.saffron/specs/` with
  `saffron.intake.Spec`; `records show SA-0087` stops being a reverse lookup.
  The item ↔ spec tests above become one join.
- **The graph lift.** With two kinds sharing ids, a loader lifts frontmatter
  into `ontology/design_record.py`'s graph and cross-kind questions get SPARQL.
  Nothing in the record format needs to change for that; that is why every
  field is a scalar or a list of ids.
- **Appendices as decision records.** `CONTEXT.md` §11 and `CLAUDE.md` say
  decisions are principles and appendices, never ADRs. Splitting `DESIGN.md`'s
  appendices out would overturn that and is a vocabulary decision to record
  when it is made. What this design gives it is a kind to slot into.
- **The ledger in git.** Wants records a merge can reason about, across two
  hosts. This is the shape; the concurrency question — two hosts picking one
  spec — is its own design.
