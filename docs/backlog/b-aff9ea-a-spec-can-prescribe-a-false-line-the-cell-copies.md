---
id: b-aff9ea
title: "A spec can prescribe a documentation line that contradicts the code, and the cell copies it faithfully"
status: open
tier: 2
filed: 2026-10-12
specs: []
prs: []
commits: []
cites: [§3.4]
related: [b-20043f]
---

## Problem

Found by both seats on #847 (`SA-0268`), in the spec loop's run 35.

`SA-0268` told the cell to write that `saffron package` runs inside the two
images. `saffron package` never starts the proxy, so it needs only the base
image. The cell wrote the line as told. The review commit corrected it
against the spec.

Run 34 found two specs that dictated text breaking a `CONTEXT.md`
definition or a measured fact. Its feedback asked for a spec review that
checks prescribed text, and no item carried it.

## Done looks like

- The spec reviewer checks each line a spec prescribes verbatim against
  the code and `CONTEXT.md` at its base.
- A prescribed line that contradicts either is a blocker on the spec.

## Record

- 2026-10-12: filed from the spec loop's run 35 (#847), carrying run 34's third feedback item.
