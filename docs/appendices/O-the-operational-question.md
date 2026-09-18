---
id: O
title: "rev 18: the operational question"
revisions: [18, 19]
question: "Is there an *operational* case for the ontology, beyond the analytical one `RATIONALE.md` closed? Rev 19 ran the spike and closed it — *The result*"
---

`SA-0001` shipped and answered the question it was asked. Five queries, five SQL wins, don't build the emitter (`ontology/RATIONALE.md`). That verdict stands, and Appendix B principle 10 is what it is an instance of.

It also raised a different question, which the RATIONALE did not test and cannot settle: **the queries were the analytical case for the ontology. Is there an operational one?**

### What makes it worth asking now

Three things, none of which existed when §1.4 was written.

- **The vocabulary found three defects in this document.** `size` blocking at the wrong tier (Appendix B), `gate_results` and `findings` being one assertion shape (§4.6), and — building it — that `CONTEXT.md` §6 and §3.3 closed the terminal-state set two different ways while `session.py` wrote a tenth state neither called terminal, `tasks.state` closes nothing at all, and `attempts.phase` holds states rather than phases. A modelling exercise that keeps finding real defects is producing something, whatever the queries say.
- **`ontology/` is now a gated surface.** The `shacl` gate makes the shapes operational *as a gate*, which is the weakest useful sense of the word and is already built. Nothing in §1.4 forbids it: the shapes validate an artifact, not a state transition.
- **Prior art.** Zhang et al., *Toward Effective and Reliable LLM Agents via Dynamic Ontology* (arXiv 2608.22974), whose framework is called OaK — ontology-as-a-kernel — builds a task ontology as an executable kernel and reports gains on three agent benchmarks. Its load-bearing sentence is architecturally ours: *"Once frozen, the kernel is the only channel through which the agent reaches the data. It cannot name a concept or invoke a computation the kernel does not declare."* That is §2's line, reached from the effectiveness side rather than the isolation side.

### The two positions

**For.** The control plane's rules are currently Python that runs and prose that does not. A declarative form makes them inspectable, checkable against each other, and testable without executing a scheduler. The conflict set, `elevate_on`, the terminal-state distinction and the refusal predicate (§4.2.1) are all set containment, and set containment is what shapes are for.

**Against, and it is the stronger half.** Saffron already has an enforceable contract between the model and what it may do, and it is not made of triples: the gate contract, `allowed_tools`, the proxy allowlist, `touches` and the `scope` gate. OaK's kernel is a *reimplementation* of that boundary for agents that lack one. Re-expressing controls that already work, in a language with no runtime here, buys inspectability and costs a second source of truth — and §4.6's first rule exists because divergence in an audit trail is worse than either store alone.

There is also a cost that has to be stated rather than discovered: **an ontology that controls execution needs the emitter the RATIONALE said not to build.** That is not incoherent — it would be built for a reason the RATIONALE never tested — but the reason must be the new one, argued on its own evidence, and not the analytics case arriving through a side door.

### What full SDLC coverage would take, measured

Extending the vocabulary to the whole of `CONTEXT.md` means roughly thirty terms — cell, container, cell runtime, worktree, mirror, batch tree, index, queue line, conflict set, extraction turn, plan checkpoint, refusal, no-progress, anchored, merge train, preflight, bucket, promote — that no query or shape reads, and that no §4.1 table projects from. Under the dead-term test they are deleted; without it the ontology is the isomorphic re-encoding §4.6 exists to forbid, one level up, re-encoding a glossary rather than a schema. **Coverage is downstream of this decision, not independent of it.** Decided one way the terms acquire readers; decided the other they are decoration, and the dead-term test is right to say so.

### The decision, and when it gets made

Not by argument. §1.4's bullet **stands for v1**, and this appendix is what reopens it — the same shape as Appendix G, which named a product only after a spike returned four assertions.

The cheap experiment is available and does not exist yet: §4.2.1's scheduler is decided in full and unbuilt, and its refusal predicate is pure set containment. Build it twice — once as the Python `intake` already needs, once as shapes over a hand-authored graph of in-flight tasks — and compare:

1. Does the shape form state a refusal the Python form leaves implicit?
2. Does either catch a case the other misses, on the same fixtures?
3. What does the graph cost to keep current, per scheduled task?
4. Can the shape form be read by someone who has not read the Python?

A yes on 1 and 4 with an acceptable 3 reopens §1.4. Anything else closes it, and `ontology/` stays what §9's v2.5 already says it is: a completed project.

### The result — the spike ran on 2026-09-04, and the rule closed it

Answers and reasoning: `docs/superpowers/plans/2026-09-02-ontology-authoritative.md`, "Phase B — the answers, and the verdict". Artifacts and scoring: `docs/evidence/2026-09-04-refusal-predicate-two-arms.md`.

**No on 1, no on 4.** The shape arm states no refusal the Python leaves implicit, and the inverse holds: `_unmatched_criterion_path` carries a `forbidden` carve-out §4.2.1 never states, so an arm written from the prose — which this experiment requires — cannot contain it. The rule needs a yes on 1, so that closes it alone. On 4, the readable shape gets `**/size.py` wrong and the correct one is a nine-deep nested `REPLACE` rebuilding `scope._to_regex` inside a SPARQL literal.

**Two corrections this appendix should carry.** *"Its refusal predicate is pure set containment"* is wrong — four of the eight refusals are glob matching. And the spike's own first write-up claimed glob matching was inexpressible in SHACL; review falsified that, and the claim is retracted. It is expressible, at the cost named in question 4.

**One finding for the other side of the ledger.** This appendix's "for" case opens with three defects the vocabulary found in this document. There is a fourth: `MERGE_TRAIN` is a state §3.3's diagram shows a task entering and `scheduler.py` reads twice, and it is in neither `CONTEXT.md` nor `ontology/factory.ttl`.

56. **A negative result answers the question it tested, and no other.** `SA-0001` proved the queries were not worth an emitter. It proved nothing about whether the vocabulary is worth executing, because it never asked — and the honest response to "then let's make it operational" is a different experiment, not a re-reading of the first one.

---

