---
id: SA-0021
title: the IMPLEMENT prompt offers a scope proposal and tells the agent scope is DIAGNOSE's job
type: docs
priority: 1
depends_on:
  - SA-0018
touches:
  - DESIGN.md
  - CONTEXT.md
  - docs/BACKLOG.md
  - tests/test_context.py
  - tests/ontology/test_vocabulary_agrees_with_context.py
forbidden:
  - .saffron/**
  - saffron/**
  - images/**
  - tests/test_session.py
  - tests/test_implement.py
  - tests/test_artifacts.py
budget_usd: 8
max_attempts: 3
max_turns: 70
risk: standard
---

## Context
`SA-0018` built a second producer of `SCOPE_REVIEW`: an IMPLEMENT attempt whose
`touches` cannot satisfy its criteria can end by proposing scope instead of
burning to a ceiling. The code shipped and works. The documents that define what
the words mean were `forbidden` to that spec, so none of them knows it happened.

That is not only a documentation debt. `CONTEXT.md` is injected into the agent's
system prompt per phase, and the stale sentence is inside the section IMPLEMENT
receives:

```
uv run python -c "
from saffron.agents.context import SECTIONS_BY_PHASE
print(SECTIONS_BY_PHASE['IMPLEMENT'])"
```

returns `(1, 2, 3, 4, 10)`, and `CONTEXT.md`'s **Touches** entry — line 147, under
`## 3. Scope` (line 141) — reads:

> Declared directly on non-bug specs; proposed by DIAGNOSE and ratified by the
> operator on bug specs.

So the IMPLEMENT system prompt now tells the agent, in the same breath, that it
may propose scope and that proposing scope is DIAGNOSE's job on bug specs. The
door `SA-0018` built is described to the agent as one it cannot use, on exactly
the feature specs it was built for.

`DESIGN.md` is wrong in two further places: §3.3's diagram (line 238) draws
`SCOPE_REVIEW` reachable only from `DIAGNOSING`, and §5.2 is titled *"Phase 1 —
DIAGNOSE (bugs only)"* while §5.3 (IMPLEMENT) says nothing about the door at all.

**This is `SA-0018`'s own situation, one spec later.** Its `touches` could not
reach the files that needed changing, `DESIGN.md` and `CONTEXT.md` were both in
its `forbidden` list, and by the feature's own logic the correct move was a scope
proposal. Found by review instead.

## Problem
- **A prompt that contradicts itself is worse than one that says nothing.** The
  implementer reads both sentences and has to guess which governs. The guess it
  is being pushed toward is the wrong one, because the stale sentence is
  specific ("on bug specs") and the new affordance is general.
- **`CONTEXT.md` is authoritative for what the words mean** and is enforced,
  including its `_Avoid_` lists. A vocabulary file that is wrong about a term is
  wrong everywhere the term is checked.
- **`DESIGN.md` section numbers are an API** — specs cite them, and `SA-0018`
  cited §5.2 for a contract §5.2 describes as bug-only.

## Acceptance criteria
- [ ] §3.3's state-machine diagram shows `SCOPE_REVIEW` reachable from
      IMPLEMENTING as well as from DIAGNOSING
- [ ] A new subsection under §5.3 states the IMPLEMENT door and its rules — the
      proposal ends the attempt, it must name a path outside `touches`, and the
      task's own spec path is added host-side — **added as a subsection, never
      by renumbering an existing one**
- [ ] §5.2's title no longer claims an exclusivity §5.3 now shares, and §5.2's
      ratification contract reads as shared by both producers rather than as
      DIAGNOSE's alone
- [ ] `CONTEXT.md`'s **Touches** entry names both proposers, so the sentence
      the IMPLEMENT prompt carries no longer contradicts the affordance the
      same prompt offers
- [ ] A test asserts on the **assembled IMPLEMENT system prompt** — not on
      `CONTEXT.md`'s text — that it does not tell the agent scope proposal is
      DIAGNOSE-only. The defect is what reaches the model, so that is what the
      witness must read
- [ ] `docs/BACKLOG.md` records that `SA-0018` could not fix this because both
      files were in its `forbidden` list, and that this is the situation
      `SA-0018` itself exists to give an exit from
- [ ] Every new test runs with no network and no cell

## Out of scope
**Any change under `saffron/`.** This spec changes what the documents say, not
what the code does; `saffron/**` is forbidden. If a document turns out to
describe behaviour the code does not have, that is a separate spec — say so in
`docs/BACKLOG.md` rather than editing the code to match the prose.

**Renumbering `DESIGN.md`.** Section numbers are an API and specs on disk cite
them. Add subsections.

**The `SCOPE_REVIEW` rendering in the morning queue.** §6 already describes it
and `saffron/report/**` is untouched here.

**Auto-ratification.** §11 lists it as a deferred idea conditioned on evidence
that ratification has become rubber-stamping. No such evidence exists yet.

## Notes for the agent
**Read the assembled prompt, do not imagine it.** `saffron/agents/context.py`
injects sections by number; `SECTIONS_BY_PHASE['IMPLEMENT']` is `(1, 2, 3, 4, 10)`
and section boundaries are parsed from the headings. A criterion above asks for a
test against the assembled string precisely because reasoning about which
sentences reach the model has already failed once — that is this spec.

**`SA-0018`'s spec text is not yours to edit.** An edit moves its `spec_sha`
(§4.2.1) and `.saffron/**` is forbidden. Where the record needs correcting, the
correction goes in `docs/BACKLOG.md`.

**This spec cannot be scheduled while its parent is unmerged**, and
`depends_on` is refused outright by the scan until `SA-0020` lands. Run it
attended, after `SA-0018`'s pull request has merged:

```
uv run saffron cell .saffron/specs/SA-0021-the-implement-prompt-contradicts-the-door-it-offers.md --repo .
```

Commit after each coherent step. Uncommitted work dies with the cell.
