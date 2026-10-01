---
id: b-ef8543
title: A spec's wrong builds in prose never reach REVIEW's host run
status: partial
tier: 2
filed: 2026-09-29
specs: [SA-0151, SA-0152, SA-0167]
prs: [597, 627]
commits: []
cites: []
related: [b-7e69d0]
---

## Problem

Found in the spec loop's run 22, 2026-09-29, at step 1b.

`SA-0152`, `SA-0151` and `SA-0167` each listed about 35 wrong builds under
"These fail it:" in their notes. None declared `wrong_versions:`. REVIEW runs
only the declared ones.

```
declaring = [c for c in spec.acceptance if c.wrong_versions]
```

That line is `saffron/cell/session.py:2769`. So the host ran none of them. The
chain PR #597 moved up to five per criterion by hand.

The issue tracker rule says a spec names its wrong versions under
`wrong_versions:` (`docs/agents/issue-tracker.md:118-126`). Nothing checks it.

## Done looks like

`driver.py check`, or intake, warns when a spec's notes list wrong builds and
a criterion declares no `wrong_versions:`.

## Record

- 2026-09-29: filed from the spec loop's run 22.
- 2026-10-01: `SA-0151` declares its wrong builds now (#627), and its cell expressed all 23. `SA-0152` and `SA-0167` still list theirs in prose.
