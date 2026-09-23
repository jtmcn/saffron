---
id: b-0adc85
title: "`saffron chains` imports graph libraries only the dev group installs, and three files still say nothing under saffron/ imports one"
status: done
closed: 2026-09-22
tier: 3
filed: 2026-09-22
by_hand: true
specs: [SA-0107, SA-0108]
prs: [355, 366]
commits: []
cites: [§4.6]
related: [b-946f03, b-952c34]
---

## Problem

Found writing ADR 5, 2026-09-22.

`saffron/projection.py` imports `rdflib` and `pyshacl`, and
`saffron/chain_walk.py` imports `pyoxigraph`, inside the functions
`saffron chains` calls. All three sit in `pyproject.toml`'s `dev` group, not in
`dependencies`. So the command fails wherever the project is installed without
the dev group.

Appendix T named this cost. The emitter falsifies a sentence in three files, and
the operator moves the dependency at merge, because `uv.lock` is `protected`.
#355 and #366 merged, and the move did not happen. These still say nothing
under `saffron/` imports a graph library:

- `pyproject.toml`, the comment above the `dev` group.
- `ontology/render.py`, its module docstring.
- `ontology/design_record.py`, its module docstring.

## Done looks like

The three libraries `saffron chains` imports are runtime dependencies, with
`uv.lock` updated, and the three sentences say which `saffron/` modules import
them.

## Record

- 2026-09-22: filed from ADR 5. ADR 5's Consequences records it.
- 2026-09-22: Done by hand with b-e0bbbf, which tracked the same move and
  named a fourth sentence, in
  `tests/ontology/test_vocabulary_agrees_with_code.py`. Both close in #472.
