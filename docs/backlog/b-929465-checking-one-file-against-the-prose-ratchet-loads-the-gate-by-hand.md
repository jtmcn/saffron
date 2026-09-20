---
id: b-929465
title: Checking one file against the prose ratchet means loading the gate module by hand, and two agents wrote throwaway scripts to do it
status: open
filed: 2026-09-20
specs: []
prs: []
commits: []
cites: []
related: [b-08a36a, 163]
---

## Problem

Filed 2026-09-20. The `prose` gate limits growth per file, so a new file is
held to zero hits of every rule. The file beside it carries hundreds.
`hooks/prose_limit.py` applies that limit to what a commit stages. Neither
offers a way to ask what the gate would count for one unstaged path.

Two agents hit this on the same day and answered it the same way.

- Writing `b-a4df62` (#389, merged) meant loading `.saffron/gates/prose.py`
  through `importlib` in a throwaway script to see which rules the new record
  broke. The record failed the hook as first written.
- The `spec-writer` agent drafting `SA-0113` wrote two such scripts into the
  repository root, `prosecheck.py` and `prosedebug.py`, and deleted them before
  it finished.

`CLAUDE.md` gained four lines naming the ratchet's two traps in #389. That
tells a reader the rules and leaves them no way to run them. The gate itself is
out of reach for a cell, because `.saffron/**` is `protected` in
`.saffron/policy.yaml`. `hooks/` is not.

## Done looks like

`python3 hooks/prose_limit.py --file <path>` prints the hits both gates would
count for that path, against the file's `HEAD` version, or against zero when
the path is new. The hook keeps its staged-index behaviour for a commit, which
is item b-08a36a's subject and stays as it is.

## Record

- 2026-09-20: filed after two agents wrote the same throwaway script in one
  day. The `prose` rules themselves are documented in Appendix R and in
  `CLAUDE.md`, so this is the missing way to run them, not a missing rule.
