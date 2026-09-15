---
id: 2
title: The agent can disable a core gate from inside the cell
status: done
tier: null
closed: 2026-08-20
specs: [SA-0002]
prs: []
commits: [cf0dee8]
cites: []
related: [17]
---

## Problem

`worktree.export_patch` runs bare `git diff`, inheriting worktree config the
agent can write. One `git config diff.srcPrefix x/` and a diff deleting the
entire test suite reads as `pass`, because path matching no longer recognises
anything.

## Done looks like

`export_patch` pins `--src-prefix=a/ --dst-prefix=b/
--no-ext-diff`, and any core gate reading a diff refuses a prefix it does not
recognise rather than silently passing. A test that sets the hostile config and
asserts the gate does not report `pass`.

## Record

**Status:** **done**, in `cf0dee8` (*fix(cell): a gate the agent could
reconfigure from inside the cell*). `DIFF_FLAGS` at `saffron/cell/worktree.py:131`
pins `--src-prefix=a/`, `--dst-prefix=b/` and `--no-ext-diff`, and both
`export_patch` and `changed_files` diff through it.

**Done, 2026-08-20.** `worktree.DIFF_FLAGS` pins prefixes, `--no-ext-diff`,
`--no-textconv` and `--no-renames` on every diff the host reads, and `_git` adds
`-c core.quotePath=false`; a command-line flag beats repo-local `.git/config`,
measured on git 2.50 (including config reached through `include.path`).
`scope_gate` is handed that diff and reports `error` — infrastructure, charged to
nobody — when the headers are not `a/ b/`. Two things the review's account got
slightly wrong, both measured: `--name-only`, which is what `scope` actually
consumed, was never bent by `diff.srcPrefix` (the `pass` was the rejected
`integrity` gate's, which parses hunks); and `diff.external` and a textconv
driver are the sharper knobs — either can empty a diff entirely. Still open: a
`-diff` attribute renders a text file as `Binary files ... differ`, which hides
*content* but never a path, so `scope` is unaffected and the future `integrity`
gate must treat such a section as unreadable rather than as no change.

**And `size` inherits it, 2026-08-25.** Measured on `SA-0002`'s gate: a block
with no `@@` contributes 0, so `*.py -diff` in `.gitattributes` makes a
2000-line rewrite count as 1 and pass — at `elevated`, the one tier where
`size` blocks. It carries a `ponytail:` comment naming the ceiling rather than
a fix, because the honest response is `error` only when the unreadable file is
inside `touches`, as `integrity` already does, and `size_gate` is handed
neither `touches` nor a `--numstat` cross-check. **The wiring spec has both and
should close it**, which makes that spec's second reason to exist.

**Closed at the tier that blocks; corrected 2026-08-25 (#27).** `size_gate` is
handed `touches` and returns `error` when an unreadable block names a declared
path (`_unreadable_declared_path`, `saffron/gates/core/size.py:101`) — reusing
`scope.matches`, so "declared" means one thing in every gate. The paragraph
above stood as outstanding work after the work had shipped, which is the shape
#26 found on item 17: a stamp read as a plan.

**Two residuals, and the first was nearly lost to the correction above.** The
guard is `if unreadable is not None and blocking` (`size.py:162`), so at
`standard` an unreadable declared path still counts as zero lines silently.
That is the right scope — the original complaint was about `elevated`, the one
tier where `size` blocks — but it is a narrower closure than "closed", and an
advisory gate that under-reports is still a gate reporting something false.
The `--numstat` cross-check remains an upgrade path in the docstring rather
than shipped code.
