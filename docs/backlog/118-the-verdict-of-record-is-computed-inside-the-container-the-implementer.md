---
id: 118
title: The verdict of record is computed inside the container the implementer controlled
status: partial
tier: 1
filed: 2026-09-13
by_hand: true
specs: [SA-0086, SA-0087, SA-0088, SA-0089]
prs: [255, 274]
commits: [4ba8bdf]
cites: [§5.4, §5.5, §5.7]
related: [2, 40, 89, 97, 98, 102, 103, 119, 120, 132, 133, 134, 135, 136]
---

## Problem

**Tier 1.** Found threat-modelling Saffron, 2026-09-13, and confirmed by
reading rather than by probe. The cell runs as root on a writable rootfs
(`_run_argv` passes no `--read-only` and no image sets `USER`), and three
things the host trusts run inside it after the agent has had it:

- **Every gate.** The executables come from the read-only `/gates` mount, but
  they call `pytest`, `ruff`, `ty` and `python3` from `/opt/venv` and `/usr`,
  and read the tree through the cell's own `git`. `DESIGN.md` §5.4 names the
  writable toolchain; this is what it costs.
- **Every lens.** `run_review` and `run_verdict` are handed the implementer's
  container, so each critic session re-execs `/opt/saffron/agent_runner.py`
  and the SDK from that rootfs, and reads `/work` and `read_at_head` through
  the implementer's `.git`. The gate table each REVIEW lens is shown is
  `latest.results`, the implementer cell's own last suite.
- **Nothing re-checks either when the base did not move.**
  `needs_reverification` returns `False` on an unmoved base, and its docstring
  calls a re-run "provably redundant". That holds only if the cell's own
  results were honest, so the one fresh-cell check PACKAGE owns is skipped on
  the path most tasks take.

Every git-config forgery this backlog has closed (items 2, 89, 102, 103) is
one instance of the class. Closing the class means the gates and the critic
judge a tree rebuilt from the exported patch, in a container the implementer
never ran in. Then what they judge is what ships, and a forged export only
hides the agent's own work.

Four specs, in order: `SA-0086` (PACKAGE re-verifies every packaged
commit), `SA-0087` (REVIEW runs in a critic cell rebuilt from the patch),
`SA-0088` (REBUT's verdict lenses do the same) and `SA-0089` (the lenses'
gate table comes from a gate-only cell on the rebuilt tree, never from the
critic cell, where a gate would run as root before the lenses do).

**By hand, because a cell cannot:**

- `DESIGN.md` §5.7, "Re-verification runs when, and only when, the base
  moved", and §5.5's lens description, rewritten to the new rule. This should
  land before or with `SA-0086`.
- **Vocabulary.** "Critic cell" landed as a hand-written `CONTEXT.md` entry
  with rev 21, like **Cell**. It is not a `factory:` term, because nothing
  would read one. Still open: whether new failures on an unmoved base need
  their own terminal state. `SA-0086` reports them as `MERGE_FAILED` with a
  note, but that state means the change did not survive today's main, and
  this is a verdict that did not reproduce.
- `saffron/report/pr_body.py`'s `_verification("base")` branch becomes
  unreachable once `SA-0086` lands. Delete it, or keep it as a guard.
- Found reviewing #255: the `"packaged"` branch gave "because the base moved
  after this task started" as its reason, which is false on every unmoved-base
  pull request once `SA-0086` re-verifies them all. It was fixed on the branch
  (`4ba8bdf`) by operator decision, though the spec forbade the file (item 40).
- `DESIGN.md` §5.7 goes stale when #255 merges, in two places: "`SA-0086` builds
  it; until it lands the skip still stands", and "whether or not the suite
  re-runs".
- "Verdict" is used for the cell's gate results in §5.7 ("the cell's own
  verdict did not reproduce"), in Appendix Q's "verdict of record", and in
  `SA-0086`'s own spec text. That goes against `CONTEXT.md`'s **Suite
  comparison** _Avoid_ line and its "never call any of them 'the verdict'
  without saying whose". #255's review took the word out of the code, and the
  design text still carries it.
- **Before `SA-0087` runs again, its third criterion needs amending.** It says "a
  patch that does not apply to its own base in that fresh tree ends the task
  `EXHAUSTED`". `worktree.DIFF_FLAGS` has no `--binary` or `--full-index`, so a
  binary change exports as a `Binary files … differ` stub that can never apply,
  whatever the agent did. PACKAGE's `apply_patch` already calls that
  infrastructure (`PackageError`, exit 2;
  `test_a_binary_patch_is_an_error_not_a_conflict`). Built to the letter, as on
  `saffron/SA-0087` @ `82258f0` (`apply_exported_patch`, the
  `CriticPatchApplyFailed` catch), a task touching a binary file ends `EXHAUSTED`
  before any lens runs and is charged for a gap in the export. That breaks
  `error` ≠ `fail`. The contract lens raised it as a blocker, and REBUT never
  answered it (item 120). Confirmed by reading; no binary diff was run through it.
  The amendment: a stub the export could never carry is `GATE_ERROR` or a
  refusal at export, as PACKAGE has it, and only a real failure to apply is the
  task's.
- **`SA-0087`'s second criterion needs a witness that can fail.**
  `test_the_critic_reads_the_tree_rebuilt_from_the_exported_patch` asserts
  `read_head_containers == [] or …`, and no test scripts a finding outside a
  diff hunk, so `anchor()` never calls `read_head`. The adequacy lens's probe,
  pointing `read_head` at the implementer's own `container` in place of
  `critic_container`, passes all 157 tests in `tests/test_session.py` on
  `82258f0` (run 2026-09-14). That swap is the regression the spec exists to
  prevent. The re-run's witness needs a finding anchored outside a hunk and an
  assertion that `read_head` ran, and ran in the critic cell.

**Not this item:** the threat model's other owner-chosen half, re-gating the
head that merges and handing a delegate findings only as quoted data. Items
**97** and **98** already carry those.

## Done looks like

no gate result or lens finding that reaches a pull
request, and no gate table a lens is shown, was produced in a container the
implementer ran in.

## Record

**Status:** open. `SA-0086` is `READY_FOR_REVIEW`: PR #255, 2026-09-14,
reviewed on the spec loop's second run. It is that run's only reviewable pull
request, so it is not stacked. `SA-0087` ran twice. The first cell ended
`NOT_IMPLEMENTED` at its turn ceiling ($8.39 of $8, item 119). The second, with
its ceilings raised in #256, went green on its first attempt and halted at
`REBUTTING` when REBUT ran out of budget ($14.03 of $14, item 120). Its branch,
`saffron/SA-0087` @ `82258f0`, is pushed with no pull request. The operator
stopped the chain there, so `SA-0088` and `SA-0089` never ran.

**2026-09-15:** `SA-0087` amended before its third run, in PR #263. Its
third criterion now splits a real failure to apply (`EXHAUSTED`) from a
binary stub the export could never carry (`GATE_ERROR`). Its second
criterion's witness must anchor a finding outside every hunk and see
`read_head` run in the critic cell. The halted branch, `saffron/SA-0087` @
`82258f0`, is discarded, and the next cell starts from the base.
`DESIGN.md` §5.5 and §3.3 carve the binary stub out by hand in the same pull
request. The budget rises to $20, because run 2 ran dry in REBUT (item 120).

**2026-09-15, later:** `SA-0087`'s third cell reached `READY_FOR_REVIEW` on its
first gate attempt — PR #274, $9.77 of $20, no repair round and no REBUT. The
`type: feature` retype in #271 is what let it finish: the diff came to 515
changed lines, and the `bug` ceiling `size` blocks on at `elevated` is 300.

The review found six blockers the three lenses did not. One was a free way past
the critic: `_apply_and_commit_patch` staged with `git add -A`, which re-runs
the clean filters the patch's own `.gitattributes` installs, so a
`working-tree-encoding` attribute leaves `git apply` at 0 and `git add` at 128 —
`CellRuntimeError`, `ORPHANED`, exit 2, charged to nobody, no lens run, and
re-queued. `git apply --index` replaces it. The other five were witnesses that
could not fail. Items **132**–**136** are what the review left; the branch is
644 changed lines against the `feature` ceiling of 600, accepted by the operator
under item **40**.

**2026-09-16:** `SA-0087` merged (PR #274) and its spec is retired to
`.saffron/specs/done/`. Two of the four slices are now in `main`; the item stays
`partial` for `SA-0088` and `SA-0089`. Retiring it advances the chain in the
live queue: `SA-0088` becomes a candidate, because a parent in `done/` is the
operator asserting that work is in `main`, which a `spec_sha` task lookup cannot
say on its own. The scheduler smoke test is re-measured a twenty-ninth time.

