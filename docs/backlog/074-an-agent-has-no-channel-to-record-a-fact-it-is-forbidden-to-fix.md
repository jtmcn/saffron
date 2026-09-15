---
id: 74
title: An agent has no channel to record a fact it is forbidden to fix
status: done
tier: 1
closed: 2026-09-07
specs: [SA-0044, SA-0058, SA-0061, SA-0063, SA-0064]
prs: [150, 158, 160]
commits: [bb9fd74]
cites: [§5.3, §5.5]
related: [70, 71, 73, 84, 86]
---

## Problem

**Status: done, 2026-09-07** — the first shape below. `SA-0063` (PR #158) built
the channel: a `notes` artifact extracted and hashed at the moment it is
produced, carried on the outcome, rendered by `pr_body.py` under a heading that
names it as the implementer's own and unadjudicated, clipped and neutralized.
`SA-0064` (PR #160) connected the one production call that had not passed it.
The first finding to arrive through it is item **84**, in `SA-0064`'s own
`notes.json`. One caveat worth stating: no pull request body has carried a notes
section *yet* — `SA-0064` packaged under `base_sha` code that predates its own
wiring, so #160's body has none. The first task to run from a base at or after
`bb9fd74` is the measurement. Item **86** holds the rendering-side test gaps.

**Tier 1.** Found reviewing `SA-0061` (PR #150), 2026-09-06, and it is an
instruction this repo has now given twice and cannot be obeyed.

`SA-0058`'s spec said: *"if wiring reveals the gate needs a different shape,
that is a finding to file rather than an edit to make."* Nothing was filed;
that omission is item **71**. `SA-0061`'s spec therefore said it harder — *"and
this time file it, in the pull request body and in `docs/BACKLOG.md`'s
language"* — and wiring falsified four comments in files it could not touch.
One reached the operator, as a review lens's `concern`. Three did not.

**The instruction is unsatisfiable by construction.**
`saffron/report/pr_body.py` assembles a pull request body entirely from the
outcome: title, acceptance criteria, failures, the test diff, the disagreement
table, lens findings, gates, provenance. **There is no agent-authored prose
section anywhere in it.** The only text an agent writes that survives packaging
is a rebuttal — which exists only when a lens raised a blocker — and its commit
subjects, which no one reads as a findings channel.

And `docs/BACKLOG.md` is `protected` in `policy.yaml`, so "in
`docs/BACKLOG.md`'s language" cannot mean writing there either.

So a spec asking an agent to *record* something is asking for a thing the
system does not have, and every `forbidden` list makes that ask more likely:
the tighter the scope, the more an agent sees that it may not fix.

**Why this is Tier 1 rather than a nicety.** Every finding in items 70–73 came
from a review round after the fact. The agent that wired the gate is the one
that knew, at the moment it knew, which comment it had just falsified. That is
the cheapest possible moment to record it and the system throws it away.

**Done looks like** one of:

- **A findings section in the pull request body**, filled from something the
  agent writes — an artifact extracted and hashed at the moment it is produced,
  the way `plan.json` already is (§5.3), never re-read from `/work`.
- **Or a `notes` field on the outcome**, rendered by `pr_body.py` under a
  heading that says these are the agent's own and unadjudicated.

Either way it is untrusted text from a cell and must be rendered as such —
`SA-0044`'s anti-theater reasoning applies: an agent that can write prose into
a pull request body can write prose that sounds like a passing verdict. Clip
it, mark it, and never let it near a status.

**Not** a lens. §5.5's critics already produce findings and are adjudicated;
this is the *implementer* saying "I saw a thing I was told not to touch", which
is a different speaker and a different trust level.
