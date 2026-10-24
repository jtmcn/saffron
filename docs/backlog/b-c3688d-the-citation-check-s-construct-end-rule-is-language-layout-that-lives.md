---
id: b-c3688d
title: The citation check's construct-end rule is language layout that lives in core
status: open
tier: 3
filed: 2026-10-24
specs: []
prs: []
commits: []
cites: [§2.1, §3.2]
related: [b-2da959]
---

## Problem

Found in the spec loop's run 47, by both seats on `SA-0314` (#956).

`saffron/spec_citations.py` reads where a construct starts from the policy's
`citations.definitions`. Where it ends is built into core: lines indented past the header,
or a closing bracket level with it. Review taught `_indent` to count tabs. A language whose
blocks end by keyword still reads as a one-line construct.

## Done looks like

The policy declares how a construct ends beside how it starts, and core reads both.

## Record

- 2026-10-24: filed from the spec loop's run 47.
