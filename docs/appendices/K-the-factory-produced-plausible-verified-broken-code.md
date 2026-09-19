---
id: K
title: "rev 13: the factory produced plausible, verified, broken code"
revisions: [13]
question: "The factory produced plausible, verified, broken code: three tasks green, one reviewed, verdict *do not merge*"
---

Three specs were run through v0.5 against a live model. All three went green on
the first attempt, produced a patch, and ended `READY_FOR_REVIEW`. One was then
applied and reviewed adversarially. The verdict was **do not merge**, on three
Critical defects.

This appendix is about that gap, because it is the whole argument of §0 and §5.5
arriving as evidence rather than as a claim.

### What passed

`SA-0004` — the `integrity` gate, 371 lines plus 579 lines of its own tests. It
passed `format`, `lint`, `types` and `tests`; its 31 new tests passed; the diff
stayed inside `touches`; the formatter was clean. Applied to the repository it
brought the test suite from 281 to 312 green.

The code was not slop. §2.1's split was clean — not one language token in a code
path, `test_paths` consulted for every classification, the Go-vocabulary tests
honest in both directions. `error` and `fail` were not blurred, and the test that
proves it is the right test to have written. Hunk consumption was count-driven
rather than marker-scanning, which is the non-obvious correct choice, with a
fixture containing diff-shaped content inside a test file to prove it. The
reviewer's own words: *"the code was close enough to correct that only actual git
output separates it."*

### What review found in under an hour

- **A diff containing `\ No newline at end of file` aborts the task.** The author
  knew about the marker — there is a branch for it — and put it in the one
  position git does not use, then wrote no test. Every task whose diff touches a
  file without a trailing newline dies as `GATE_ERROR`, unrepairable, with the
  agent never told why.
- **"An existing test was removed" was inferred from net line count.** Delete the
  failing test, write a comment longer than the test, and the gate is green —
  precisely the move §5.4 says this gate exists to stop, performed by the most
  natural thing an agent does when removing a test.
- **The same comparison fails a legitimate refactor.** Consolidating two tests
  into one `parametrize` shrinks the file and trips the gate. Blocking, with no
  override, so the loop's only repair is to pad the file — the gate teaching the
  gaming it was built to prevent.
- **The gate fails its own pull request**: sixteen violations on its own diff,
  because §5.4's "unless `touches` explicitly includes it" exemption was omitted.
- **The agent can disable the gate from inside the cell.** `export_patch` runs
  bare `git diff`, inheriting worktree config the agent can write. One
  `git config diff.srcPrefix x/` and a diff deleting the entire test suite reads
  as `pass`.

And of eleven mutants applied to the agent's own tests, **five survived**.

### Why the gates could not have caught any of it

Every one of those defects is invisible to `format`, `lint`, `types` and `tests`,
because the tests were written by the same author, against the same model of the
problem, carrying the same blind spots. The test suite is not evidence about the
behaviour anybody wanted; it is evidence that the code and its tests agree.

45. **A test written by the author of the code certifies agreement, not
    correctness.** Thirty-one passing tests and five surviving mutants are the
    same artifact described two ways. Mutation is the cheapest thing that tells
    them apart, and on agent-authored work it is not optional.

46. **Over-built for the rare case, under-built for the common one.** The parser
    handled quoted paths with spaces, binary bodies, octal escapes and mode
    changes — and mishandled the line git appends to almost every hunk. Exotica
    is visible and reads as rigour; the ordinary case is invisible because it is
    assumed. Ask of any parser: what does the *usual* input look like, and is
    there a test containing it?

47. **A proxy measure is gameable in exactly the direction the adversary wants.**
    Net lines removed stood in for "a test was removed". The adversary's move
    defeats it and a legitimate refactor trips it — wrong in both directions on
    one comparison, which is not a check but a biased coin. When a gate cannot
    measure the thing, the honest output is that it cannot, not a heuristic that
    resembles it.

### What this settles

§0 claims the product of this factory is not code but a reviewable artifact.
Three green runs and one review is the smallest experiment that could test that,
and the answer is unambiguous: **the gates were necessary and nowhere near
sufficient.** A hard-gate loop with a capable model produces work that is
plausible, internally consistent, self-tested, and wrong in ways only an
adversary looking for the wrongness will find.

§5.5's critic is therefore not a refinement to add once the loop is trustworthy.
It is the component that makes the loop's output mean anything, and v0.5's
success criterion — an agent fixing one real bug inside a cell — is met while the
factory's actual purpose is not.

48. **Gates verify what you thought to check; the critic exists for what you did
    not.** They are not two grades of one mechanism. Everything on the first list
    can be automated, and everything on the second is why the first is not enough.

### The repair loop did not fire, three times out of three

Across a new file, a schema change to code with existing tests, and a 371-line
parser, GATE ⇄ REPAIR never ran. The reason is structural rather than accidental:
**a capable agent with `Bash` runs every gate it can reach before committing.**
It ran the tests, watched them fail, fixed them, ran the formatter, and only then
committed — so the host's suite arrived after the agent had already done the
host's job.

The repair loop's real domain is therefore only the gates an agent *cannot*
self-check: the core ones, which read the host's view of the diff. That makes the
core gates the only gates that can ever fire, and it makes their absence from the
v0.5 suite — `scope` ran in no cell at all until this revision, `integrity` still
runs in none — the more serious gap of the two.

49. **A verification an agent can run itself is a verification it will have
    already passed.** Its value is not zero, but it is not caught-at-the-gate
    value; it is turns-saved value. Anything you need to *catch* has to be
    something the agent cannot see the answer to.

### Two smaller findings

**Patches perish.** `SA-0003`'s patch no longer applies: three hours of
subsequent commits moved `session.py` underneath it. A verified-green change has
a shelf life measured against the branch it was cut from, which is what §5.7's
rebase-and-re-verify and §6.1's merge train exist for, and v0.5 has neither.

**The measured cost model, three tasks in.** $1.29, $3.08 and $2.49 for plan plus
implement — against §7.1's $2–6 for implement alone. All three without a repair
attempt, so the row that matters remains unmeasured, and principle 44 still
stands.

---

