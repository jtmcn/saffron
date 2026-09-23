# Spec chain feedback, 2026-09-23

One spec, `SA-0137`, from backlog item b-a9ee32. Its sibling item b-b5f379
could not be a spec. It edits `DESIGN.md`, which is `protected`, and a cell
cannot rebuild the image it runs in. So it went by hand as pull request #488,
and `SA-0137` stacks on it.

## Pre-flight

The measurements came before the writer. A probe ran on git 2.39.5, 2.47.3
and 2.54. It settled three things before any draft: the pin restores the
hunks, it is harmless on 2.39.5, and it changes nothing for a committed
`.gitattributes`. The same probe found the ordering constraint. On 2.39.5
the witness passes with the fix reverted, so `revert` would refuse it, and
the cell must run on the bumped image.

## Rounds and cost

| Step | Agent | Time | Tokens |
|---|---|---|---|
| Draft | `spec-writer` | 8.7 min | 101k |
| First review | `spec-reviewer` | 3.2 min | 59k |

The first review found no blocker, so no revision ran.

## Findings by class

| Round | Severity | Finding | Class | Check that should have caught it |
|---|---|---|---|---|
| 1 | concern | `SAFFRON_BASE_IMAGE` can swap in a base whose git predates `attr.tree` | An input the claim did not name | none |
| 1 | concern | The witness has no git-version guard, and CI's git is unread | An input the claim did not name | none |
| 1 | note | `HOME=` with the pin passes the witness | A witness drives one member of a set | Pre-flight 1 |
| 1 | note | A pin in `_git` and the script but not `git_argv` passes | A witness drives one member of a set | Pre-flight 1 |
| 1 | note | The turns ceiling is argued from a row of another shape | Size or ceilings | Pre-flight 7 |

The first concern was answered, not applied: `SAFFRON_BASE_IMAGE` is unset
on this host. The second waits for the cell's pull request, the first CI run of the witness. The notes were
left as they stand.

## What the pre-flight should learn

1. **The toolchain version is an input.** A witness that depends on the
   version of a tool bites only where that version runs. That means the cell
   image, any `SAFFRON_BASE_IMAGE` override, and CI. Pre-flight should list
   each place the witness runs and the version found there.
2. **`driver.py check` picks the worst row, not the nearest.** Its line
   compared a two-file change with a four-file one. The nearest row in shape
   peaked at 22 turns against a ceiling of 130.

# Second chain, 2026-09-23: SA-0138, SA-0139 and SA-0140

Three specs from four items, written in parallel with one scratch worktree
each. `SA-0138` is from b-19b255, `SA-0139` from b-6377cf and `SA-0140` from
b-8487de. Item b-440f17 got no spec. It is `done`, and its three new shapes
live in `.saffron/gates/prose.py`, which is `protected`.

## Operator decisions

1. `SA-0140` ends a verdict session that never started in `GATE_ERROR`. REBUT
   already ends `GATE_ERROR` for a critic-cell fault, at `rebut.py:546-550`.
   The first question to the operator said `GATE_ERROR` names only a gate.
   That premise was wrong, and the question was asked twice.
2. Each spec's `protected` edits land by hand in its own pull request. The
   cell and its lenses then read the new rule, not the old one. `CONTEXT.md`
   §4 is injected at IMPLEMENT, REPAIR and REVIEW.

## Rounds and cost

| Spec | Step | Time | Tokens |
|---|---|---|---|
| `SA-0138` | Draft | 23.7 min | 211k |
| | First review | 12.2 min | 149k |
| | Revise | 10.6 min | 44k |
| | Second review | 7.4 min | 114k |
| | Revise | 5.0 min | 12k |
| `SA-0139` | Draft | 17.0 min | 143k |
| | First review | 5.4 min | 85k |
| | Revise | 9.5 min | 51k |
| | Second review | 5.6 min | 86k |
| | Revise | 8.9 min | 37k |
| `SA-0140` | Draft | 19.0 min | 180k |
| | First review | 7.7 min | 98k |
| | Revise | 12.1 min | 59k |
| | Second review | 7.6 min | 95k |
| | Revise | 6.1 min | 20k |

Every second review found a blocker, so every spec took two revisions. The
stop rule held at two reviews. Each final revision measured its change on a
prototype in place of a third review.

## Blockers by class

| Spec | Round | Blocker | Class | Check that should have caught it |
|---|---|---|---|---|
| `SA-0138` | 1 | The fixture's attempts collect what base collects, so `latest` passes for the pre-turn baseline | A fixture makes two reachable values equal | none |
| `SA-0138` | 2 | An uncollected failing code reads `unproven` under two wrong versions | A fixture makes two reachable values equal | none |
| `SA-0139` | 1 | `repair_prompt` tells REPAIR that base failures are excluded | A rendered sentence outside `touches` turns false | none |
| `SA-0139` | 2 | Two tests assert the old preamble's words are absent, and pass silently | A rendered sentence outside `touches` turns false | none |
| `SA-0140` | 1 | The witness runs from pytest's directory, so a prompt file in `/work` passes | A fixture makes two reachable values equal | none |
| `SA-0140` | 2 | Lens order is fixed, so "the first errored lens decides" passes | A fixture makes two reachable values equal | Pre-flight 1 |

## Concerns by class

| Class | Count | Check |
|---|---|---|
| An arrangement argued rather than run | 5 | Pre-flight 10 |
| A claim's witness drives one member of a set | 5 | Pre-flight 1 |
| A protected document the change makes false | 4 | Pre-flight 8 |
| Size or ceilings, a turns peak that is a floor | 4 | Pre-flight 7 |
| A path only a cell-marked test can reach | 1 | none |
| A file one lens leaves for the next in a shared cell | 1 | none |

## What the pre-flight should learn

1. **A fixture makes two reachable values equal.** This is four of six
   blockers. The code can read the wrong one of two values, and the fixture
   gives both the same content. The pairs were the pre-turn baseline and the
   last attempt, the process's directory and the request's, and two lens
   orders. A 2026-09-22 record names the same class. The check is a writer
   step. For each value a witness depends on, list what the code could read
   instead, and make the fixture give each a distinct value.
2. **A rendered sentence the change makes false.** This is two blockers and
   four concerns. A changed prompt, a pinned substring in a test, and a line
   in `CONTEXT.md`, `DESIGN.md` or an ADR each read the old behaviour. The
   check is a command. Grep every literal the change edits, and every
   sentence stating the rule it changes, across `tests/`, the prompts and the
   `protected` documents.
3. **The writer cannot edit a `protected` file.** The permission classifier
   refused one writer's edit to `DESIGN.md` and `CONTEXT.md` after the
   operator's decision. The delegate made those edits by hand.
4. **The writer cannot find the pre-flight's check numbers.** Two writers
   reported that "preflight check 7" names nothing they can read. A brief
   should quote the rule rather than name it.
5. **Parallel specs collide in one test.** Each spec rewrites the queue smoke
   test's docstring and pinned lists in `tests/test_scheduler.py`. Stacking
   three meant squashing each branch and resolving that file twice.

# Third chain, 2026-09-23: SA-0141

One spec from item b-4e0868, the first slice of moving REBUT's two
structured turns onto the SDK's `output_format`. The item asked for a spike
before any spec. The spike ran first, in two runs, and cost $1.30. Its
record is `2026-09-23-structured-output-spike.md`.

## Rounds and cost

| Step | Time | Tokens |
|---|---|---|
| Spike, two runs by the operator | about 2 min | $1.30 |
| Draft | 15.1 min | 172k |
| First review | 8.7 min | 140k |
| Revise, with a prototype | 6.9 min | 33k |
| Second review | 6.3 min | 133k |
| Fixes by hand | none | none |

Neither review found a blocker. The first found five concerns and three
notes. The second found two concerns and three notes. The delegate applied
the second round's fixes by hand instead of a writer round.

## Findings by class

| Finding | Class | Check that missed it |
|---|---|---|
| A witness reached `REBUTTING` by an early return | Arrangement argued, not run | Pre-flight 10 |
| A parent's new test would go weaker unmigrated | Change breaking a live test | Pre-flight 6 |
| A payload left in text fails nothing | Migration whose miss fails nothing | none |
| A pinned sentence missing from the keep-list | Rendered sentence the change edits | Second chain's lesson 2 |
| `revert` turns a module-scope name into a skip | Witness discipline | Pre-flight 1 |
| The completion grep misses a variable payload | Migration whose miss fails nothing | none |
| A parent's test double drops the new field | Change breaking a live test | none |
| A parent's revised scope was not named | Claim about the tree | Pre-flight 5 |

No finding touched the SDK's behaviour. Every claim the spike measured held
through both reviews.

## What the pre-flight should learn

1. **Measure an external API before the writer starts.** The spike's second
   run used the production option shape. It settled a risk no reader could:
   whether `tools` and `dontAsk` hide the `StructuredOutput` tool. The
   writer then cited measurements, and no review questioned one.
2. **Prototype before the first review, not after it.** The first review's
   main concern was an arrangement. The writer's prototype then settled it
   in 7 minutes. Run the wrong versions before dispatching the reviewer.
3. **A migration needs a check that reads structure.** A payload moved from
   one field to another passes wherever it is left behind. A text grep
   misses one built from a variable. Name every carrier: helpers, doubles,
   literals. List the dict keys the payload is spelled with.
4. **A parent's tests are invisible at base.** Two findings were about test
   doubles a parent spec adds. For each parent, list the doubles its notes
   describe and whether each carries what this spec moves.
5. **The second chain's lesson 2 applies here too.** Grepping every literal
   in the edited prompts would have caught the missing keep-list sentence.
