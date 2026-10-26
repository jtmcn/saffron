---
id: b-2227b0
title: "Moving whole `CONTEXT.md` entries into the graph is parked, after three reviews found no delta over a loader"
status: wontfix
tier: 3
filed: 2026-10-24
closed: 2026-10-24
specs: []
prs: [963]
commits: []
cites: [§4.6]
related: [b-c16c6c, b-545741, b-8e14fb]
---

## Problem

A draft ADR kept each term's whole entry in `ontology/factory.ttl` as SKOS
annotations and rendered `CONTEXT.md` from it. The label was `rdfs:label`, and
the definition `skos:definition`. The rest became one `skos:scopeNote`.
Banned phrases became `skos:hiddenLabel`. A view query and a term page in
`saffron serve` were its reader. Three `adr-reviewer` rounds left it not
mergeable.

- §4.6 rule 2b says a vocabulary valued only by agents stays a glossary.
  Appendix O calls a graph stretched over `CONTEXT.md` a re-encoded glossary.
- A cross-check test closes every measured gap (b-c16c6c). Of the 166 commits
  at base that touched either file, 138 touched `CONTEXT.md` alone, so the move
  made the common edit heavier.
- A loader in the pattern of `ontology/design_record.py` feeds the view the
  same definitions from Markdown. The view already reads spec text and failure
  lines from outside the graph.
- The move retires no parser of `CONTEXT.md`, and rendering in place adds one.
  Both defects recorded at base came from rendering in place: the unbounded
  sentence in `ontology/spans.py`'s `definition_sentence` comment, and the
  deleted prose in the docstring of `test_vocabulary_agrees_with_context.py`.

## Done looks like

Closed as parked. It reopens only on a measured case: an entry form that the
stated grammar plus a parse test cannot split, and that occurs in
`CONTEXT.md`. Until then the path is b-c16c6c, a loader if a view page wants
definitions, and b-545741.

## Record

- 2026-10-24: parked by the operator after the third review, and closed with
  the reopen condition above.
