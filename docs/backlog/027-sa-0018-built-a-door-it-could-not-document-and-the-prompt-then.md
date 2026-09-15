---
id: 27
title: '`SA-0018` built a door it could not document, and the prompt then contradicted it'
status: done
tier: null
specs: [SA-0018, SA-0021]
prs: []
commits: []
cites: [§3.3, §5.2, §5.3.1]
related: [28]
---

## Problem

**Status:** **done** — `SA-0021`, by hand on the host, 2026-08-30.

`SA-0018` added a second producer of `SCOPE_REVIEW`: an IMPLEMENT attempt whose
declared `touches` cannot satisfy its criteria proposes a set instead of grinding
to a ceiling. The code shipped and works. The documents that define what the words
mean did not move, because **`DESIGN.md` and `CONTEXT.md` were both in `SA-0018`'s
own `forbidden` list** — so the spec that created the affordance was structurally
unable to describe it.

The result was a prompt that contradicted itself. `CONTEXT.md` §3 is injected into
the IMPLEMENT system prompt (`SECTIONS_BY_PHASE['IMPLEMENT']` is `(1, 2, 3, 4, 10)`),
and its **Touches** entry read "proposed by DIAGNOSE and ratified by the operator on
bug specs". So the same assembled prompt offered the implementer the door and told
it, more specifically, that the door was DIAGNOSE's on bug specs. The specific
sentence wins that argument.

**This is the situation `SA-0018` exists to give an exit from, one spec later and
one level up.** Its `touches` could not reach the files its own feature made wrong;
by the feature's own logic the correct move was a scope proposal naming `DESIGN.md`
and `CONTEXT.md`. It was found by review instead. Note that a *proposal* naming
those paths would have been recorded — `validate_scope_proposal` checks only that a
path escapes `touches`, not that it escapes the deny lists — so the door was open;
nothing pointed the implementer at it.

Closed by `SA-0021`, by hand on the host (see item 28), 2026-08-30: §3.3 draws
`SCOPE_REVIEW` from IMPLEMENTING, §5.3.1 states the door's three rules, §5.2 no
longer claims the contract as DIAGNOSE's alone, and `CONTEXT.md`'s **Touches**
entry names both proposers. The witness reads the *assembled* prompt rather than
`CONTEXT.md`'s text, because reasoning about which sentences reach the model is
what failed here.
