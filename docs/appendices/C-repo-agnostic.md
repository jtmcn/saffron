---
id: C
title: "rev 4: repo-agnostic"
revisions: [4]
question: "What makes Saffron language-blind: the gate contract, and the core/repo boundary it draws (§2.1, §5.4)"
---

Saffron develops any repo, in any language. `thermal-edge` is demoted from *the* target to *an* example — the second repo, after Saffron itself.

**What actually changed, structurally.** Only one thing, and everything else follows from it: **the gate contract** (§5.4). A gate is an executable emitting one JSON object. That single decision is what lets the repair loop, baseline subtraction, and the whole review pipeline stay language-blind, because nothing downstream ever sees tool output — it sees `failures[]`. The corollary that makes it work is that gates translate their own output, which pushes ~20 lines of shell into each repo and keeps every parser out of the orchestrator.

The rest is bookkeeping: a `repos` table, per-repo preflight and baselines, round-robin scheduling, a repo column in the queue.

Three principles this revision contributes:

12. **A boundary is cheap; an abstraction layer is not.** The contract gets written now because retrofitting one into a core that has grown language knowledge is painful. The *second implementation* of anything waits for a repo that needs it. There is no plugin registry with one plugin.
13. **When a check feels language-specific, separate the question from the vocabulary.** "Was a test deleted or silenced?" is universal; `@pytest.mark.skip` is not. Put the question in core and the tokens in `policy.yaml` (§5.4, `integrity`). This is the single most reusable move in the whole design.
14. **Generality is a claim, and claims need tests.** Two Python repos prove nothing about language independence. Repo three exists to falsify §2.1, should be chosen for dissimilarity rather than usefulness, and has a pass condition stated in advance: the diff to Saffron's source is empty.

**What did not change, and shouldn't:** every safety property in §5.1 is about containers and git, not about languages, so repo-agnostic costs nothing there. The critic lenses (§5.5) are stated in terms of correctness, contracts and test adequacy rather than any stack — that was accidental in rev 2 and is load-bearing now. And §8's flywheel becomes *more* valuable with multiple repos, because a rejection reason promoted from `CLAUDE.md` to a gate in one repo is a gate you can copy into the next.

---

