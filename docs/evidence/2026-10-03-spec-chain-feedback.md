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

## Second chain: `SA-0201` to `SA-0204`

Four tier 1 items became four specs in one chain. They harden the paths a
stack batch cannot survive unattended, before its first live run. The
operator settled one design question per item before any writer ran.

| Spec | Item | What it builds |
|---|---|---|
| `SA-0201` | b-031ac2 | `PROVIDER_UNREACHABLE`, exit 2, re-offered in a stack batch |
| `SA-0202` | b-7251b5 | one re-prompt for a malformed wrong-version answer |
| `SA-0203` | b-4c5dc7 | one REBUT past the budget under a $7.00 cap |
| `SA-0204` | b-038aef | a draft pull request for a cut-short `EXHAUSTED` task |

The four writers ran in parallel from one base. Every pair shared a file, so
the caller chained them afterwards and set each `depends_on`.

### Cost

Wall time per agent, from each agent's own report.

| Spec | Draft | Caller revise | Review 1 | Revise 1 | Review 2 | Revise 2 |
|---|---|---|---|---|---|---|
| `SA-0201` | 30.6 min | 8.0 min | 7.1 min | 8.0 min | none | none |
| `SA-0202` | 27.9 min | none | 7.0 min | 7.8 min | 5.6 min | 7.2 min |
| `SA-0203` | 29.8 min | 9.5 min | 7.0 min | 8.8 min | none | none |
| `SA-0204` | 28.1 min | 7.1 min | 6.9 min | 11.4 min | none | none |

A "caller revise" answered a finding the caller raised from a writer's
report, before any review. Revisions measured each fix on the prototype in
place of a second review. `SA-0202` took one second review, because its
first blocker sat in a criterion the revision rewrote.

### Rounds

| Spec | Round | Blockers | Concerns | Notes |
|---|---|---|---|---|
| `SA-0201` | caller | 1 design | 0 | 0 |
| `SA-0201` | 1 | 0 | 5 | 4 |
| `SA-0202` | 1 | 1 witness | 3 | 4 |
| `SA-0202` | 2 | 1 witness | 1 | 4 |
| `SA-0203` | caller | 1 design | 0 | 0 |
| `SA-0203` | 1 | 2 witness | 5 | 4 |
| `SA-0204` | caller | 1 design | 0 | 0 |
| `SA-0204` | 1 | 0 | 5 | 4 |

No first review came back empty. Every review blocker was a witness that let
a wrong version pass. Every caller blocker came from parallel drafting.

### Each finding by class

- **A set member no witness drives.** This is check 1 again, and the largest
  class.
  - `SA-0202`: three kinds of bad answer, then two answers of the same kind.
  - `SA-0201`: the scope re-prompt beside the schema re-prompt.
  - `SA-0203`: a rebuttal with no commit, and a REBUT that crosses the budget.
  - `SA-0203`: a second lens's verdict session under one cap.
- **A mutant that survives another build of the same change.** `SA-0201`'s
  breaker mutant died on the prototype and lived on a build with its own
  branch. The writer measured it, then strengthened the witness. Check 1
  should ask which other builds the Problem section permits.
- **A brief decision copied from a neighbour state.** The caller told the
  `SA-0201` writer to treat the new state as `PREFLIGHT_FAILED`. In a stack
  batch that made it a miss, which the operator's decision ruled out. No
  check reads the brief.
- **Siblings drafted apart that change each other's paths.** `SA-0203` made
  the path `SA-0204` packages unreachable and added a halt. The overlap check
  in step 3 reads `touches`, never behaviour. Coupled specs need one writer
  in sequence, or each brief names the other's end state.
- **Hand edits that say more than the criteria.** `SA-0201`'s §5.1.1 and its
  shapes comment, `SA-0203`'s §5.6, §3.3 and ADR 4, and `SA-0204`'s §5.7.
  Check 8 reads the spec against the design, and nothing reads the hand
  edits against the spec.
- **A queued spec's witness that pins a set.** `SA-0198` pins all 24 task
  states, and `SA-0201` adds a 25th. Check 6 reads tests at base, and never
  the witnesses of queued specs.
- **A code sentence the change makes false.** `SA-0203`'s comment at
  `session.py:77`, and `SA-0204`'s commit text at `package.py:322`. This is
  check 6.
- **An assertion that holds either way.** `SA-0202`'s "no `- Nothing:` line"
  held with or without the errored entry. The writer found it by inverting
  the assertion on the prototype.

### For the skill

- Draft coupled specs in sequence, or give each writer the others' settled
  end states. Parallel drafting cost three caller rounds here.
- Add a check for hand edits: each sentence in DESIGN, an ADR or the ontology
  names the criterion that makes it true.
- Check 6 should grep queued specs' witnesses for pinned sets.
- Every writer grew the smoke test's top paragraph to four lines, and the
  `prose` hook refused three of them. A scratchpad script rewrote the pin per
  branch during the restack. `driver.py bookkeeping` could own that pin.

## SA-0201, from item b-3732ef

The spec makes the ledger record which model ran each attempt. It covers
the item's first half. The paid comparison of a stronger model stays a
script run by hand.

| Draft | Pre-flight revise | Review 1 | Revise 1 | Review 2 | Revise 2 |
|---|---|---|---|---|---|
| 17.0 min | 1.1 min | 4.7 min | 1.6 min | 4.3 min | 3.4 min |

| Round | Blockers | Concerns | Notes |
|---|---|---|---|
| Pre-flight | 1 | 0 | 0 |
| 1 | 1 | 3 | 4 |
| 2 | 2 | 2 | 3 |

- **A measured fact the writer could not see.** The pre-flight found the
  CLI's `<synthetic>` model name in 15 host transcripts. The CLI writes it
  for rate limits and API errors. As drafted, a walled turn would record it
  as a model. Check 8 found it by asking what each value can hold.
- **A set member no witness drives.** This is check 1, and it took every
  blocker in both rounds. The Notes allowed row values that kill a wrong
  version but did not force them. A row with no model at a return place
  reached by no other row hides a caller that passes nothing.
- **A stale claim about the tree.** An operator edit to `DESIGN.md` landed
  in the spec's own commit, and the spec still called the sentence pending.
  Check 5 should run after the delegate's hand edits, not before them.

Round 2 repeated round 1's class, so no third review ran. The writer
implemented every declared wrong version on its prototype instead. It
reported 47 probes and 47 killed, after one survivor forced a row value.

## For the skill, from SA-0201

Check 1 should be a probe table, not a reading. For each wrong version,
the writer implements it on the prototype and names the row that kills it.
That table settled in one pass what two reviews found by reading.
