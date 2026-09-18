---
id: F
title: "rev 7: what a read-through found"
revisions: [7]
question: "Nine more from an end-to-end read-through, including `coverage` blocking and advisory in the same document"
---

`SA-0001` and `CONTEXT.md` each found defects by being *written against* this document (Appendix E, principle 25). Rev 7 is the cheap version of the same move: reading the document end to end against the vocabulary, writing nothing. It found nine things, and the two most expensive of them had survived an adversarial review and five revisions.

**Three contradictions the document was already carrying.**

- **`coverage` was blocking and advisory at the same time.** §5.4 argued at length that a blocking coverage gate rewards assertion-free tests; §5.6 then made it blocking at `risk: elevated`. Resolved in favour of §5.4, at every tier. This is the identical defect Appendix B caught in `size` — in the same sentence — and it survived because only half the sentence was fixed.
- **"Bounded on three axes", followed by five rows and the words "Five, not three."** `CONTEXT.md` said five. A residue of rev 5, and the kind of thing the companion document exists to catch.
- **`revert` broke §2.1's boundary as stated.** §2.1 said any core gate needing to *execute* something belongs on the repo side; §5.4 said `revert` is "the one place core reaches into the repo's toolchain." The rule is now stated so the exception fits inside it: **core invokes declared gates, never tools.**

**Six defects that would have shipped.**

- **Baseline subtraction was keyed on `line`.** The worst of them. Any diff that is not append-only shifts pre-existing failures, so untouched failures would have read as new and the repair loop would have spent attempts on code the task never wrote — the §7 countermeasure defeating the exact failure it was built for. Identity is now `(gate, file, code)`. The same fix rescues no-progress detection, which was comparing bytes across a set whose line numbers move every attempt, and would therefore never have fired.
- **Finding anchoring would have zeroed out lens #3.** Blast radius is *what else calls this*, so its findings point at unchanged lines; a hunk-only reconciler drops them all, silently, and the drop-rate diagnostic would have blamed the prompt. A second anchor admits a line that names an identifier the diff changed.
- **REBUT had no edge out of failure.** One attempt, gates re-run, and nothing in §3.3 said what happens when the re-run is red. It is `EXHAUSTED`.
- **`saffron gc` ran a night behind itself.** `ORPHANED` was inferred from a 24h-stale `updated_at`, but a cell killed at 06:30 is twelve hours old at the next batch start — so nothing was ever freed on the cycle that killed it. The supervisor now stamps `ORPHANED` at death and the delay runs from there.
- **`--cpuset-cpus` pins into a hybrid core list.** A cell landing on efficiency cores runs its gates several times slower than its siblings, reintroducing per-cell timing variance — the flaky-gate mode that bullet was written to remove. P-cores only, enumerated at preflight.
- **`SCOPE_REVIEW` writeback had no home.** "Written back into the spec file" meant either an unattended write to a remote `main` (forbidden by N1) or a `spec_sha` move that invalidates the task ratification just unblocked (§4.1). It now rides the task's own branch as its first commit, which needs neither exception.

**Two scope corrections**, both applications of rules the document already states to places it had not applied them: the scheduler's conflict sets, round-robin and stacking are deferred to v2 (§4.2, §9), because at a two-deep queue they arbitrate contention that never arrives; and §9 gains a third rule.

Four principles, and the first two are the ones that generalize past this system:

27. **An identity that includes a coordinate the change moves is not an identity.** Line numbers, byte offsets, array indices, row numbers — anything the diff renumbers is a display field. Key on what survives the edit.
28. **A reconciler tuned to one producer silently disables another.** Filters fail closed and leave no error, so the symptom shows up attributed to whatever they filtered. Every drop rule needs to be checked against every producer that feeds it, not just the one it was written for.
29. **A rule with an unstated exception has been abandoned, not weakened.** §2.1's boundary was false from the moment `revert` was added, and stayed useful only because nobody tested it. Write the exception into the rule and the rule keeps working.
30. **Fixing half a contradiction leaves a contradiction.** `size` and `coverage` were wrong in one sentence; rev 3 fixed one word of it and the appendix recorded a win.

And the method note, promoted into §9 as its third rule: **this pass cost an hour and found more than rev 6 did.** But the two defects at the top of the list — line-keyed identity, hunk-only anchoring — are things a single replayed PR surfaces immediately and no reading surfaces reliably. Rev 8 should not be a document.

---

