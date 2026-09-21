---
id: b-d5d290
title: A new name is checked against the vocabulary by nobody, so four collided in one branch and three were found after the code shipped
status: open
tier: 3
by_hand: false
filed: 2026-09-20
specs: []
prs: [393]
commits: []
cites: [§4.6]
related: [b-606ea3, 65, 72, 170]
---

## Problem

Found 2026-09-20, building the record on git refs (item 170, PR #393). Four
names in one branch collided with something the tree already held. One was
caught before the code was written.

**"event".** The record's entries were called events. `saffron/events.py` owns
that word for the `events.jsonl` stream `saffron watch` tails. The design's §8
exists to keep the two apart. Caught while writing the plan, so no code carried
it.

**`records/`.** `saffron/record/` was added beside the dev-only `records/`
package. `records/load.py` already defines a class `Record`. Caught by a peer
session after Task 1 had committed.

**"index".** The folded ledger was called the index throughout the design,
eight code sites and the pull request body. `CONTEXT.md` §8 gives **Index** to
the static page an operator reads at 06:30. `saffron/cli.py` printed both
meanings seventy lines apart. Caught by a review after the branch shipped and
the pull request was open.

**"projection".** Proposed as the fix for "index", and worse than it.
`DESIGN.md` §1.4, §4.6 and §9 give that word to the RDF graph.
`saffron/projection.py` is the module that emits one. **b-606ea3 is already
open** on the same word having no glossary entry. Caught by the operator before
it landed.

**The check exists and reads the wrong half of the vocabulary.** The `terms`
gate's `AVOIDED` map (`.saffron/gates/prose.py:146`) holds seven hand-written
phrases: `sandbox`, `ticket`, `work item`, `the denylist`, `soft fail`,
`self-heal`, `auto-fix`. Each maps a forbidden spelling to the term that
replaces it. That catches a writer reaching for the wrong word for a known
concept. It cannot catch a writer taking a word the vocabulary already gave to
something else. It never reads the defined headwords. `CONTEXT.md` defines
**86** of them.

Three of the four collisions were between a module or package name and a
defined term. That is the cheap case. `saffron/record/`, `saffron/projection.py`
and `records/` are all greppable, and so is every headword.

**This is not a style question.** `CONTEXT.md` is what
`saffron/agents/context.py` injects into a cell per phase. A word meaning two
things in the tree means two things in the prompt. The flywheel's middle bucket
(§8) is the instruction surface that gets sharper over time. Item 65 and item
72 are the same shape one layer down: a closed set living in one place, and a
guard that cannot fire.

## Done looks like

A check that reads `CONTEXT.md`'s defined headwords, not only its `_Avoid_`
lists, and refuses a new name that takes one.

The minimum that would have caught three of the four: every new top-level name
under `saffron/`, `records/`, `harness/` and `ontology/`, compared against the
86 headwords and against the other packages' names, before the first commit.
Package directory, module basename, exported class. The `terms` gate is
advisory, so this rides it or a prek hook rather than blocking a cell.

The harder half is prose, where "index" landed. A headword used for something
that is not its definition. Two approximations. A headword in a
`docs/superpowers/specs/` document or a new module docstring resolves to its
`CONTEXT.md` meaning. A new noun phrase repeated across a document is a
candidate headword nobody defined. Both are heuristics. The gate is advisory,
which is the right side to err on.

`AVOIDED`'s seven entries are hand-maintained. The headwords are generated from
`ontology/factory.ttl`. Whichever way this is built, it reads the generated
side. Otherwise it becomes the second hand-maintained list this item exists to
complain about.

## Record

**Filed 2026-09-20** from PR #393's two-axis review, which found "index" after
the branch shipped, and from the operator catching "projection" before it
replaced "index".

`by_hand: false`. The gate and its rules are ordinary work for a cell. The
`CONTEXT.md` entries a fix wants are separate items already: b-606ea3 for the
emitter's four words, and item 170's §11 for the record's own.

Not filed as a `terms` gate defect. The gate does what it was built to do. What
is missing is a second rule, and its shape belongs in the design record for
`prose` and `terms` (`docs/superpowers/specs/2026-09-16-prose-ratchet-design.md`).
