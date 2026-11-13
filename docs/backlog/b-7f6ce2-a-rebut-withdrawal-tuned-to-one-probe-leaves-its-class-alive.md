---
id: b-7f6ce2
title: A blocker REBUT withdraws once the witness kills its one probe, so the probe's siblings still pass
status: open
tier: 3
filed: 2026-11-13
closed:
specs: []
prs: []
commits: []
cites: [§5.6]
related: [b-92c92a, b-9ed36d]
---

## Problem

Found reviewing #1183 (`SA-0381`) in the spec loop's run 67.

The host filed a criterion probe as a blocker. It skipped the cut for any
draft holding `&`, and the witness stayed green. The implementer added an
unused `&flow_deps` anchor to one test draft. The probe then failed, and
the adequacy lens withdrew its blocker
(`~/.saffron/batches/v0/SA-0381/rebuttal.json`).

The same probe with `#` or `*` in place of `&` still passed. Both review
seats found it, and a review commit added a comment and a glob to one draft.
The verdict session saw one probe killed and judged the class closed.

## Done looks like

A probe REBUT reruns to withdraw a blocker is joined by its siblings: the
same edit with each other character class the claim names. The blocker
stays unless every sibling also fails the witness.

## Record

- 2026-11-13: filed from the spec loop's run 67.
