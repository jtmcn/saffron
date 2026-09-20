---
id: b-08a36a
title: The prose hook reads the index, so `make check` passes on a new spec that has never been staged
status: open
tier: 2
filed: 2026-09-19
specs: []
prs: [378]
commits: []
cites: []
related: [44, b-044ae7, b-281f0a]
---

## Problem

Found 2026-09-19, committing `SA-0112` on `joel/spec-writer-agent`. The spec
was written in a worktree where `make check` exited 0 and the author reported
that as evidence. Staging the same file refused the commit. It carried 28
em-dashes, 53 sentences over the limit, 12 semicolons, and one retired
vocabulary term.

`.pre-commit-config.yaml:70-75` declares the hook with
`pass_filenames: false`, and `hooks/prose_limit.py:48-51` reads
`git diff --cached --name-status -M -z --diff-filter=AMR`. The hook inspects
the index. It never reads the working tree, and `prek run --all-files` changes
nothing, because the file list prek passes is discarded.

Two consequences, both measured today.

- **An unstaged file is invisible.** A scratch Markdown file carrying an
  em-dash and a 34-word sentence was written into this worktree.
  `prek run --all-files` reported `prose limit … Passed`. `git add -N` on the
  same file kept it passing, because the intent-to-add entry stages no
  content.
- **A staged file is read at its staged content.** After a refused commit, the
  index holds the old copy. The working tree was then fixed and
  `make check` reported the original hits, naming lines the file no longer
  had. The second run, after `git add`, passed.

The cost is not the hook's rule. `make check` is what every author in this
repo reports as done, and `docs/agents/issue-tracker.md:49-50` tells a spec
author to run it before pushing. For a new file it answers a question nobody
asked. The `prose` gate itself is unaffected: a cell's gate
reads a diff against `base_sha`, where every file is committed.

## Done looks like

`make check` says something true about a new file's prose, or says nothing and
is known to say nothing.

The cheap shape is a second entry point on the same script. It takes paths
from prek instead of the index, so `make check` covers every tracked and
untracked file in scope. The index path stays as it is, because the commit
hook is where the per-commit limit belongs.

The other shape is a note in `docs/agents/issue-tracker.md` and in
`.claude/agents/spec-writer.md`. It says `make check` does not read an
unstaged file, and names the per-file invocation that does. That costs one
line in each, and leaves the hole open for anyone who does not read them.

## Record

- 2026-09-19: filed by hand from PR #378, whose **Not covered** section names
  this. The measurement above is that branch's, and `SA-0112` is the spec that
  paid for it.
