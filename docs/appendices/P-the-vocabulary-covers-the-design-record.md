---
id: P
title: "rev 20: the vocabulary covers the design record"
revisions: [20]
question: "Should the appendices have been ADRs? No — and the phrase that kept the question alive was a summary of two verdicts that nobody decided"
---

Three sessions in a row asked whether `DESIGN.md`'s appendices should be ADRs. The
answer stayed no, and the third asking found the sentence that made the question
worth repeating.

**The finding is a phrase, not a design.** `DESIGN.md`'s status line said
"`ontology/` stays what §9's v2.5 says it is: a completed project." Two verdicts
sit behind that. `ontology/RATIONALE.md` closed **the emitter** — five queries,
five SQL equivalents, don't build the ledger→RDF projection — and Appendix O closed
**§1.4**, whether shapes control execution, on a spike that answered *no* on two of
four questions. Neither closed the vocabulary to growth, and the vocabulary had
never stopped growing: rev 19 made it authoritative for the closed sets and gave it
a generator, and backlog item 52 queues `TaskState` and `InFlightState` for it.

The shorthand read as a wider decision than either verdict made, and it did the
thing a wrong summary does — it stopped work nobody had decided to stop. This is
the same family as Appendix G's "Docker": a form of words standing where a decision
was never taken. It is not the same defect, and the difference is worth a number.

57. **A summary of two decisions is a third decision, and nobody made it.**
    "Don't build the emitter" and "shapes do not control execution" are both true
    and both narrow. Compressed to "a completed project" they became a claim about
    scope that neither verdict supports, sitting in the status line where it is
    read first and cited most. A summary is lossy in a direction — toward the
    general — and the general version is the one that gets enforced.

**What changed.** `CONTEXT.md` §11 had just named the genres a decision here is
recorded in, and nothing carried them: the file's own architecture is that the
vocabulary is authoritative for its closed sets, and `CONTEXT.md` §11 sat outside
it. `factory:Principle` and `factory:RevisionAppendix` now exist, `PrincipleShape`
and `RevisionAppendixShape` read them, and `ontology/design_record.py` parses the
appendices into that graph and renders the principle index above from it.

**Two of `CONTEXT.md` §11's five genres are deliberately absent.** `EvidenceRecord`
and `SpikeVerdict` have no shape or query reading them, and a term whose only
reader is an `rdfs:comment` is what `tests/ontology/test_no_dead_terms.py` deletes
— *"cheap to fake. Delete it; do not comment it."* Appendix O measured the full-`CONTEXT.md`
expansion at roughly thirty terms and said coverage is downstream of readers, not
independent of them. That holds here: these two join when something reads them.

**The direction is the opposite of `render.py`'s, and that asymmetry is the point.**
A closed set is a decision the vocabulary owns, so `CONTEXT.md` renders from the
`.ttl`. A principle is prose an appendix owns, so the graph is parsed *from*
`DESIGN.md` and only the index renders back. Nothing writes prose into an appendix.

**What the emitter's status is now.** Deferred, with the revisit clause
`RATIONALE.md:22` already carried. Not finished, not refused — asked again when
reconstructibility has to be enforced continuously rather than spot-checked.

