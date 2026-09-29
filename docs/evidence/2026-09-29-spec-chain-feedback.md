# Spec chain feedback, 2026-09-29: run 21's seven items become four specs and three fixes by hand

Run 21 (`docs/evidence/2026-09-29-spec-loop-skill-feedback-run-21.md`) ranked
seven items for Saffron to absorb. This chain turned four into specs through
the writer and reviewer agents. The other three landed by hand, since two
live in `.saffron/**`, which is `protected`, and one was a single assertion.
Run 21's stack had merged (#574 to #583) before the chain began, so every
spec is cut from `main`.

## What the operator settled

- All seven items, tier 1 and tier 2.
- b-cf832a by hand: `.saffron/gates/tests.py` fills `uncollected`, which
  also closes items 50 and 51.
- b-47659f by hand, after the delegate's probe confirmed it.
- b-5b1f8a: a structure rule first. When that measured unworkable, the
  adequacy prompt, inside `SA-0195`.
- b-78ccc7: spec now, and ADR 8's measured pass at review time.
- b-66d1c3: a stacked child's REVIEW is `main`'s, said aloud. No ADR.

## What the chain produced

| Spec | Item | Type | Size priced | Rounds | Round 1 | Round 2 |
|---|---|---|---|---|---|---|
| `SA-0193` | b-cd5fd2 | feature | 1388 of 3000 | 2 | 1 blocker, 1 concern | 0 blockers, 0 concerns |
| `SA-0194` | b-38d45f | bug | 784 of 1300 | 2 | 1 blocker, 3 concerns | 0 blockers, 2 concerns |
| `SA-0195` | b-78ccc7, b-5b1f8a | feature | 1840 of 3000 | 2 | 0 blockers, 4 concerns | 0 blockers, 3 concerns |
| `SA-0196` | b-66d1c3 | feature | 1656 of 3000 | 2 | 0 blockers, 4 concerns | 1 blocker, 3 concerns |

The stack is `SA-0193` ← `SA-0194` ← `SA-0195` ← `SA-0196`. No spec declares
a parent, and no two share a touched file. They stack only because each
spec commit rewrites the queue smoke test's pinned lines.

The fixes by hand:

- **b-cf832a, items 50 and 51.** The `tests` gate collects file by file
  when a handed subset fails to collect. It reports each name it cannot
  collect in `uncollected` and as a failure keyed on the node id. Replayed on
  `SA-0187`'s cell commit with its source reverted, the old gate gave `error`
  and `revert` skipped. The new gate reports 3 witnesses failing without
  their source and 3 uncollected.
- **b-47659f.** With `run_criterion_probes` moved past the critic cell's
  teardown, `SA-0120`'s witness passed. It now asserts the critic timeline,
  and both mutants fail it.

## Where the chain departed from the brief

- **The arm for b-38d45f.** The brief preferred tokens shaped like
  identifiers. The writer measured both arms over 188 ledger findings. The
  identifier arm unanchored 14 real findings, and a list of 54 common words
  unanchored none. The measurement won.
- **A stale item claim.** b-78ccc7 said REBUT's verdict prompt carries no
  standing instructions. At base it does (`saffron/phases/rebut.py:287`).
  The writer dropped that bullet.
- **A structure rule for b-5b1f8a.** 62 asserts at base compare with a
  constant spelled in capitals. Most are routing checks beside a literal pin.
  A rule cannot see the pin, and `structure` has no ratchet, so the rule
  would fail the tree at base.

## Findings by class

| Class | Spec | Round | Check that should have caught it |
|---|---|---|---|
| A claim over a set whose witness drives one member | 0193, 0194, 0196 | 1 | pre-flight 1 |
| The same, on letter case and on the four turn prompts | 0194, 0196 | 2 | pre-flight 1 |
| A trigger set that names less than the sources it claims | 0196 | 2 | pre-flight 3 |
| An arrangement read, not run | 0194, 0195 | 1 | pre-flight 10 |
| A protected edit the spec names, not yet at base | 0194, 0195 | 1 | none: the delegate's order |
| A sentence in a touched file the new text contradicts | 0195 | 1 | pre-flight 8 |
| Dictated prompt text never run through `prose` | 0195 | 1 | pre-flight 11 |
| A hand edit that says more or less than the build | 0195 | 2 | none: nothing reviews the delegate's own edit |
| A turn ceiling margin over a floor | 0195 | 2 | pre-flight 7 |
| A downstream reader the change leaves unnamed | 0195 | 2 | pre-flight 4 |
| A staleness anchor written after the state it guards | 0196 | 1 | pre-flight 4 |
| A spec directory parsed on every call | 0196 | 1 | none |

The claim over a set was every blocker in the chain, again, in both rounds. Each writer ran
its declared wrong versions on a prototype and killed them all. Each
blocker was a wrong version nobody declared. The writer measures what it
thought of, and the reviewer supplies the next member of the set.

`driver.py cite` ran clean on every draft. No round found a claim about the
tree that had stopped being true.

## New checks this run argues for

- **Land the protected edits before the first review.** Two first reviews
  spent a concern on a `DESIGN.md` sentence the spec already listed. The
  delegate makes them in the spec's branch, then dispatches the reviewer.
- **Review the delegate's own hand edits.** The one second-round concern on
  `SA-0195`'s docs was an edit the delegate wrote. The second reviewer reads
  those edits against the build, and the brief says so.
- **A spec's dictated text passes `prose` before review.** The writer runs
  `hooks/prose_limit.py --file` on a copy of each file the spec dictates
  text into.

## The loop's own gaps

- **`bookkeeping` drafts a new smoke test paragraph.** Every writer
  appended one, and the commit hook refused each. The `prose` gate keys a
  docstring on its length, so the paragraph must be rewritten in place.
  Four commits needed it by hand. The command should draft the replacement.
- **Parallel writers collide on the smoke test.** Each pins the candidate
  list, so four branches conflict on one line. Restacking them took a
  rewrite per branch.

## Rounds and cost

| Step | Wall time |
|---|---|
| Four drafts, in parallel | 18 to 23 minutes each |
| First reviews | 4 to 6 minutes each |
| Revisions | 5 to 9 minutes each |
| Second reviews | 3 to 6 minutes each |
| Round-2 fixes, no third review | 5 to 9 minutes each |

## What the delegate got wrong

- **A brief that stated an arm.** b-38d45f's brief preferred the identifier
  arm, which would have dropped 14 real findings. The brief asked the writer
  to measure, which is what caught it.
- **The protected edits came late.** They landed after the first reviews,
  which spent a concern on each.
- **A hand edit that overclaimed.** `SA-0195`'s `DESIGN.md` sentence made
  reading the `_Avoid_` lists conditional. The build reads them always.

## Not settled

- ADR 8's measured pass for `SA-0195` is hand work at review time. Its
  fixture of run 20's five Standards defects does not exist yet (b-abeb74).
- REBUT's verdict session keeps the stripped vocabulary, so it cannot check a
  conventions blocker filed on an `_Avoid_` word. `SA-0195` names it out of
  scope.
- `SA-0196`'s `findings.json` read is overwritten by a spec's next run. A
  record fact would follow item 170's direction.
