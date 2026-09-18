---
id: A
title: "What changed in rev 2, and why"
revisions: [2]
question: "Nine adversarial-review findings on rev 1 — DIAGNOSE proposes `touches`, `coverage` goes advisory, no vote over disjoint lenses"
---

Rev 1 was reviewed adversarially. Nine findings survived scrutiny; all are incorporated above. The ones worth remembering as *principles*, because they'll recur:

1. **A gate that requires the human to already know the answer isn't a gate, it's a tax.** (Hand-written `touches` on bug specs → DIAGNOSE.)
2. **A dependency edge that can only be satisfied by a human action outside the batch will never be satisfied inside it.** (`MERGED` → `READY_FOR_REVIEW`.)
3. **A walking skeleton must contain the hard part.** Rev 1's v0 deferred the gate contract, the artifact, and all isolation — and turned unattended execution on first.
4. **Controls inside the untrusted zone are not controls.** (In-agent hooks and Bash regex denylists demoted to ergonomics.)
5. **Two safety mechanisms that make each other dead code mean you picked one without noticing.** (Abort-on-red vs. baseline subtraction.)
6. **A blocking metric gate teaches the cheapest way to satisfy it.** (Coverage → advisory; `revert` → blocking.)
7. **Resource limits that the runtime doesn't actually enforce produce flakiness you'll misattribute to the model.** (`--cpus` vs. `--cpuset-cpus` + thread env vars.)
8. **Detection without reclamation is not a countermeasure.** (Disk preflight → `saffron gc`.)
9. **A voting rule over disjoint voters never votes.** (Majority-of-lenses → any blocker.)

Rev 1 sections that survived unchanged: specs-in-target-repo, SQLite-for-recoverability, three-axis bounding, host-invoked gates, the critic's "say so if there's nothing" clause, never letting an agent resolve conflicts, and the warning against building the planner first.

---

