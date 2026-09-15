---
id: 82
title: A mutant can pin the text a spec dictates or the text an agent writes, never both
status: done
tier: 1
closed: 2026-09-08
specs: [SA-0063, SA-0064]
prs: []
commits: []
cites: []
related: [69, 83]
---

## Problem

**Status: done, 2026-09-08.** The constraint is stated where an author meets it
— `docs/agents/issue-tracker.md`'s conventions, beside the rest of the spec
format — and `intake.py` refuses at parse a mutant whose `find` text appears in
the spec's body **or in its own claim**: a claim is prompt text by the same
route, `context.witnesses_block` handing it to the implementer and
`criteria_section` to the critic.

Measured against this repo's 54 specs: one refusal, `SA-0063`, which is the
spec this item was written about and the exact mutant it describes.

**Read that number with its denominator.** Only **two** of the 54 declare a
mutant at all (`SA-0063` and `SA-0064`), so the check has fired on the only two
chances it has had. "One refusal in 54" invites a false-positive rate this
corpus cannot support. No length threshold was added, and whether one is needed
is *not* measured: the argument for going without is that a `find` must match
exactly once in its file, so a very short one is already an unusable mutant —
and that argument thins as the text gets longer. A rough count over this corpus
finds dozens of backticked identifier-shaped spans quoted verbatim in a spec
body that would each match exactly once in a file that spec's `touches` covers,
so collisions are not obviously rare. If it starts biting, the tree-aware half
belongs beside `saffron/mutation.py`, which is the module that may read the
repo — `intake.py` deliberately cannot, so it cannot tell a `find` naming text
that already exists at base (disclosing nothing, since the implementer can read
the file) from one naming text the spec invents.

**Corrected in review of #167**, along with two defects that review found: the
check compared a mutant against its *own* claim only, while `witnesses_block`
hands the implementer every claim — a sibling claim disclosed just as well and
nothing refused it; and the refusal removed a spec from `_retired_ids`' credit,
so retiring `SA-0063` to `done/` — the documented next step — would have
stranded `SA-0064`, whose parent it is. A disclosed mutant now raises
`DisclosedMutantError`, which carries the parsed spec, and a retirement still
credits a spec refused on policy rather than on shape.

One consequence worth knowing before the check meets a spec someone is waiting
on: an unparseable spec leaves the scanned set, so its dependents refuse with
*"depends_on X is not among the specs in this directory"* — a dangling
reference rather than an unmerged dependency. `SA-0064` reads that way in the
queue today. The cascade is `discover_specs`' designed shape, but the sentence
points at the wrong fact.


Found writing `SA-0064`, 2026-09-07, after `SA-0063` ran both halves of it.

A `Mutant` names exact text and applies only when `find` matches exactly once.
For a spec that builds code which does not exist yet, the operator writing the
mutant cannot know the text the agent will produce. There are two ways out and
each costs something.

**Dictate the literal.** `SA-0063` did: it mandated an exact heading and an
exact constant declaration so the mutants would match, and they did — *"2 of 2
witness(es) died under their own mutant"*, the first real `witness` verdict this
repo has produced. But the spec body **is** prompt text: `build_system_prompt`
passes it as a substituted `{spec}` value, so every literal a spec pins is a
literal the implementer reads. `SA-0063` went further and named them as
mutant-pinned in its own `## Notes for the agent`, which is the same as handing
the mutants over. Its verdict is therefore sound evidence that the *mechanism*
works and no evidence that the *tests* are honest — a test written to kill a
known mutant is the theater the gate exists to refuse.

**Or pin what the code already determines.** `SA-0064` does: a field that
exists, a parameter that exists, a predicate already written, so the natural
spelling is close to forced and no disclosure is needed to make it match. The
verdict then means something. The cost is that this only works where the change
*edits* existing code. A spec creating something new has no such text to name.

So the mechanism measures honestly where a change is an edit, and measures
itself where a change is new — which is a real limit on the answer item **69**
was built to give, and one nobody would find: the reasoning currently lives in
two spec files' `## Notes for the agent` sections and nowhere a spec author
looks.

**Measured after this was written:** the second option does not work either,
and item **83** is why — a mutant that matches at the base commit kills the task
at baseline. So as things stand an author can have an honest mutant or a
runnable spec, and 83 has to land before this item's advice is usable at all.

**Done looks like** the constraint stated where an author meets it —
`docs/agents/issue-tracker.md`'s conventions, beside the rest of the spec
format — rather than a code change. Worth pairing with one cheap validator,
though: `intake.py` could refuse at parse a mutant whose `find` text appears in
the spec body it is declared in. That is one string search beside `Mutant`'s
existing "not empty" check, and it catches exactly the mistake `SA-0063` made,
which no reviewer caught either — both lenses that read that spec's diff missed
it, and it was found only by reading the agent's own reasoning as it worked.
