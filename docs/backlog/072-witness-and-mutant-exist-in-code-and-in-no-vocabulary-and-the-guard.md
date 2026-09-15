---
id: 72
title: '`witness` and `mutant` exist in code and in no vocabulary, and the guard for that reads the vocabulary'
status: done
tier: 2
specs: [SA-0045, SA-0056, SA-0057, SA-0058, SA-0063, SA-0064]
prs: []
commits: []
cites: [§5.4.1]
related: [65, 69, 71, 74]
---

## Problem

**Status:** **done**, by hand, 2026-09-07. `factory:witness` is declared at
`blockingWhenElevated` and named by `SizeTierShape`; `mutant` and `witness` are
`CONTEXT.md` §4 entries and deliberately *not* vocabulary terms, because
`test_no_dead_terms` rejects a class no shape reads. The guard now reads
`saffron/gates/core/` off disk and was run against the unfixed tree, where it
names `['witness']` — and declaring the triple then made `test_shapes` name
`['witness']` too, which is `CLAUDE.md`'s promised guard firing for the first
time on the case it was written for.

**Tier 2.** Found reviewing `SA-0056` and again reviewing `SA-0058`, 2026-09-06.

Item 69's chain added a core gate and a term, and neither reached
`ontology/factory.ttl` or `CONTEXT.md`. Measured:

```
vocabulary declares:  census committed criteria integrity revert scope secrets size
saffron/gates/core/:  census committed criteria integrity revert scope size witness
```

`secrets` is the ordinary direction — specified in the vocabulary, not yet
built. **`witness` is the first core gate in the other direction: built, and in
no vocabulary.** `mutant` is the same for a term: `CONTEXT.md` is authoritative
for meaning and does not contain the word, though `DESIGN.md` §5.4.1 introduces
it in bold as a defined term and a module is named after it.

**The guard cannot fire, and `CLAUDE.md` promises it will.** That file says a
new core gate "needs a blocking level in `factory:CoreGateBlockingShape` … and
a test names the shape and the file when you forget."
`tests/ontology/test_shapes.py` does exactly that — over
`vocabulary.subjects(rdf:type, factory:CoreGate)`. A gate absent from the
vocabulary is absent from that set, so the test passes and the promise is false
for precisely the case it exists to catch. `CoreGateShape`'s `sh:in` does not
reject it either, for the same reason.

Beyond the ontology: `session._blocking` treats any gate outside
`advisory_gates` as blocking at every tier, so an unvocabularied core gate
defaults to the strictest level with nothing to catch it — which is half of
item **71**.

**Why nobody did it, and why that is the real finding.** This is the third
occurrence of one shape: *the spec that introduces a term is `forbidden` from
the vocabulary that would define it.*

- item **65** — the four batch stop reasons; `ontology/` forbidden to `SA-0045`
  and to every spec above it
- **`mutant`** — flagged reviewing `SA-0056`, forbidden there and to `SA-0057`
- **`witness`** — forbidden to `SA-0057` and to `SA-0058`

Each `forbidden` list was right: a cell inventing vocabulary while implementing
against it is how a term comes to mean whatever the implementation needed. The
defect is that nothing then owns the entry, and three chains have now ended
with a term the code uses and the glossary does not have.

**A structural detail that decides who can fix it.** `ontology/` is *not* in
`policy.yaml`'s `protected` list, so a cell may edit the vocabulary — but
`CONTEXT.md` is protected, and it is *generated* from the vocabulary by
`ontology.render`. `test_generated_surfaces_are_current` fails if the two
disagree. So the two halves must move together and one of them a cell may not
touch: this is an operator's edit, or a spec that declares `ontology/**` in
`touches` and hands the render to the operator. Worth deciding once rather than
per term.

**Done looks like** `factory:witness a factory:CoreGate` with a blocking level
in `factory:SizeTierShape` — it moves with the tier exactly as `size` does, and
it is the second such gate, so that shape's comment calling `size` "the one
core gate a risk tier moves" needs amending too — a `mutant` entry in
`CONTEXT.md`'s vocabulary, `uv run python -m ontology.render` re-run, and the
closed-set tests green.

**The pattern, decided.** Of the two arms — either the vocabulary stops being
`forbidden` to the spec that introduces a term, or every such spec carries a
follow-up filed when it is written rather than discovered three pull requests
later — the first is structurally unavailable, and that is measured rather than
argued. `ontology/factory.ttl` is neither `protected` nor in
`integrity.gate_config`, so a cell may edit it; but the change is not complete
until `ontology.render` rewrites `CONTEXT.md`, which *is* `protected`, and
`protected_touch_refusal` runs at intake (`saffron/cli.py:441`). A spec
declaring the regeneration is refused before a cell starts; one omitting it
fails `scope` on an out-of-scope file, or lands a vocabulary its own derived
surfaces contradict and fails `test_generated_surfaces_are_current`. That
test's docstring already said so, and nobody had read it back to this item.

So the second arm: `docs/agents/issue-tracker.md` now requires a spec that
introduces a term to file its vocabulary follow-up, marked **by hand**, in the
same commit as the spec.

**One term left undecided, on purpose.** `notes` — item **74**'s channel,
shipped in `SA-0063`/`SA-0064` — is in no vocabulary either. It is not a gate,
and `DESIGN.md` does not bold it as a defined term the way §5.4.1 bolds
**mutant**, so declaring it here would be the vocabulary-invention the
`forbidden` lists exist to prevent. It is a candidate, not an omission; decide
it when a document defines it.

**Two brittle guards found while closing this**, both the same shape one level
down — a test pinned to the membership it checks. `test_render`'s fixture
asserted `` `revert`, `probe`. `` , naming the last core gate by hand, so
declaring a ninth broke it; it now derives the tail from `render.members`. And
`ontology.render` rewrites a closed set's enumeration but not the prose after
it, so adding `witness` left a 90-character line in a file whose longest was 87
— cosmetic, hand-rewrapped, and worth knowing before the next set grows.
