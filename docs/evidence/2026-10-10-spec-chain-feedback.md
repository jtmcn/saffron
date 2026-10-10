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
