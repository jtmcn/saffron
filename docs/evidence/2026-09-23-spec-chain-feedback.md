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
