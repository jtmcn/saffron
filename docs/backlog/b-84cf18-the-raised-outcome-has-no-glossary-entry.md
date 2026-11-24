---
id: b-84cf18
title: "The `raised` outcome of a REVIEW edit has no glossary entry"
status: open
outside_cell: true
tier: 3
filed: 2026-11-24
specs: []
prs: []
commits: []
cites: [§5.4.1]
related: [b-c2f264]
---

## Problem

`SA-0431` adds `raised` to the outcomes a criterion probe, a wrong version
and a parent's version can record. It means the witness failed under the
edit only by raising, and no assertion failed. The `witness` gate names such
a witness in its summary too. `CONTEXT.md` defines `killed`, `survived` and
`unproven` for these edits, and has no entry for `raised`.

## Done looks like

The **Criterion probe** and **Wrong version** entries in `CONTEXT.md` name
`raised` and say it files a concern rather than a blocker. `DESIGN.md`
§5.4.1 says the `witness` gate and REVIEW read a raise apart from a kill,
under the repo's declared `witness: assertion:` pattern.

Four more passages say only a host-filed survivor, or only an anchored
concern, reaches REBUT. Each names the host-filed concern too:

- `DESIGN.md:1261`, on findings reconciled against the diff.
- `DESIGN.md:1313`, on REBUT's anchored concerns.
- `CONTEXT.md:808-809`, on an unanchored host-filed survivor.
- `CONTEXT.md:850-853`, the **Rebuttal** entry.

Both files are protected, so the edit is made by hand once `SA-0431` lands.

## Record

- 2026-11-24: filed with `SA-0431`.
