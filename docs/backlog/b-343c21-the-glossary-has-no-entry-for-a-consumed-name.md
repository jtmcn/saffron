---
id: b-343c21
title: The glossary has no entry for a consumed name, and SA-0134 and SA-0135 use the term
status: open
tier: 2
by_hand: true
filed: 2026-09-22
specs: [SA-0134]
prs: []
commits: []
cites: [§3.2, §4.2]
related: [b-602d00, 65, 72]
---

## Problem

Found 2026-09-22, writing `SA-0134`.

`SA-0134` adds a reader that says whether a tree base holds a path or a
name. `SA-0135` stacks on it and adds the `consumes:` spec field. A child
lists there what it uses from its `depends_on[0]`, and the host refuses the
task before its cell when an entry does not resolve.

`CONTEXT.md` has no entry for a consumed name or for the field. Its
**Refusal** entry lists what is refused before a cell starts, and this is
not among them. `CONTEXT.md` is generated from `ontology/factory.ttl`, and
both are forbidden to the two cells, so neither can add the entry.

## Done looks like

A **Consumed name** entry in `ontology/factory.ttl`, rendered into
`CONTEXT.md` by `uv run python -m ontology.render`. It says an entry is a
repo-relative path or `path:name`, resolved at the task's tree base. An
unresolved one refuses the task before its cell starts, and the
**Refusal** entry names it. This lands after `SA-0135` merges.

## Record

- 2026-09-22: filed with `SA-0134`.
