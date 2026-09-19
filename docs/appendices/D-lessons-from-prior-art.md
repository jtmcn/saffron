---
id: D
title: "rev 5: lessons from prior art"
revisions: [5]
question: "What prior art does better — and the negative finding, that good process hygiene converges on near-zero verification"
---

Reviewed `mattpocock/sandcastle` — a TypeScript library for orchestrating coding agents in sandboxes, plus the author's own factory built on it (a label-driven GitHub Actions pipeline, and two earlier abandoned generations: a local daemon and a parallel planner).

**The headline finding is a negative one, and it is the most useful thing here.** Their pipeline has essentially no verification. `ci.yml` is `on: push: branches: [main]` — **no `pull_request` trigger**, so agent PRs receive zero automated checks before a human merges them. Every "run the tests" instruction is prose inside a prompt, executed and self-assessed by the agent. Their own library documents the host-side gate pattern explicitly — *"`sandbox.exec()` … handy for gating an implement step on a quick verification"* — and their factory never uses it. Their reviewer is framed as a refactoring agent told to *"preserve exact functionality"*, posts `event: "COMMENT"` (never `REQUEST_CHANGES`), and then calls `gh pr ready` — it advances the PR and structurally cannot block it. There is nothing anywhere on anti-gaming, baselines, or repair loops; their iteration terminates when the agent prints `<promise>COMPLETE</promise>`, a string the agent controls.

This is a serious, well-engineered project by a capable author, and it converged on: **good process hygiene, near-zero verification.** Read that as evidence about where the gravity pulls. Process is visible, satisfying, and produces a working pipeline quickly; gates are invisible until the day one catches something. Saffron's entire bet is the other way round, and this is the strongest argument yet for not letting that bet erode when the harness work gets tedious.

**What they do better, adopted here.** All operational, all things you learn by running something overnight rather than by designing it:

15. **Treat agent output as claims; reconcile against a host-computed fact set.** They validate the reviewer's inline comments against parsed diff hunks and drop the ones that don't land. Generalized in rev 5 to critic findings (§5.5) and to phase transitions (§4.3, doneness measured from git — `commitsAhead`, HEAD-moved, `--diff-filter=U`). This is the same principle as host-invoked gates, extended from quality to control flow.
16. **Bound liveness on more axes than you think, and never let a bound destroy work.** Their ADR-0019 documents an agent finishing, a spawned child holding stdout open, EOF never arriving, the full idle timeout burning, and *then the committed work being discarded*. Hence rev 5's split of idle from completion, and the rule that any bound firing still evaluates the worktree (§4.3).
17. **Refuse before you spend.** Their workflows check issue shape and existing PRs before starting an agent. Rev 5 makes this scheduler gate 0 (§4.2).
18. **Structured output is a separate, tool-less turn** — do the work, then resume the session with a prompt that forbids acting and asks only for the block (§5.3). Bounded schema retries, never content retries.
19. **Retry idempotent infrastructure races; fail fast on everything that builds what the agent acts on.** Their ADR-0020, on a prompt-expansion timeout under parallel load: degradation is worse than abort, because a silently-wrong prompt burns an attempt producing plausible garbage (§4.3).
20. **Control files in the workspace are agent-visible and agent-writable.** Their worktree lock deliberately lives outside the worktree — *"visible to the agent, which could delete or commit it."* Saffron had `plan.json` inside `/work` after validation; fixed (§5.3).
21. **`--force-with-lease` pinned to the checked-out SHA, and one writer per branch** (§5.7). Turns a silent clobber into a loud failure for the price of a flag.
22. **Source determines processing** — their ADR-0008: inline prompts skip templating entirely, because callers pipe issue bodies containing `{{...}}` into them. Spec text is data (§5.3).
23. **A living refusal record.** Their `.out-of-scope/` gives each refused feature a doc: what, why, which seam covers it, and the prior requests. Adopted for §1.4.
24. **A glossary with explicit *Avoid:* lists**, read by agents before they touch code. Cheap, and it competes directly with the ontology — so it is now a second bar `RATIONALE.md` has to clear (§4.6, rule 2b).

**Deliberately not adopted.** GitHub labels as the task queue and state machine — it's a good fit for a public repo with contributors and a poor one here, where specs-in-repo buy version-controlled acceptance criteria and offline batches. Their `<promise>COMPLETE</promise>` completion signal, for the obvious reason. And their reviewer framing, which is the thing Saffron most specifically rejects.

---

**One thing to actually go read, independent of this design:** `docs/research/permissions-systemic-fix.md` and ADRs 0005/0014 — a full taxonomy of container UID/permission failures, including that macOS assigns GID 20 to `staff` while `node:22-bookworm` already uses it for `dialout`, so `groupmod -g 20` fails and the image build dies without `-o`. Also that a single-file bind mount whose parent doesn't exist in the image causes Docker to create the parent as `root:root` and silently break auth. Those will cost a day each to rediscover, and §5.1's cell will hit both.

---

