---
id: 85
title: The host runs one copy of a spec and the cell reads another
status: done
tier: 1
specs: [SA-0064]
prs: []
commits: []
cites: []
related: [80, 83]
---

## Problem

**Status: done, 2026-09-08 (#166).** `spec_drift` compares the two copies
the run already holds and reports through `Preflight`. It never refuses: an
operator iterating on a spec is exactly what produced this. Absence is silent —
the first version reported a spec with no copy at base, which is the ordinary
shape of an attended run and the *absence* of the hazard rather than an
instance of it, and it would have printed on nearly every run.

Measured 2026-09-07, on `SA-0064`'s second run.

`saffron cell <path>` loads the spec with `load_spec(args.spec)` — the file the
operator names, on disk, now. The cell's worktree is built from the mirror at
`base_sha`, so it carries whatever `.saffron/specs/` holds on the default
branch. Nothing compares them.

They differed on this run, and it showed. The host's copy had criterion 2's
mutant removed (item **83**, an hour earlier); `main`'s copy still carried it.
The implementer's notes then reasoned about *"Criterion 2's spec-declared mutant
lives in `saffron/cell/session.py`"* — a field `agents/context.py` withholds
from the prompt by construction, and one the host's own copy no longer had. The
agent was working from a contract the host was not judging it against.

This is also the measurement item **80** asked for and it is what moves that
item to tier 1: the prompt-level withholding of `mutant` is defeated by the
worktree copy, and now demonstrably rather than in principle.

**Done looks like** attended mode reporting the difference, or refusing it. Both
copies are already in hand at preflight — `spec_sha` is computed host-side and
`.saffron` is exported from `base_sha` regardless — so the check is a comparison
of two strings the run already holds, not new machinery. Refusing may be too
strong for an operator deliberately iterating on a spec, which is exactly what
produced this; naming it in the preflight line is not.
