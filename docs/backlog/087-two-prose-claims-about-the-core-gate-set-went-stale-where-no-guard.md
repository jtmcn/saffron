---
id: 87
title: Two prose claims about the core gate set went stale where no guard reaches
status: done
tier: 3
closed: 2026-09-22
specs: []
prs: [446]
commits: [1b9e6701, 057f674d]
cites: [§2.1, §5.4.1, §7]
related: [71, 72]
by_hand: true
---

## Problem

Found reviewing item **72**'s own branch (#164), 2026-09-07. Neither is a live
defect — both are sentences that were true when written and are now false, in
the two places item 72's new guard cannot see. That guard compares
`saffron/gates/core/*.py` against `ontology/factory.ttl`; it reads no prose.

`DESIGN.md` §7's risk table says *"The seven core gates never execute repo
code — most read the diff, but `census` and `criteria` read other gates' results
instead; any core gate that wants to *run* something belongs on the repo side"*.
Nine now, and the second half is the larger error: `revert` and `witness` both
invoke the repo's declared `tests` gate (§5.4.1 calls `witness` *"`revert`'s
exception, not a new one"*), so the row's own rule reads as violated by two of
the gates it governs rather than as the boundary it is. The distinction the row
wants is *invokes a declared gate* versus *knows a tool*, which is §2.1's actual
line.

`saffron/gates/contract.py:113` still carries **"Nothing reads it yet, and the
thing that will currently disagrees."** in `witness_blocking`'s docstring.
`session.py:998` reads it — item **71**'s reconciliation landed and left the
paragraph describing the world before it. This one costs something today: item
72's commit message and `SizeTierShape`'s comment both cite
`contract.witness_blocking` as the authority for `witness`'s blocking level, and
a reader who follows the citation lands on a paragraph saying nothing reads it.

## Done looks like

both sentences corrected by hand — `DESIGN.md` is
`protected` and its §7 table is not generated, so neither is a cell's to touch.
Worth deciding separately whether the `revert`/`witness` distinction deserves a
`CONTEXT.md` §4 line of its own, since three files now state it in three
wordings. Half an hour.

## Record

**Status: done, 2026-09-22, by hand.** The docstring half went first. The
`1b9e6701` refactor rewrote `witness_blocking`'s docstring, and it now names
`saffron.gates.suite` as the reader. The `DESIGN.md` half landed with ADR 2
(#446, `057f674d`). §7's row now says core never runs a tool, and it names
`revert` and `witness` as the gates that invoke the declared `tests` gate.
The same commit corrects §5.4, which called `revert` the one place core
reaches into the toolchain.

The `CONTEXT.md` §4 question is answered by ADR 2. The `revert`/`witness`
distinction now has one statement, in
`docs/adr/0002-core-invokes-declared-gates-never-tools.md`.
