---
id: b-714ccd
title: "A witness that asserts the input's default value passes REBUT, though it cannot tell the fallback from a constant"
status: open
tier: 2
filed: 2026-10-12
specs: []
prs: []
commits: []
cites: [§5.5]
related: [b-20043f]
---

## Problem

Found by the adequacy lens and both seats on #845 (`SA-0266`), in the spec
loop's run 35.

The spec says the risk falls back to the spec's own `risk`. REBUT's fix
asserted `effective_risk == "standard"` on a spec with no `risk:`. Its
default is `"standard"`, so a hardcoded `"standard"` passed. The adequacy
lens confirmed the blocker still stood after REBUT, and the task packaged
anyway. The review commit seeded `risk: elevated` and the probe died.

## Done looks like

- The adequacy lens names a witness whose expected value equals the
  input's default, and asks for an input that separates the two.
- A confirmed adequacy blocker after REBUT keeps the task from packaging
  unanswered.

## Record

- 2026-10-12: filed from the spec loop's run 35 (#845).
