---
id: 38
title: '`events.Phase` splits `GATE ⇄ REPAIR`, and `CONTEXT.md` does not'
status: open
tier: 2
specs: []
prs: []
commits: []
cites: []
related: [37]
by_hand: true
---

## Problem

`CONTEXT.md` names six phases, counting `GATE ⇄ REPAIR` as one; `events.Phase`
lists seven, because a gate attempt and a repair turn print different lines.
The split is probably right and is currently held by a comment and a test.

## Done looks like

Done looks like: `CONTEXT.md` saying whether it is sanctioned, and the `Literal`
following. Protected, so by hand. Second divergence — see item 37.
