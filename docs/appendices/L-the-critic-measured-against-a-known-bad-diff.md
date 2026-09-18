---
id: L
title: "rev 14: the critic, measured against a known-bad diff"
revisions: [14]
question: "The critic built, and measured against a known-bad diff rather than argued for"
---

Appendix K argued from a single review that §5.5's critic is what makes the
loop's output mean anything. Rev 14 builds it and measures it, and the test was
available for free: `SA-0004`'s patch is a real agent-written change that passed
every gate and its own thirty-one tests, and that adversarial review rejected on
three Criticals — all written down before the critic existed.

So the critic's first live run had a ground truth. Nothing was tuned after seeing
its output.

### What it found

- **The net-line-count proxy, as a `blocker`** — the defect that defeats the
  gate's entire purpose, and the most important of K's three.
- **Two things K does not contain**, both true: the failure message hands the
  agent the evasion recipe, and no fixture covers the mixed case. K found the
  defect; the critic found why it stays exploitable.
- **§5.4's omitted `touches` exemption, as a `concern`** — reached from §5.2's
  ratified-spec commit rather than K's "the gate fails its own PR". Same defect,
  independent route.
- **Two more not in K at all**, correctly filed as `note`: an empty-file test
  deletion passing the gate, and an assertion no implementation could fail.
- **Missed**: the `\ No newline at end of file` abort, and the
  `git config diff.srcPrefix` escape — the latter squarely blast-radius, the
  third lens, deliberately not built because no risk tier is wired.

**Drop rate: 0% on both lenses.** Every finding anchored to a real changed line.
No hallucinations on the first honest run — which is the number §5.5's
reconciliation exists to protect, and the one most likely to be bad.

### What that settles, and what it does not

§5.5's design works. A critic given a bounded remit, a fresh session, read-only
tools and an instruction to find the reason a change should not merge produced
findings a careful adversarial review had missed, and produced no invented ones.

50. **A critic and a reviewer fail differently, and that is the argument for
    having both.** The machine critic caught what the human-equivalent review
    missed and missed what it caught. That is not redundancy with a weaker copy;
    it is two different failure surfaces over one diff. §5.5's disjoint lenses
    are the same idea one level down, and the same reasoning says a critic does
    not replace the operator — §11's "human, always" stands.

Two caveats, both volunteered by the implementation rather than found later:

**The lenses are not disjoint enough.** Both filed the `touches` finding, which
means their remits overlap on "code contradicts a written spec". §5.5's
no-voting rule rests on disjointness by construction — *"the schema critic will
never independently corroborate the correctness critic's timezone finding"* — so
an overlap is not a duplicate to deduplicate, it is a prompt defect.

51. **Two lenses reaching the same finding is a fact about the prompts, not about
    the finding.** It reads as corroboration, which is exactly what makes it
    dangerous: a system that treats agreement as evidence will be most confident
    where its lenses are least independent.

**The second lens ran on a smaller model** because $0.83 of budget remained. That
is a confound in every comparison above and it is stated rather than smoothed.

### Where a blocker goes

To REBUT, which §5.6 now describes in the order that ambiguity is settled in:
"confirmed" means anchored, and the critic's `verdict` answers the rebuttal
rather than preceding it. The phase is built and tested against fakes, and
**it has never run against a live model** — no rebuttal, no verdict, and no
gate re-run after a rebuttal has been measured. Appendix J's rule applies to it
exactly as it applied to the repair loop: the path that has never run is the one
your estimate is about.

---

