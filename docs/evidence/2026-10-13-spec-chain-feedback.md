# Spec chain feedback, 2026-10-13

One item went through the chain at base `e9a066ec`: b-000d04, filed the same
day from `SA-0286`'s second review. It became `SA-0291`. The operator chose a
declared `subject:` field over running exempt witnesses or a rule alone.

| Spec | Item | Round 1 | Round 2 | Measured tokens |
|---|---|---|---|---|
| `SA-0291` | b-000d04 | 0B 3C 3N | 0B 2C 3N | 839 |

The draft took 18 minutes and each review took 3 to 4. Round 2's findings were
one sentence each, so the delegate applied them by hand and checked that the
spec still loads.

## Each finding by class

- **A mutant's find that the build can remove or repeat.** Three findings
  across both rounds. The cell could repeat the mutant-file condition, route it
  through a shared helper, or a parent spec could rewrite the line first. The
  pre-flight counts a find at base. It never asks whether the build the spec
  asks for keeps that text once at head.
- **A complement member no witness drives.** A set-aside witness that declares
  a subject outside the source, and a witness shared by two criteria. The same
  class as every earlier run.
- **A hand edit stating a parent's unbuilt behaviour as present.** DESIGN.md
  described `SA-0273`'s probe as running. The sentence came from an earlier
  commit, and this spec's hand edit sat beside it.
- **A sentence of the code's own vocabulary that goes stale.** `revert`'s note
  and a test docstring call a mutant's file "the subject". The new field makes
  both misleading.

## What the delegate did by hand

- Filed b-000d04 and placed it in tier 1.
- Shortened the queue smoke test's docstring to one line. The writer's added
  paragraph tripped the `prose` docstring-length ratchet at commit.
- Applied round 2's four one-sentence fixes and re-ran `load_spec`, `cite`
  and the prose check.

## The next checks

1. **A find survives the build the spec dictates.** The writer's prototype
   should be built the way the Problem says, and the find counted at its head.
   Pre-flight 1 should name this.
2. **Re-count every find at the post-parent base before dispatch.** `SA-0291`'s
   finds in `intake.py` depend on `SA-0290`'s build. A `driver.py` step could
   count them when the parent merges.
3. **The writer agent's bookkeeping adds no docstring paragraph.** Its step for
   the queue smoke test should rewrite the first line only.
