---
id: b-e0bbbf
title: Merge-time hand edits that `SA-0107` and `SA-0108` hand to the operator
status: done
closed: 2026-09-22
tier: 3
filed: 2026-09-19
by_hand: true
specs: [SA-0107, SA-0108]
prs: [355, 366]
commits: []
cites: []
related: [b-d6bff7, b-606ea3, b-946f03]
---

## Problem

Found in the spec loop's run 8, 2026-09-19. Both specs name edits that their
`forbidden` lists put out of a cell's reach. Nothing tracks them past the merge.

From `SA-0107` (#355), whose `saffron/projection.py` imports `rdflib`:

- Four sentences say nothing under `saffron/` imports a graph library:
  `pyproject.toml:21-22`, `ontology/render.py:3-4`,
  `ontology/design_record.py:16-17` and
  `tests/ontology/test_vocabulary_agrees_with_code.py:21-22`.
- pyoxigraph, pyshacl and rdflib sit in the `dev` group
  (`pyproject.toml:35-37`). The move needs `uv lock`, and `uv.lock` is
  `protected`.

From `SA-0108` (#366): `CLAUDE.md`'s *Running the CLI* block needs
`saffron chains`.

`SA-0106`'s edits to `DESIGN.md` are item b-d6bff7's, which names each line.

## Done looks like

Once #355 and #366 merge: the four sentences say what imports the graph
libraries, the three packages move out of `dev` with `uv.lock` regenerated, and
`CLAUDE.md` lists `saffron chains`.

## Record

- 2026-09-19: filed from the spec loop's run 8 (stack #351 ← #360 ← #355 ←
  #366 ← #353).
- 2026-09-22: Done by hand. `rdflib`, `pyshacl` and `pyoxigraph` move to
  `dependencies`, with `uv.lock` regenerated. None of the four sentences
  denies that `saffron/` imports them any more. The comment at `saffron/cli.py:1009`
  gives the deferred import's real reason, and `CLAUDE.md` lists
  `saffron chains`. The ontology ADR's draft found
  the move missing.
