---
id: 152
title: A witness node id is checked by nothing until a cell has been paid for, so a spec can name a test that does not exist
status: done
tier: 2
filed: 2026-09-16
closed: 2026-09-16
by_hand: true
specs: []
prs: [290]
commits: []
cites: [§5.4.1]
related: [82, 83, 124, 153]
---

## Problem

**Tier 2.** By hand: the check belongs in `tests/test_queued_specs.py` and the
rule it makes mechanical is in `docs/agents/issue-tracker.md`, both outside what
a cell can land.

`tests/test_queued_specs.py` has five tests over the live queue — every spec
parses, ids are unique, none is refused on its own text — and **none of them
reads a `witness`**. So a queued spec may name a test node id that does not
exist, and nothing says so until that spec's cell runs and `criteria` reports it,
after the cell has been paid for.

`docs/agents/issue-tracker.md` already states both halves of the rule in prose:

> A `preserves: true` witness must already exist at `base` (use `git grep` for
> the test name). […] A witness must fail with the source reverted, not merely
> be missing at base.

Both are mechanically checkable over the queued corpus, and neither is checked.

Found writing `SA-0093`–`SA-0095` on 2026-09-16 (#290). `SA-0094` was written
naming `test_create_network_names_the_holder_when_the_subnet_overlaps` as a
`preserves` witness. No such test exists — the real one is
`test_an_overlapping_network_names_the_one_already_holding_the_subnet`. It was
caught by grepping on a hunch before the spec review ran, which is the only
reason it is not an example rather than a near miss.

The spec review does check this, by hand, every time: all three reviews of #290
verified each `preserves` witness at `base` and reported it under check 3. That
is a human-and-model check standing in for a `grep`, run once per spec, against
a corpus a test could read in full in under a second.

There is a second failure this closes, which the by-hand check cannot reach at
all. `SA-0095`'s review flagged it: a spec's `preserves` witness can be valid
when the spec is written and invalid by the time its cell runs, because an
earlier spec in the same chain renamed the test. `tests/test_session.py` is
inside both `SA-0093`'s and `SA-0094`'s `touches`, and neither protects
`SA-0095`'s two witnesses by name. A review at authoring time cannot see that;
a test that runs on every commit can.

## Done looks like

A test in `tests/test_queued_specs.py` reading every queued spec's `acceptance`
and resolving each `witness` against the live suite: a `preserves: true` witness
names a test that exists, and a non-`preserves` witness names one that does not.
Resolution by collection rather than by `git grep`, so a node id that is
well-spelled but unreachable — wrong file, wrong class — fails too.

Both halves matter and the second is the less obvious one: a non-`preserves`
witness that already exists at base is the case `criteria` and `revert` exist to
refuse, and catching it at `make check` costs nothing where catching it in a
cell costs an attempt.

## Record

**Filed 2026-09-16** from writing #290's three specs and reading their reviews.

**2026-09-16, done, by hand.** `tests/test_queued_specs.py` resolves every
queued witness. A `preserves` one must be a node id in the suite's collection,
taken with the argv `.saffron/gates/tests` uses. Any other must have no `def` in
its file **at the commit that last edited the spec**, not at HEAD. That is the
one departure from this record's "Done looks like", and it is forced: the cell
implementing a spec writes its witness, and from then until the spec retires
to `done/`, HEAD holds it. A HEAD check would fail that cell's `tests` gate
and `main` between the merge and the retirement. Absence is read with
`git grep`, not by collection, because a checkout per spec costs too much, and
for absence a grep is the stricter reading. An uncommitted spec edit is read
against the working tree. CI now fetches full history, and a shallow clone
fails its own test instead of passing quietly.

Measured against planted defects: this record's own misnamed `SA-0094`
witness, the right name in the wrong file, and a new-behaviour witness naming a
test that exists all fail. A cell-written witness under a committed spec
passes. The first draft's `git grep -E` spelled whitespace `\s`, which ERE
reads as a literal `s`, so the committed-tree lookup never matched and the
check passed everything. The planted cases missed it because they all went
through the uncommitted branch. A test now pins the lookup.
