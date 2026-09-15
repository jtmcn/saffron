---
id: 7
title: '`CLAUDE.md` no longer reaches the agent, so the flywheel''s middle bucket is inert'
status: done
tier: 1
closed: 2026-09-11
specs: []
prs: []
commits: [0d5f8e6]
cites: [§2.1, §8]
related: []
---

## Problem

`setting_sources: []` was set because a target repo's `.claude/` was configuring
the agent working on it — measured, a planted subagent and skill both loaded out
of `/work` (Appendix J). The fix is right and it has a cost: the repo's
`CLAUDE.md` stops loading too, and that is §2.1's named learning surface and
**bucket 2 of §8's entire flywheel.**

## Done looks like

`CLAUDE.md` injected host-side from the mirror, the way
`CONTEXT.md` already is — which is the better shape anyway, since a file under
`/work` is rewritable mid-attempt.

## Record

**Status: done, 2026-09-11** (`fix(review): no lens was shown the invariants it judged a
diff against`). `mirror.file_at` reads `CLAUDE.md` at `base_sha` and
`context.standing_instructions` injects it into IMPLEMENT, which REPAIR, REBUT and the
extraction turns resume — and, now, into the three review lenses and the verdict lenses too,
once the lens corpus's spread was measured
(`docs/evidence/2026-09-11-lens-corpus-spread.md`,
`docs/superpowers/plans/2026-09-10-claude-md-reaches-every-phase.md`). The corpus was re-run
under the change on 2026-09-11: the per-run ranges overlap, so the decision rule reads no
measurable difference at n=3 (`docs/evidence/2026-09-11-lens-corpus-claude-md.md`).
