---
id: b-43061c
title: The `prose` gate reads no text inside a string literal, so an SQL comment or a prompt string escapes every word rule
status: open
tier: 2
filed: 2026-09-26
specs: []
prs: []
commits: []
cites: [§8]
related: [b-044ae7, b-440f17]
---

## Problem

Found in the spec loop's run 18, 2026-09-26.

`prose` reads Python comments and docstrings. Text inside a string literal is
neither, so no rule reaches it. Three pull requests in one run shipped text
through that gap, and review caught each by hand:

- #525 (`SA-0145`) put a five-line comment inside `ledger.py`'s `SCHEMA` string.
- #530 (`SA-0159`) put a two-line comment there whose both clauses were false.
- #526 and #528 built prompt headings with an em dash in an f-string, and the
  em dash reached the filled prompt.

## Done looks like

- `prose` holds each `--` line in `SCHEMA` to its comment rules. Or `SCHEMA`
  moves to a `.sql` file the gate reads.
- A string a prompt is built from is held to the Markdown rules, or the choice
  not to is written down.

## Record

- 2026-09-26: filed from the spec loop's run 18 (stack #531).
