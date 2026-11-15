# Spec chain feedback, 2026-11-15

Continues `docs/evidence/2026-11-14-spec-chain-feedback.md`. Check numbers
carry on from its 56. Two writers drafted in parallel after spec loop run
72 merged, each in its own worktree cut from `7219608c`.

## SA-0399 (b-e447ea)

`RETIRED_DIRNAME` moves to `saffron/intake.py`, and every reader takes it
from there. Draft time was about 17 minutes.

**Review 1: 0 blockers, 1 concern, 3 notes.** Applied by hand, and the
chain stopped.

- Criterion 1 flags any `done` part of any literal in `saffron/`. A later
  status value would trip it. It stays as a tripwire with a message that
  says to narrow it. Check 57 names the class.
- A bare `done` line in an f-string at `session.py:1418` passes only under
  exact part equality. The notes now pin that rule. Pre-flight 1 missed a
  member the scan reaches.
- The smoke test's reason for holding SA-0399 went unrecorded. One more
  docstring line trips the docstring-length rule, so it stays out.
- An annotated assignment would hide the definition from criterion 2.
  The notes now name `AnnAssign`. Pre-flight 3 missed the node kind.

## SA-0400 (b-11e2ac)

A criterion probe whose file matches no `touches` glob and is not its
criterion's `subject` is refused before any cell. Draft time was about 18
minutes. The `DESIGN.md` §5.4.1 and `CONTEXT.md` sentences landed in the
spec's own pull request.

**Review 1: 1 blocker, 4 notes.** The writer revised.

- No probe on a `touches` file sat under the criterion with a subject. A
  subject that replaced `touches` passed. Pre-flight 1 missed the member.
  Check 58 names it.

**Review 2: 1 concern, 3 notes.** Applied by hand and measured on the
prototype.

- The path rule was driven only by a leading `./`. Stripping that prefix
  passed. A probe on `pkg/../other/u.py` now kills it. Check 59 names it.

## Checks to build

57. A witness that scans source for a spelling says how broad its rule
    is, and its failure message says what to do when a new use trips it.
58. A rule with two ways in drives a member that enters by each way under
    the case that also has the other.
59. A claim that a path is normalised drives a spelling a prefix strip
    leaves alone.
