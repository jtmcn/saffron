---
id: b-e773d9
title: Two queued specs in separate chains clash on a name one deletes and the other reads, and no check compares names
status: open
tier: 1
filed: 2026-10-12
specs: [SA-0268, SA-0271, SA-0290]
prs: [849]
commits: []
cites: [§4.2.1]
related: []
---

## Problem

Found by the delegate on 2026-10-12, while writing `SA-0284`.

`SA-0268` adds a host probe to `saffron/task.py`. It reads
`runtime.GATEWAY` and calls `create_network` with no subnet. `SA-0271`
deletes `GATEWAY` and every subnet default, and it forbade
`saffron/task.py`. The two sat in separate chains with no `depends_on`
between them. Whichever landed second would end `EXHAUSTED`, at up to $45.
PR #849 fixed this pair by hand.

Neither check saw it. The pre-flight's overlap check and the queue's
refusals compare `touches`. These two specs share no path, because each
forbids the file the other changes. They clash on a name.

A spec already declares the names it reads from a parent in `consumes`.
Nothing declares the names a spec deletes or renames.

## Done looks like

One queued spec deletes a name, and another reads it or adds a reader of
it. The queue refuses that pair unless a `depends_on` orders them. The
refusal names both specs and the name. A declared field in the spec is one
way to get there. A pre-flight command over the specs' text is the cheaper
first step.

## Record

- 2026-10-12: filed from the SA-0268 and SA-0271 conflict, fixed by hand in
  PR #849.
- 2026-10-12: specced as `SA-0290`, the declared field and the queue
  refusal. The operator ruled out the pre-flight command for a cell, since
  `SA-0279` refuses a spec touching `.claude/`.
