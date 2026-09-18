---
id: T
title: "rev 24: the emitter, reopened on the clause it carried"
revisions: [24]
question: "The emitter reopened on the RATIONALE's own clause: N5's query ran only against fixtures, so no merged change was ever its subject"
---

`SA-0001` answered the analytical question and answered it no. Five queries,
five SQL wins, do not build the emitter (`ontology/RATIONALE.md`). That verdict
stands. The RATIONALE carried one condition that would reopen it, and Appendix P
restated the status as deferred rather than refused: asked again when
reconstructibility must be enforced continuously rather than spot-checked. This
appendix argues that the condition now holds, and it is a different question
from the one `SA-0001` tested (principle 56).

### N5 is asserted for real work and checked only for fixtures

N5 is a numbered requirement in §1: any merged change reconstructible from
stored artifacts alone, expressed as a derivation-chain query so it is checkable
rather than asserted. Q4 is that query. It exists, it is tested, and every input
it ever ran against was written by hand.
`tests/ontology/test_queries.py` builds each task, spec and diff as Turtle text
in the test body. No merged pull request was ever its subject. Q4 therefore
proves that the query is well formed. It proves nothing about any change this
repository shipped.

61. **A check that runs only on fixtures verifies the check, not the subject.**
    Q4 encodes N5 and passes against a hand-authored graph. Passing establishes
    that the query is well formed. It establishes nothing about any merged
    change, because no merged change was ever its input. A requirement checked
    that way is asserted with extra steps.

### What changed since rev 18

Two things, and neither existed when the RATIONALE was written.

- **Backlog item 118, and Appendix Q.** The verdict of record was computed
  inside the container the implementer controlled. Every git-config forgery this
  backlog closed is one instance of that class. An audit trail matters more once
  the thing it audits was, for a period, forgeable from inside.
- **Q4's own header states the win, while arguing the other side.** The
  derivation edges are stated rather than reconstructed from a path template.
  That is what lets a broken chain be absent from the result, instead of
  rendering as a missing file. A break that renders as a missing file is the
  `tool` field one level up. A chain that never linked reads identically to one
  that did.

The second point is the whole argument, and it needs narrowing to survive.
§4.1's foreign keys carry the chain, and plan and diff are file paths rather
than rows. A walk that checks each path exists already tells a missing file from
a present one. What it cannot tell is a present file that is not this task's.
The batch tree is keyed by spec, so a later task of the same spec writes over
the earlier task's plan and diff. The event log still holds what each task
recorded at extraction. An edge stated only when the stored file matches that
record drops the overwritten chain. The checked walk calls it whole.

### The decision rule, named before the run

Appendix G named a product only after a spike returned four assertions.
Appendix O named its rule before running and then honoured the answer. The same
shape applies here, and the claim is falsifiable.

Build the projection from the whole ledger, then run Q4 over it across the
merged history. The comparator is the checked walk: §4.1's foreign keys, with
every stored file checked to exist. The claim is that Q4 drops at least one
merged pull request the checked walk reports as whole. A missing file cannot
carry the claim, because the checked walk sees one too. A task that cannot be
tied to its own events counts for neither side. A single instance carries it.
Zero instances across every merged pull request refutes the operational case, as
the queries refuted the analytical one. The emitter then returns to the drawer
with a third negative result. That answer is worth the weekend on §9's own
logic, whichever way it lands.

A positive result is narrower than it will read. Every instance comes from the
record check, and a SQL walk given the same check finds the same set. So one
instance shows that N5 needs that check. It does not show the check needs a
graph. The emitter keeps its place only if Q4 over the projection stays cheaper
to hold than the SQL walk with the check added. That is the RATIONALE's own
standard.

### Backlog item 170 bounds the question

Item 170 makes commits on `refs/saffron/*` the authoritative record and the
ledger an index folded out of it. It also moves artifacts to a store named by
content hash. No later task can then overwrite an earlier one's plan or diff,
and the record carries a hash for every artifact, the diff included. The one
case this rule can find stops arising once item 170 lands.

So the rule measures history recorded before item 170, and it runs once over
that history rather than at every batch end. That makes it urgent rather than
moot. Item 170 has still to decide whether the tasks already recorded are
migrated or abandoned, and abandoning them removes the evidence. Each break the
rule finds is a chain the old layout already lost, which is an input to that
decision. A standing N5 check belongs to the record item 170 builds, not to the
batch tree it replaces.

The same item reverses §4.6's first rule, which the next section cites. The
projection's derivation from the ledger holds either way. Once the ledger is an
index, the projection is derived from a derivation.

### What this costs, stated rather than discovered

- **§4.6's first rule.** Divergence in an audit trail is worse than either store
  alone. The projection is therefore derived and never authored, rebuilt from
  the ledger rather than updated in place. It is validated against the shapes
  as it is built, since the `shacl` gate reads only the tree. Q4 runs over it
  as a check on real history, rather than beside it as a test.
- **A graph library becomes a runtime import.** `pyproject.toml`,
  `ontology/render.py` and `ontology/design_record.py` each state that nothing
  under `saffron/` imports one. The emitter falsifies that sentence in three
  places. All three are forbidden to the spec's cell, and the dependency move
  needs the protected `uv.lock`, so the operator does both at merge.
- **Coverage stays downstream of readers.** Appendix O measured the full
  `CONTEXT.md` expansion at roughly thirty terms and ruled that coverage follows
  readers. The emitter adds one reader for the terms Q4 already names. It
  licenses no other term, and `tests/ontology/test_no_dead_terms.py` still
  governs.

### What this does not reopen

§1.4's bullet stands. The factory ontology describes the run record. It never
controls execution, no scheduling decision reads a triple, and the shapes gate
no state transition. Appendix O's rule closed that question on 2026-09-04 on
evidence, and this appendix touches none of that evidence.

The operator states an intent to revisit it, on grounds of growing complexity in
the control plane. That intent is recorded here and decides nothing. Appendix O
is explicit that an ontology controlling execution needs this emitter. It is
equally explicit that the reason must be argued on its own evidence, rather than
arriving through a side door. Naming the intent in advance is the opposite
of the side door, and the bullet still moves only on a measured result.

What the emitter does supply is the instrument. The 2026-09-04 spike answered
its question 3, the cost of keeping the graph current per scheduled task, from a
hand-authored graph of in-flight tasks. A projection built from the ledger
measures part of question 3 on real rows, as a byproduct of work done for N5.
It builds once over history rather than per scheduled task, so it prices a
rebuild and not the per-task upkeep.
Questions 1 and 4 are what closed the spike, and neither is answered by this. On
question 1 the cause was recorded and is narrower than it reads: the shape arm
stated no refusal the Python left implicit, because `_unmatched_criterion_path`
carries a `forbidden` carve-out §4.2.1 never states. The prose was incomplete,
not the shapes. Anyone reopening §1.4 starts there, with §4.2.1 first.
