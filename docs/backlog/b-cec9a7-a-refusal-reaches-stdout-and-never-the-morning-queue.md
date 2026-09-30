---
id: b-cec9a7
title: A refusal reaches stdout and never the morning queue, though §4.2 and the glossary say it lands there as one line
status: open
tier: 3
filed: 2026-09-29
specs: []
prs: []
commits: []
cites: [§4.2, §6]
related: [52]
---

## Problem

Found in item 52's review, 2026-09-29. Item 52 said this was filed separately,
and no record held it.

`DESIGN.md` §4.2's gate 0 says a refusal lands in the morning queue as one line.
`CONTEXT.md`'s **Refusal** entry says a scan's refusal reaches the queue as one
line. `saffron queue` and `saffron batch` print refusals to stdout
(`saffron/cli.py`). Nothing writes a queue row for one, and `index.html` never
shows it.

`report/index.py`'s `RowState` has no member for a refusal. A `REFUSED` row state
chosen before anything writes one is how `SKIPPED` came to have no producer.

## Done looks like

One of two outcomes. A refusal writes one row to the morning queue, with a
`RowState` member and a rank. Or §4.2 and the **Refusal** entry say that
refusals reach stdout only.
The exhaustiveness test in `tests/test_report.py` forces the rank once a row
state exists.

## Record

- 2026-09-29: filed from item 52's review.
