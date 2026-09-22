---
id: b-76953a
title: Two protected sentences say no gate applies a criterion probe, and after `SA-0120` the host applies every one
status: open
tier: 3
filed: 2026-09-21
by_hand: true
specs: []
prs: []
commits: []
cites: [§5.4.1]
related: [b-2750d5, b-0c1d69]
---

## Problem

Found writing `SA-0120`, 2026-09-21. Once it lands, the host applies each
criterion probe in a Gate-only cell after REVIEW. It runs that criterion's
witness over the edit and files a survivor as a blocker for REBUT. Two
protected sentences still end on the item that work closes.

- `DESIGN.md:989` reads "No gate applies one yet (backlog item b-2750d5)."
- `CONTEXT.md:369`, the *criterion probe* entry, reads "No gate applies one yet
  (backlog item b-2750d5)."

Both stay literally true, since the host applies the edit and no gate does.
A reader takes them to mean nothing applies one at all. Both files are
`protected`, so no cell can edit them.

## Done looks like

Both sentences say the host applies each criterion probe in a Gate-only cell
and files a survivor as a blocker for REBUT. `CONTEXT.md` changes through
`ontology/factory.ttl` if the entry is generated from it.

## Record

- 2026-09-21: filed by hand with `SA-0120`. It waits on that spec's merge.
