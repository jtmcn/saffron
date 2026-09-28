---
id: b-1e9a7a
title: An in-cell REVIEW concern is re-anchored at the packaged head, so a REBUT edit that shifts lines can lose it
status: open
tier: 3
filed: 2026-09-27
closed:
specs: []
prs: []
commits: []
cites: [§5.5]
related: [b-792ab2]
---

## Problem

Found in the spec loop's run 19, 2026-09-27, reviewing `SA-0147` (#542).

`SA-0147` adds each layer's in-cell REVIEW concerns to the end review's
findings. It anchors them at the layer's packaged head. REVIEW read the diff
before REBUT. A REBUT edit that shifts lines moves or drops the anchor. The
in-cell correctness lens raised it, and both seats kept it as a design
residual.

## Done looks like

A concern anchors at the commit REVIEW read, or carries that commit. A test
holds a REBUT edit that shifts the concern's line.

## Record

- 2026-09-27: filed from the spec loop's run 19.
