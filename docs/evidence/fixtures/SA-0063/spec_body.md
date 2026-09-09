
## Context

`docs/BACKLOG.md` item **74**, the top of tier 1. It is an instruction this
repo has now given three times and cannot be obeyed.

`SA-0058`'s spec said a finding should be filed rather than fixed; nothing was,
and that omission became item **71**. `SA-0061`'s spec said it harder — *"and
this time file it"* — and wiring falsified four comments in files it could not
touch: one reached the operator as a lens `concern`, three did not, and they
became item **75**. `SA-0062` said it a third time: *"that is a finding to file
rather than a signature to edit from this side."* The contract lens filed that
one, not the implementer, and only because a human was reading.

## Problem

`saffron/report/pr_body.py` assembles a body entirely from the outcome — title,
acceptance criteria, failures, the test diff, disagreements, lens findings,
gates, provenance. **There is no agent-authored prose section anywhere in it.**
The only text an implementer writes that survives packaging is a rebuttal,
which exists only when a lens raised a blocker, and its commit subjects, which
nobody reads as a findings channel.

So a spec asking an agent to *record* something asks for a thing the system
does not have, and every `forbidden` list makes the ask more likely: the
tighter the scope, the more an agent sees that it may not fix.

The moment the implementer knows is the cheapest moment there will ever be. It
is the one that wired the gate and therefore the one that knows which comment
it just falsified. Every finding in items 70–75 came from a review round after
the fact, at review cost, and some did not come at all.

## The shape

An extraction turn, the way `plan.json` already is one (§5.3): the agent emits
a block, the host parses and hashes it *at that moment*, and the hash and the
text travel on the outcome. Never re-read from `/work` — a file left in the
workspace is a claim, not a record.

Then `pr_body.py` renders it under a heading that marks it. Untrusted text from
a cell, so it is clipped to a declared ceiling and passed through `neutralize`
like every other cell-authored string that reaches GitHub.

## Out of scope

**A lens.** §5.5's critics already produce findings and are adjudicated. This is
the *implementer* saying "I saw a thing I was told not to touch" — a different
speaker at a different trust level, and collapsing the two would put unreviewed
cell prose into a table the operator reads as reviewed.

**Writing to `docs/BACKLOG.md` from a cell.** `docs/**` is `forbidden` here and
the backlog is the operator's file. Item 74 says the backlog is `protected` in
`policy.yaml`; **it is not** — `protected` is `DESIGN.md`, `CONTEXT.md`,
`.saffron/**`, `uv.lock`. The real barrier is `touches`, which is item 75's
point, and the correction belongs in the backlog rather than in this spec's
code. File it.

**Acting on the notes.** Nothing reads them but a person. No triage, no
routing, no queue effect, and explicitly no status — that is criterion 5 and it
is the whole safety argument.

**`saffron/gates/**`.** Forbidden. If the outcome cannot carry the field
without a gate change, that is a finding to file — and this time the spec you
are running is the one building the place to file it. Put it there.

## Notes for the agent

**On this spec's own mutants.** Two criteria declare a `mutant`, and they are
the first in this repo to do so — everything item 71 built has until now run on
nothing. You do not see them: `agents/context.py` hands you `witness` and
`claim` and never `mutant`, deliberately, because a mutant you could read is a
mutant your test could be written to catch and nothing else.

Both name a literal this spec dictates rather than code you are about to write,
because that is the only text a mutant can pin before the code exists. So:
`### Notes from the implementer` is the exact heading, and `_NOTES_LIMIT = 4000`
is the exact ceiling declaration. Each must appear **exactly once** in
`saffron/report/pr_body.py` — a `find` matching twice applies nothing and the
gate lands `skip`, which costs the run its only real exercise of the mechanism.

The three criteria without a mutant have none for the same reason inverted:
their claims are about behaviour whose text this spec cannot predict. That is a
limitation worth knowing rather than one worth hiding.

**A ceiling, named.** The prompt withholds mutants, but this spec file is in the
worktree you are working in, and `.saffron/**` is forbidden to *write*, not to
read — `forbidden` is the `scope` gate reading a diff, and it says nothing about
reads. That is `docs/BACKLOG.md` item **80**, filed with this spec. Do not go
looking. If you do read it, say so in your notes — which is, after all, the
channel this spec exists to build, and the datapoint that moves item 80 to
tier 1.
## Acceptance criteria

- [ ] An implementer's notes reach the pull request body under a heading that says whose they are and that nobody has adjudicated them. The operator must be able to tell this text from a lens finding at a glance: a finding has been anchored to the diff and carries a severity, and this has neither.
- [ ] The notes are cell-authored text, so they are clipped to a declared ceiling and neutralized the way every other cell-authored string in this renderer already is. An agent that can write prose into a pull request body can write a screenful of it, or an `@name`, or a `Fixes #12`.
- [ ] The notes are extracted and hashed at the moment they are produced and carried on the outcome, never re-read from the cell's workspace mount. A file left there is a claim, not a record — the plan artifact is the precedent and the reason is the same one.
- [ ] A task that produced no notes renders exactly the body it renders today. The channel is new and every prior task has nothing to put in it, so an empty one must not add a heading over nothing.
- [ ] Notes never reach a status. No gate result, no verdict, no acceptance box is written from them, and nothing in the body's own summary line changes because they exist. `SA-0044`'s reasoning applies unchanged: an agent that can write prose can write prose that reads like a pass.