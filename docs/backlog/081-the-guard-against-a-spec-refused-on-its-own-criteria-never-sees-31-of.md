---
id: 81
title: The guard against a spec refused on its own criteria never sees 31 of 53 specs
status: done
tier: 1
specs: [SA-0001, SA-0011, SA-0015, SA-0016, SA-0021, SA-0060, SA-0063]
prs: []
commits: []
cites: []
related: [82]
---

## Problem

**Status: the diagnosis is wrong, the fix landed anyway, 2026-09-08.** The
ordering claim below does not hold and did not hold when this was filed:
`scheduler.py:687` is the criterion-path check and the `depends_on` loop is at
697, so the dependency is decided *after*, not before. Measured by planting
`saffron/nowhere/invented.py` in each spec's first checklist box in turn and
reading what the queue refuses it for — of the **30** specs whose criteria
`_criteria_texts` reads from the markdown checklist, **28 report the
criterion-path refusal**. `SA-0016`, named below as a spec the guard cannot
reach, is among the 28: it is caught. The remaining two are probe-dependent
rather than a second class — `SA-0021` stops on an earlier `depends_on`
refusal, and `SA-0001` is not refused at all because its own
`forbidden: saffron/**` reads the planted token as a citation.

**This paragraph first shipped with the denominator wrong, as 32 of which 4
stopped earlier — caught in review of #166.** 32 is the count of specs carrying
a `depends_on`, which is the very coincidence the next paragraph accuses the
original item of. A corrected measurement that reproduces the error it corrects
is worth recording rather than quietly fixing: the number was reasoned from the
population the item named instead of read off the run.

The "53 specs, 31 preempted, 22 examined" figure appears to have counted specs
that carry a `depends_on` (32 of 54 today) rather than specs whose refusal
preempted the check. That is the number a reader would get by reasoning from
the ordering rather than by running it, which is what `CLAUDE.md`'s rule is
about.

What survives is the weaker complaint, and it is real:
`test_no_real_spec_is_refused_on_its_own_acceptance_criteria` reaches the
property only because of an ordering nothing pins, and it asserts something
weaker — that no refusal is a criterion-path refusal — so it goes silently
blind the day the order changes. So the item's **Done looks like** is
implemented as written:
`test_no_real_spec_names_a_criterion_path_its_touches_do_not_cover` runs
`_unmatched_criterion_path` over every spec `discover_specs` finds, with no
ledger and no refusal ordering in front of it, and refuses to pass on a corpus
it did not actually scan.

**Its first version scanned 49 of the 54, and the wording here said 54.** It
was built on `_real_corpus`, which copies `done/` alone — so the specs still
live at the top of `.saffron/specs` were outside it, which is exactly the set a
fresh defect appears in first. Caught in review of #166 and widened; the mutant
is `saffron/nowhere/invented.py` planted in `SA-0060`, which the retired-only
corpus passes blind. The discovery failures are no longer asserted empty
either: a spec that does not parse cannot be asked this question, and item 82's
validator makes exactly one such spec on the branch stacked above this one.


Found filing `SA-0063`, 2026-09-06. That spec shipped with `/work` in an
acceptance claim; `_unmatched_criterion_path` reads it as a path token, no
`touches` pattern of that spec matches it, and **a spec refused on its own
acceptance criteria never runs.**

`tests/test_scheduler.py::test_no_real_spec_is_refused_on_its_own_acceptance_criteria`
is the test written for exactly that class — its docstring names `SA-0011` and
`SA-0016` as the two it memorialises — and it passed throughout. Measured by
reintroducing the token and running both: the queue smoke test fails, that one
does not. What caught the defect was `test_saffron_queue_smoke_reproduces_this_
repos_measured_queue` asserting an exact refusal *count*, which is luck: it
fires only when the number moves, and it would have said nothing had the same
defect arrived in a spec already being refused for something else.

**The refusal ordering is what blinds it.** A `depends_on` no `MERGED` task
satisfies is decided before `_refuse` reaches the criterion-path check, and the
test supplies no ledger — deliberately, so that "nothing is filtered before
`_refuse` runs and every spec reaches it". Every spec carrying a `depends_on`
therefore refuses on the dependency and stops. Measured over the corpus the
test itself builds (whole `done/` moved to top level): **53 specs, 31 preempted,
22 examined.**

The docstring states the blindness without noticing it: *"a `depends_on` refusal
is the expected shape here, because the corpus is one long dependency chain with
no tasks behind it; a refusal on anything else is the bug."* It is the expected
shape, and it is also the thing that stops the check from ever running. So the
test grows blinder as the corpus grows: every chained spec added is one more it
cannot see.

`SA-0011` declares `depends_on: []` and is examined. `SA-0016` declares
`SA-0015` and is not — one of the two specs the test exists to remember is
outside what it can reach.

**Done looks like** the property asserted directly rather than through the queue:
`_unmatched_criterion_path` over every spec `discover_specs` finds, with no
ledger, no `gh`, and no refusal ordering in front of it. That is what the test's
name already promises, and it is one loop. Keep the queue-shaped test for what
it does cover — the ordering is what makes it blind, not the corpus, so a fixture
that satisfies every dependency would work too and would cost more to maintain
than the property is worth.
