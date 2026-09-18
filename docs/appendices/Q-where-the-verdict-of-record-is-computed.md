---
id: Q
title: "rev 21: where the verdict of record is computed"
revisions: [21]
question: "Where the verdict of record is computed: outside the container the implementer had root in, on the tree the exported patch describes"
---

Found threat-modelling Saffron on 2026-09-13: a bootstrap from the code and the
git history, then an interview with the owner. It was confirmed by reading the
code rather than by probe, and recorded as backlog item 118.

**The finding is a class, and every earlier fix was an instance of it.** This
document records four routes by which the implementer changes what the host
reads back: `diff.srcPrefix` (Appendix K, backlog item 2), the diff settings
(item 89), replace refs (item 102) and binary rendering (item 103). Each was
closed by pinning one more thing on the command line. The class was open at its
root. The final gate suite and every critic lens ran in the implementer's own
container, after it had spent the repair loop as root on a writable rootfs.
The gates' executables came from `/gates`; the `pytest`, `ruff`, `git` and
Python they call did not. The lenses were fresh sessions; the runner and SDK
each session re-execs were not fresh. And the one check PACKAGE owns outside
that container, re-verification, was skipped on an unmoved base, which is most
bases, because a re-run there was "provably redundant".

58. **A check that is redundant only if its subject was honest is not redundant.**
    "Provably redundant" was true about the tree: an unmoved base makes the
    packaged tree byte-identical to the one the suite ran on. It said nothing
    about the verdict, and the verdict is the only thing the re-run was for. A
    skip justified by equal inputs has to ask who computed the output. When the
    answer is the party being checked, the equality proves nothing.

**What changed.** The verdict of record moves out of the implementer's
container, on both halves (§5.4 to §5.7):

- PACKAGE re-verifies every packaged commit, in a gate-only cell, on a commit
  host git built from `patch.diff`. What the gates judge is what is pushed
  (`SA-0086`).
- REVIEW's lenses and REBUT's verdict lenses run in a **critic cell**: a new
  container from the repo's image, whose worktree is the task's base with the
  exported patch applied. What the critic reads is what ships (`SA-0087`,
  `SA-0088`).
- The gate table a REVIEW lens is shown comes from a suite run in a gate-only
  cell on that same rebuilt tree, never in the critic cell, where the gates
  would run model-authored code as root before the lenses re-exec their runner
  (`SA-0089`).

The suites the repair loop runs stay where they were. They are feedback, and
feedback the agent can corrupt corrupts only the agent's own attempt.

**What it does not change.** The cell still runs as root on a writable rootfs
(§5.4). Nothing here makes the implementer's container trustworthy; it only
stops the verdict depending on it. A read-only rootfs and a non-root `USER`
would narrow what the agent can reach inside it, the token and the host's
resources among them, and are still worth doing for that. This revision does
not rest on them. §5.4's invariant is untouched: a lie still has to be visible
in the diff, and the diff is now also the only thing the verdict is computed
from.

**Vocabulary.** "Critic cell" is a hand-written `CONTEXT.md` entry, as **Cell**
and **Critic** are. It is not a `factory:` term: nothing would read one, and
`tests/ontology/test_no_dead_terms.py` deletes a term with no reader. Until
someone decides otherwise, a verdict that does not reproduce on an unmoved base
shares `MERGE_FAILED` with a change that did not survive today's main (item
118).

