---
id: E
title: "rev 6: what the vocabulary found"
revisions: [6]
question: "Three defects `CONTEXT.md` found in this document by being written against it"
---

`CONTEXT.md` (Appendix D, item 24) was written against this document. Like `SA-0001` before it, the artifact found defects in the design it was derived from — three, all of which had survived four revisions and an adversarial review:

- **Accept rate could not appear in the batch header.** §6 claimed it; the definition — merged over completed — made the impossibility plain. Nothing is merged when a batch ends, because merging is the next morning's work. Now a *trailing* rate over prior batches (§6).
- **`runs` had no batch identity.** Rev 4 quietly turned a run into *one repo's slice* of a night and left it in the table that used to mean the night itself. A multi-repo batch was unqueryable. Now `batches` exists, budget lives on it, and `gate_runs` became `gate_results` to retire the third sense of the word (§4.1).
- **The finding severity scale was defined nowhere in this document.** It had a `severity` column, a rule about blockers, and a queue line printing "1 concern" — and never stated the levels. Writing them down surfaced that two levels were not enough: with only `blocker` and `concern`, every true-but-trivial observation inflates the number that drives queue sort order. `note` added (§5.5).

Two principles from this, and the first is the one worth keeping:

25. **A vocabulary is a test suite for a design, in the same way a spec is.** Both `SA-0001` and `CONTEXT.md` found real defects purely by being written *against* the document with enough precision to force a contradiction. This is now twice in a row, which stops being luck. **Any derived artifact that has to be exact — a glossary, a spec, a schema, a prompt template — is worth writing partly for the defects it will surface.**
26. **Directional words need a fixed referent.** "Promote down the bucket list" is ambiguous the moment the list is printed 1, 2, 3 but ordered cheapest-first. Name the destination, not the direction (§8).

Also settled here: the vocabulary is injected per phase rather than wholesale (§5.3), and it is exempt from the `CLAUDE.md` line budget because it is definitional rather than behavioural (§8).

---

