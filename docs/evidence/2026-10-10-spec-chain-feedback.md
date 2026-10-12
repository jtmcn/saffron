# Spec chain feedback, 2026-10-10

## A rewrite after a cell, `SA-0245` split into `SA-0245` and `SA-0258`

Run 32's cell ran `SA-0245` and ended `EXHAUSTED`. It landed 2087 changed
tokens against the `bug` ceiling of 1300, from an estimate of 1128. It peaked
at 131 turns against a ceiling of 130, and REBUT ran out with four blockers.
The operator chose a split. `SA-0245` keeps the handler, the exit code 143
and the in-process witnesses. `SA-0258` takes the `batch` wrap, the process
witness and the prose. One writer drafted both, from the cell's own patch,
findings and criterion probes.

### Cost

| Step | Time |
|---|---|
| Draft, both specs | 30.9 min |
| Review 1, `SA-0245` and `SA-0258` | 4.3 and 4.0 min |
| Revise 1, both | 13.7 min |
| Review 2, `SA-0245` and `SA-0258` | 5.5 and 5.4 min |
| Revise 2, both | 10.1 min |

Both landed under 80% of the ceiling, measured on prototypes by `size_gate`.
`SA-0245` measured 776 tokens and `SA-0258` 467. Neither had a third review.

### Rounds

| Spec | Round 1 | Round 2 |
|---|---|---|
| `SA-0245` | 2 blockers, 1 concern, 4 notes | 0 blockers, 2 concerns, 3 notes |
| `SA-0258` | 0 blockers, 2 concerns, 4 notes | 0 blockers, 0 concerns, 5 notes |

### Each finding by class

- **A wrong version the witness passes.** Round 1's first blocker and round
  2's first concern on `SA-0245`. A handler raising a `KeyboardInterrupt`
  subclass passed, because only the bare run read the class. A build that
  also wrapped `batch` passed too. It would have turned `SA-0258`'s witness
  green at its own base. The writer had killed every listed wrong version.
  Both reviewers found theirs by naming a wrong build per Problem sentence.
- **A design conflict the spec named and left open.** Round 1's second
  blocker. The spec said §4.3's "never auto-clean on failure" was stale and
  left it to the operator. The operator amended §4.3 by hand. Pre-flight 8
  found the conflict, and then nothing forced a decision before the review.
- **A claim over a set whose witness drives one member.** `SA-0258`'s round 1
  concern. The claim covered any live child, and the witness drove one with
  its output discarded. The agent turn's piped child is the member it missed.
- **A measured fact stated past its measurement.** `SA-0258`'s second round 1
  concern, and `SA-0245`'s Linux concern in round 2. A sentence said a stop
  waits "until the agent next writes", which was reasoned. The witnesses had
  run on macOS only. The writer then ran all three in the cell image.

### What run 32 left that the rewrite used

The cell's `criterion-probes.json` and `rebuttal.json` named both surviving
wrong versions. The writer confirmed both were real, not misnamed witnesses.
The cell had written its child process with the marker inside it, so the
signal landed in `Popen.__exit__`'s own wait. The spec had said otherwise.
So a spec's notes must pin a witness's shape tightly enough that a cell
cannot rebuild a masking one. The rewrite's notes now say why each detail
matters.

## An arm the evidence overturned, `SA-0259`

Item b-f8fa24 said the in-cell agent is refused every write to
`.pre-commit-config.yaml`. A spike measured the set before any writer ran.
Under IMPLEMENT's options, Write was refused on 41 of 69 paths, for $7.21.
The operator chose an intake refusal. The writer drafted it, with a ninth
refusal kind.

Its report then named two retired specs whose cells had written `.claude/`.
Their events showed `python3` writes through `Bash`, 80 in `SA-0116` and 32
in `SA-0196`. A spike confirmed the route on five refused paths, for $0.52.
Another showed an allow rule does not lift the refusal, for $0.40. So the
premise was false, and the refusal would have blocked work that merges. The
operator moved the arm to IMPLEMENT's prompt, which names the route.

### Cost

| Step | Time |
|---|---|
| Draft, intake refusal | 26.6 min |
| Rewrite, prompt route | 15.0 min |
| Review 1 | 5.8 min |
| Revise 1 | 7.6 min |
| Review 2 | 5.0 min |
| Revise 2 | 7.1 min |

### Rounds

| Round | Blockers | Concerns | Notes |
|---|---|---|---|
| 1 | 0 | 4 | 4 |
| 2 | 0 | 2 | 3 |

### Each finding by class

- **A wrong version at a different site.** Round 1's first concern. The
  section appended inside `constraints_block` passed every witness, and the
  end review's prompt would carry the route. Witnesses that read one prompt
  do not pin the prompts beside it.
- **A measured fact stated past its measurement.** Two concerns, in the spec
  and in my own `DESIGN.md` hand edit. Both said Edit and shell redirects are
  refused over the set. Only Write was measured over it. Edit and redirects
  were seen on one path, in `SA-0255`'s cell.
- **The same class again, one site over.** Round 2's first concern. Salvage
  rebuilds its options from the bare system prompt. A build that added the
  section only there passed every witness, measured at 346 passed. Round 1
  named the class, and its fix pinned one more site, not all of them.
- **A sentence true of the set and false of a member.** Round 2's second
  concern. "Refused on one of them" read true in §5.3, where "them" is the
  set. In a prompt naming only `sub/.claude/x.md`, it claims an unmeasured
  refusal.
- **A hand edit that broke its neighbour.** My §5.3 paragraph split "Those
  first two" from what it names.

### What the next run changes

- **Search past cells for the opposite before designing around a refusal.**
  The ledger and `~/.saffron/batches/` held the counterexample all along.
  The 69-path spike measured the file tools and never tried `Bash`. A check
  for "has any cell done what this item says cannot be done" would have
  saved a draft and a decision.
- **Name a wrong build per Problem sentence, and per site.** Every finding
  that survived a writer's kill list came that way. A kill count proves only
  the list it was given.
- **A child's red-at-base depends on the parent not overreaching.** A spec
  whose child takes half its work needs a witness that the parent left that
  half alone.
- **`driver.py probe` should exit non-zero on a kill.** It always exits 0.
  A wrong version needing two edits runs as nested probes, and the outer
  verdict then always reads "survived". Both `SA-0259` rounds had to read
  the inner pytest line by hand.
- **Settle a named design conflict before review 1.** A spec that says "for
  the operator to settle" costs a blocker. The brief should ask first.
- **Read a hand edit's own paragraph for antecedents.** Pre-flight 12 caught
  overclaims in earlier runs, and it still does not read placement.

## Seven tier 1 items, nine specs, `SA-0260` to `SA-0268`

The operator asked for specs for the next loop while run 32's batch ran
elsewhere. Two read-only agents triaged sixteen tier 1 items first.

| Verdict | Items |
|---|---|
| Ready to spec | b-6cd3c2, b-032c61 |
| A decision, then a spec | b-3bba0f, b-a7e5f3, b-883f74, b-e0e1cf, b-4a63b7 |
| By hand or a measurement | b-cab612, 40, 49, 79, b-a8270f |
| Fixed already | b-a04cc8, b-3c7ce9, b-8170eb, b-a4df62 |

Each stale verdict was checked at base before closing it. Four of sixteen
tier 1 items described code a merged fix had already changed.

The operator chose four arms. b-4a63b7's arm failed at the writer's step 1.
REBUT records no probe kill, and ADR 3 runs no probe after REBUT. The
operator deferred it, and the item's record says why.

### Cost

| Spec | Draft | Review 1 | Revise 1 | Review 2 | Settle |
|---|---|---|---|---|---|
| `SA-0260` | 21.9 min | 2.1 min | 7.4 min | 1.8 min | none |
| `SA-0261` | 14.2 min | 3.9 min | 7.6 min | 3.5 min | 6.2 min |
| `SA-0262` | 19.1 min | 5.8 min | 9.5 min | 3.6 min | 7.6 min |
| `SA-0264` | 29.0 min | 7.0 min | 7.3 min | 2.8 min | by hand |
| `SA-0265`, `SA-0267` | 31.5 min | 7.8 min | 32.0 min, split | 7.4 and 5.6 min | 23.6 min |
| `SA-0266`, `SA-0268` | 31.2 min | 8.7 min | 21.9 min, split | 5.3 and 6.3 min | 10.8 min |

Triage took 2.6 and 3.2 min. b-4a63b7's writer stopped after 1.2 min.

### Rounds

| Spec | Round 1 | Round 2 |
|---|---|---|
| `SA-0260` | 0 blockers, 2 concerns | 0 blockers, 0 concerns |
| `SA-0261` | 1 blocker, 1 concern | 0 blockers, 2 concerns |
| `SA-0262` | 0 blockers, 5 concerns | 0 blockers, 3 concerns |
| `SA-0264` | 0 blockers, 4 concerns | 0 blockers, 3 concerns |
| `SA-0265` | 1 blocker, 6 concerns | 0 blockers, 4 concerns |
| `SA-0267` | 0 blockers, 6 concerns | none |
| `SA-0266` | 1 blocker, 4 concerns | 2 blockers, 2 concerns |
| `SA-0268` | 1 blocker, 3 concerns | none |

No first review came back empty. Every round 2 finding was settled by the
writer measuring on its prototype, with no third review.

### Each finding by class

- **An arrangement that hides a wrong version.** The largest class, nine
  findings. A `GATE_ERROR` spec left `remaining`, so a loop that re-offered
  it looked the same as one that did not. Two seeds a witness rested on
  could be written so they killed nothing. A test's margins of years hid
  a missing one-second truncation and a local-time conversion. Pre-flight
  1 drives each member of a set. It does not ask what else the
  arrangement makes equal.
- **A claim over a set whose witness drives one member.** Five findings.
  The dead-state refusal drove one of `REJECTED` and `EXHAUSTED`. A carried
  pull request was driven on one of three states.
- **A rule a sibling path already enforces, missed by a new path.** Two
  blockers on `SA-0266` and `SA-0268`. A new command started gate cells
  with no N1 host probe, then probed without reporting what it tolerated.
  `run_one_cell` does both. No pre-flight check asks what invariants the
  path being copied carries.
- **My own hand edits.** Seven findings across five specs. A count left at
  four, a residual credited to the wrong item, a glossary word the specs
  then broke, and three sentences that contradicted the code or each
  other. Pre-flight 12 caught none of them, because they were written
  after it ran.
- **A residual the spec did not state.** Six findings, most on `SA-0262`
  and `SA-0264`. A design argument resting on what the change exposes,
  not on what it fixes.
- **Size.** Two specs split after review, not before. Each review added a
  criterion that pushed the prototype past 80% of its ceiling.
- **A precedent cited for the opposite.** The writer called `migrate.py`
  a precedent for a non-PACKAGE state in a `task_package` fact. It maps
  every such state away.

### What the next run changes

- **Ask what the arrangement makes equal.** For each wrong version, name
  the state that tells it apart, and check the arrangement reaches it.
  This is the class that survived every writer's kill list.
- **Copy a path's invariants with its calls.** A spec that starts cells
  outside `run_one_cell` lists what `run_one_cell` does before a cell
  starts, and says which it keeps.
- **Pre-flight 12 runs after every hand edit, not once.** Each review
  round moved a hand edit, and the next reviewer found it.
- **Price a review's likely additions before the first review.** Both
  splits came from reviews adding a witness to a spec already near 80%.
- **A triage pass is worth its cost.** Six minutes found four stale tier 1
  items and one infeasible arm before any writer started.
