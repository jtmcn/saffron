---
id: 37
title: '`events.Terminal` and `CONTEXT.md`''s "terminal state" are two different things'
status: open
tier: 2
specs: [SA-0029, SA-0030, SA-0040]
prs: []
commits: []
cites: [§4.1]
related: [36]
by_hand: true
---

## Problem

`CONTEXT.md` reserves **terminal state** for the states that reach the operator.
`events.Terminal` means the five ways an IMPLEMENT turn ends having committed
nothing. Two of the five map onto a terminal state, which makes the collision
easy to miss rather than hard.

Renaming was deferred because `SA-0029`'s criteria and `SA-0030`/`SA-0040` all
cite `Terminal`. An earlier draft of this item said the name was `DESIGN.md`
§4.1's; it is not — see item 36. Found reviewing PR #91.

## Done looks like

`TurnEnded` across the three specs, or a `CONTEXT.md` entry
saying the two terms are deliberately distinct. Protected either way, so by
hand, and worth settling before `SA-0040` and `SA-0038` render the word.
