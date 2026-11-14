# Spec chain feedback, 2026-11-14

Continues `docs/evidence/2026-11-13-spec-chain-feedback.md`. Check numbers
carry on from its 48. Two writers drafted in parallel after spec loop run
69 merged, each in its own worktree cut from `3495ef85`.

## SA-0389 (b-d2b6b3)

`revert` reads a spec's declared renames, by `census`'s own acceptance
rule, so an accepted pair's new name is not a new test. The finishing
layer's half of the item stays open.

**Review 1: 0 blockers, 3 concerns, 2 notes.** The writer revised.

- The notes said `revert_gate`'s docstring held nine lines. The prose
  gate counts ten, its limit. Pre-flight 5 missed a count it could run.
- "Names are compared whole" drove only the text after the last `::`. A
  prefix match on a parametrised family passed. Pre-flight 1 missed the
  member. Check 51 names it.
- The summary clause was claimed for every summary, and only four carry
  the exempt names. Pre-flight 1 missed the set's real bounds.
- An accepted rename that is also exempt, and a name collected twice,
  had no driven member. Pre-flight 1 missed both.

**Review 2: 1 blocker, 1 concern, 4 notes.** Applied by hand. No summary
held more than two left-out names, so a clause cut to three passed. Three
other name lists in the same module cut to three. Check 50 names it. The
concern asked to run the wrong versions. The writer had applied all 14 in
its prototype, so it was answered with that evidence. The extra pair
priced the estimate at the `bug` threshold, so the spec is typed
`feature`.

## SA-0390 (b-990bd9)

One function in `phases/package.py` builds a task's queue line, and the
three sites with an outcome call it.

**Review 1: 1 blocker, 1 concern, 3 notes.** The writer revised.

- Three wrong versions changed a note, a risk and a concern count. The
  witness held each at its default, so none could die. The prototype
  already pinned the values, and the spec text did not. Check 49 names it.
- One claim compared five rows on ten fields, and one row has no
  rebuttal. The Notes split the rows, and the claim did not. Pre-flight 2
  missed a claim against its own Notes.

**Review 2: 0 blockers, 2 concerns, 3 notes.** Applied by hand. Both
concerns were the round 1 class again: the caller fields and the push
note sat at their defaults. A citation to a line inside a test now names
that test, for `cite`'s rule from `SA-0384`.

## Checks to build

49. For each wrong version, the witness's input holds a non-default value
    in the field that version changes. A default hides the change.
50. A claim about every member of a printed list drives at least four
    members, so a list cut to three dies.
51. A claim that names are compared whole drives a prefix and a substring
    case, beside the short-name case.
