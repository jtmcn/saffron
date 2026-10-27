---
id: b-545741
title: "Two modules each decide where a `CONTEXT.md` first sentence ends, and only one stops at the blank line"
status: done
tier: 3
filed: 2026-10-24
closed: 2026-10-27
specs: [SA-0317]
prs: [979]
commits: []
cites: []
related: [b-c16c6c]
---

## Problem

`ontology/spans.py` `definition_sentence` bounds a first sentence at the
entry's blank line. Its comment records why: unbounded, a definition without a
trailing period matched a period paragraphs away.

`context_enumeration` in `tests/ontology/test_vocabulary_agrees_with_context.py`
splits on the first period with no blank-line bound. The test that checks the
render reads the closed sets by a different rule from the one the render
writes by.

## Done looks like

The test imports `definition_sentence` and keeps no rule of its own. Today an
entry with no trailing period makes `definition_sentence` raise `ValueError`,
and `context_enumeration` reads the whole remainder instead. A fixture entry
with no trailing period makes both raise.

## Record

- 2026-10-24: found in the third review of the parked draft ADR (b-2227b0).
- 2026-10-27: done by `SA-0317` in #979, from the spec loop's run 49.
