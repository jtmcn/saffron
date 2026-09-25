---
id: b-50b566
title: The authoring docs do not list the consumes field, and the pre-flight still checks consumed names by reading
status: open
tier: 3
by_hand: true
filed: 2026-09-23
specs: []
prs: []
commits: []
cites: [§3.2]
related: [b-602d00, b-343c21]
---

## Problem

Found 2026-09-23, in the spec review of `SA-0135`.

`SA-0135` adds `consumes:` to the spec frontmatter, and `SA-0136` refuses
nine malformed entry shapes at load. The authoring docs say neither.

- `docs/agents/issue-tracker.md` lists every frontmatter field and its
  default (`docs/agents/issue-tracker.md:12-16`). It does not list
  `consumes`, its entry forms, or that it needs a `depends_on`.
- `create-saffron-spec` pre-flight check 4 asks the writer to name what a
  child keys by and to check that its parent produces it
  (`.claude/skills/create-saffron-spec/references/preflight.md`, section 4).
  Once the host checks it, the writer declares it in `consumes:` instead.

Both files are outside the two specs' `touches`.

## Done looks like

`docs/agents/issue-tracker.md` lists `consumes`: a list of repo-relative
`path` or `path:name` entries, resolved at the tree base, refused at load
without a `depends_on` or in a malformed shape. Pre-flight check 4 tells the
writer to put what a child keys by into `consumes:`. This lands after
`SA-0136` merges.

## Record

- 2026-09-23: filed after `SA-0135` and `SA-0136` were queued.
- 2026-09-25: #517 lists `consumes` in `docs/agents/issue-tracker.md`, with
  its entry forms and its need for a `depends_on`. The malformed shapes and
  the pre-flight's check 4 are still open.
