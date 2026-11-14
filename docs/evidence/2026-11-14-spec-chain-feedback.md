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

## SA-0393 (b-249808)

The `integrity` gate fails an added line that cites a spec id of the
task's prefix, unless the id is the task's own or a spec file's.

**Review 1: 0 blockers, 4 concerns, 5 notes.** The writer revised.

- The bounds left alone the commonest citation form, `"""SA-NNNN`, and
  every id after the first in a slash list. Pre-flight 1 missed the forms
  the bounds treat as fixtures.
- The spec read ids from file names. `_retired_ids` reads them from
  frontmatter, and its comment says why. Pre-flight 3 missed a rule the
  base states in a comment.
- No judged id sat at a line's start.

**Review 2: 0 blockers, 3 concerns, 4 notes.** Applied by hand. Each
concern was an undriven member: the listing's exit codes, the slash
rule's left side and a nested file under `done/`.

## SA-0394, SA-0395 and SA-0396 (b-7fc792)

The writer split the item twice. `driver.py check` priced each draft
over 80% of the size ceiling. It counts test lines in `estimated_lines`
and applies the 1.78 overrun to them, though the `size` gate counts no
test path. SA-0394 adds `mirror.files_after`. SA-0395 adds
`probe.inert_edit`. SA-0396 wires it into REVIEW.

**SA-0394, review 1: 0 blockers, 3 concerns.** The writer revised. A
`GitError` collapsed into `None`, the move had no witness, and the spec
named a "probe cell". **Review 2: 1 concern**, applied by hand: the
empty-dict calls passed no paths, so a build mapping each path to `None`
passed.

**SA-0395, review 1: 2 blockers.** The rule parsed Python with `ast`
inside `saffron/`, against §2.1. The operator's delegate moved it behind
repo-declared line patterns, the `witness:` precedent. The `probes:`
block landed by hand, since `Policy` refuses unknown keys and the setup
template sits under `.claude/`. **Review 2: 1 blocker, 3 concerns.** The
writer revised once more. No witness pattern held a quantifier brace, so
`str.format` passed. An added `def` mid-block took over the lines below
it, and a language-free indent guard closed that.

**SA-0396, review 1: 1 blocker, 3 concerns.** The writer revised. The
witness drove an unstacked spec, where `tree_base` equals `base_sha`. A
read at the wrong base passed it, and refused nothing in every stacked
cell. **Review 2: 2 blockers, 1 concern.** Applied by hand. No witness
sent a pair with no edit through the read, so a read over every pair
raised and orphaned the task. A placement the claim named was undriven,
and it moved to Out of scope. The Notes now name the `mirror_ops` alias,
since the function's own `mirror` parameter would be shadowed.

## Checks to build

52. A rule placed in `saffron/` is read against §2.1 before the draft.
    One that names a language, a file suffix or a parser is the repo's.
53. A witness of a read keyed by a base drives a stacked spec, so
    `tree_base` and `base_sha` differ.
54. A pattern a repo declares carries every metacharacter its loader must
    survive, a quantifier's braces among them.
55. `driver.py check` prices only the lines the `size` gate counts.
56. A read over a list whose entries may lack a field drives an entry
    without it.
