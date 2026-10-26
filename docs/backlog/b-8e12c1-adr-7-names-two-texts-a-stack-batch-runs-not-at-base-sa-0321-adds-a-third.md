---
id: b-8e12c1
title: ADR 7 and the glossary name two texts a stack batch runs that are not at `base_sha`, and SA-0321 adds a third
status: open
tier: 2
by_hand: true
filed: 2026-10-26
specs: [SA-0321]
prs: []
commits: []
cites: [§4.2.1]
related: [b-009d51]
---

## Problem

Found 2026-10-26, writing `SA-0321`.

`SA-0321` makes a stack batch rewrite a citation whose construct moved to
one place. It records the rewritten text as the task's spec text before
the spec review. Three protected texts say a stack batch runs no such text.

- ADR 7 says the text not at `base_sha` "is a spec review's revision or a
  follow-up, and nothing else" (`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md:86-88`).
- `DESIGN.md` §4.2.1 names a revision and a follow-up spec as the two
  exceptions (`DESIGN.md:472`).
- `CONTEXT.md`'s **Recorded spec text** says a revision, a follow-up and a
  draft each write one (`CONTEXT.md:219-222`).

All three are `protected`, and `SA-0321` forbids them.

## Done looks like

ADR 7 is amended to add a third text: a queued spec whose moved citations
the batch rewrote. `DESIGN.md` §4.2.1 names it beside the other two. The
**Recorded spec text** entry names the citation rewrite among its writers.
All three land in `SA-0321`'s own pull request.

## Record

- 2026-10-26: filed with `SA-0321`.
- 2026-10-26: edited by hand in `SA-0321`'s pull request. ADR 7 carries an
  amendment, and `DESIGN.md` §4.2.1 and **Recorded spec text** name the rewrite.
  It closes with that pull request's number.
