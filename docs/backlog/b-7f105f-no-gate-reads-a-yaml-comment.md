---
id: b-7f105f
title: "No gate reads a YAML comment, so the comment rule goes unenforced in `.pre-commit-config.yaml`"
status: open
tier: 3
filed: 2026-10-09
specs: []
prs: [790]
commits: []
cites: []
related: [b-f8fa24]
---

## Problem

Found by #790's Standards seat in the spec loop's run 32.

`CLAUDE.md` holds a comment to one or two lines with no semicolon. The `prose`
gate reads Markdown and Python only. `SA-0255`'s hook block carried a
three-line preamble and a semicolon, and no gate saw either. #790's review
fixed both by hand in 4ac2fbb7. The `dead` hook's preamble runs four lines
(`.pre-commit-config.yaml:22-25`), and the `ast-grep` one runs nine.

## Done looks like

`prose` reads comments in the repository's YAML files under the same rules as
Python comments, with a baseline for the existing hits. Or a recorded decision
says why not.

## Record

- 2026-10-09: filed from the spec loop's run 32.
