# Spec chain feedback, 2026-10-03

One backlog item became one spec. `SA-0200` comes from item b-b0cd68. It
makes the two tests that read `.saffron/specs/` hold across a retirement, so
a stack batch's finishing commit can go green in this repository.

## Cost

Wall time per agent, from each agent's own report.

| Draft | Review 1 | Revise 1 | Review 2 | Revise 2 |
|---|---|---|---|---|
| 14.0 min | 4.1 min | by hand | 1.6 min | by hand |

## Rounds

| Round | Blockers | Concerns | Notes |
|---|---|---|---|
| 1 | 0 | 2 | 2 |
| 2 | 0 | 1 | 2 |

The first review found no blocker. The pre-flight settled `census` on the
spec's own cell before the writer ran. A rewrite that dropped the per-spec
parametrization would have failed that cell on its first attempt.

## Each finding by class

- **A brief that was wrong.** The brief said `integrity`'s `touches`
  exemption allowed a `pytest.skip(` call. It binds the gate-config check
  alone. The writer caught it before drafting. Step 2 says to verify a
  brief, and this claim was reasoned, not read.
- **A follow-up named without its failure.** Round 1 found the spec deferring
  the driver and `issue-tracker.md` edits without saying a retirement breaks
  until they land. Check 8 reads departures from the item. It should also
  ask what each deferred follow-up breaks in the meantime.
- **A set member no witness drives.** This is check 1, in both rounds.
  - Round 1: a `README.md` in `done/`, and a helper that empties its source.
  - Round 2: the top-level branch of the claim round 1's fix added. A
    revision written by hand skipped check 1 on its own new claim.
- **A prototype claim that predates a revision.** Round 2 noted that the
  wrong versions added in revision 1 were never run. Each revision should
  say which wrong versions it ran.

## For the skill

Revisions made by hand cost less than a writer round. Round 2's one concern
came from one of them, though. Re-run check 1 on every claim a revision
touches, whoever writes it.
