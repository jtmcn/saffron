---
id: B
title: "rev 3: the factory ontology"
revisions: [3]
question: "Is a factory ontology worth building? (`SA-0001`, §4.6)"
---

`SA-0001` defines a PROV-O/EARL vocabulary for Saffron's own run record (§4.6). Two principles it contributes, both generalizable beyond ontologies:

10. **A design artifact can succeed by concluding "don't build it."** The spec's deliverable includes a rationale that challenges every one of its queries against a SQL equivalent, and a verdict of "SQL is fine" is a pass. This is the cheapest possible form of that answer. The expensive form is an emitter you maintain for a year before noticing nobody reads it.
11. **Modelling pays before it ships.** Writing down what an *attempt* is in relation to a *gate result* produced two schema criticisms (§4.6) that hold whether or not a triple is ever stored. The output of a modelling exercise is not only the model.

**And one correction the spec forced on the design.** §5.4 listed `size` as always-blocking; §5.6 described it as *becoming* blocking at `risk: elevated`. Both couldn't be true. `SA-0001`, written against the document and reasoning about its own 600-line ceiling, tripped on the contradiction. Resolved in favour of §5.6: `size` is advisory at standard risk, blocking at `elevated`.

That is worth noting for its own sake. The first real spec written against this design found a defect in it — which is the same mechanism as §5.2's plan gate, operating one level up. Specs are a test suite for the design document, and they should be read that way: a spec that is awkward to write is evidence about the design, not about the spec author.

---

