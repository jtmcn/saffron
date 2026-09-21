---
id: b-4bd68a
title: A lens can search code only as text, and a command tool would let it edit the tree it judges
status: open
filed: 2026-09-21
specs: []
prs: []
commits: []
cites: [§2.1, §5.3, §5.5]
related: []
---

## Problem

Found 2026-09-21, asking why agents here do not search with `ast-grep`.

A lens gets `Read`, `Glob` and `Grep` and nothing else
(`saffron/phases/review.py:35`). Grep answers most questions a lens asks.
It cannot match by structure, such as every call that passes one keyword
argument, or every function a changed decorator wraps. Test adequacy
(§5.5.1) asks exactly those questions about code the diff did not touch.

Handing the lens `Bash` is not the fix. Every lens in a task reads one
critic cell's worktree, so a lens that runs a command can change what the
next lens judges. An `allowed_tools` rule such as `Bash(ast-grep run:*)`
does not close that. It still admits `ast-grep run -r ... -U`, which writes
files. It is also a control inside the cell, and a control inside a cell is
never the boundary.

`ast-grep` is also absent from the base image. Saffron's own
`.saffron/Dockerfile` installs it for the `structure` gate. A core tool that
calls it by name would break §2.1: core invokes declared gates, never tools.

## Done looks like

- A lens can run a structural search whose tool surface cannot write. The
  runner builds a fixed argument vector from a pattern, a language and a
  path, and no argument reaches a rewrite flag or a shell.
- The search is declared by the target repo in `.saffron/`. Core offers it
  to a lens only when the repo declares it, and `saffron/` never names
  `ast-grep`.
- A test starts a lens the way production does and shows the tool leaves
  the critic cell's worktree unchanged, with a mutant that passes `-U`.
- A lens run on a repo that declares nothing sees the same three tools as
  today.

## Record

**Filed 2026-09-21** from a session that drafted `ast-grep` usage for
`CLAUDE.md`. That draft covers the implementer, which already holds `Bash`.
This item covers the lenses, which do not.
