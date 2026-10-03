# Spec chain feedback, 2026-10-02

Three backlog items became three specs in one stack. The operator filed the
items from a question about queue visibility. They answered five design
questions before any writer ran.

| Spec | Item | What it builds |
|---|---|---|
| `SA-0197` | b-2d09de | `saffron watch` with no spec id follows every task |
| `SA-0198` | b-49a2f7 | the batch header's trailing accept rate |
| `SA-0199` | b-0703c8 | a live queue row per phase, rewritten on `ORPHANED` |

The stack is `SA-0197` then `SA-0198` then `SA-0199`, on the backlog branch.
Every spec sits behind the queued chain that ends at `SA-0152`.

## Cost

Wall time per agent, from each agent's own report.

| Spec | Draft | Review 1 | Revise 1 | Review 2 | Revise 2 |
|---|---|---|---|---|---|
| `SA-0197` | 10.3 min | 3.8 min | 5.8 min | 1.4 min | 9.4 min |
| `SA-0198` | 15.0 min | 5.4 min | 7.4 min | 1.6 min | by hand |
| `SA-0199` | 22.5 min | 6.5 min | 8.3 min | 3.1 min | by hand |

## Rounds

| Spec | Round | Blockers | Concerns | Notes |
|---|---|---|---|---|
| `SA-0197` | 1 | 1 witness | 1 | 5 |
| `SA-0197` | 2 | 1 witness | 1 | 3 |
| `SA-0198` | 1 | 1 witness | 6 | 3 |
| `SA-0198` | 2 | 0 | 1 | 2 |
| `SA-0199` | 1 | 3 witness | 2 | 4 |
| `SA-0199` | 2 | 0 | 2 | 4 |

No first review came back empty. Every blocker was a witness that let a
listed wrong version pass.

## Each finding by class

- **A kill measured on the host and not in the cell.** `SA-0197`'s order
  check relied on how macOS lists three directories. A Linux cell lists them
  another way. The writer ran its prototype on the host only. No check covers
  this class. Check 10 should ask where a measurement ran.
- **A set member no witness drives.** This is check 1, as in every run so far.
  - `SA-0197`: a directory that joins late and sorts first.
  - `SA-0199`: a raise before any phase, and a second `REPAIRING`.
  - `SA-0199`: the header on a live write.
- **A test double that skips a write production makes.** `SA-0198`'s
  `run_one_cell` double wrote no state. A rate read before the cell's own
  write then passed. This is check 4, the data flow, applied to a double.
- **A witness compared against its own table.** `SA-0198` checked the set
  against a table the cell writes. Check 1 should name this shape.
- **Wrong versions the writer listed and never ran.** `SA-0199` listed 29 and
  ran 25. The review found three of the four unrun ones alive. Running every
  listed wrong version would have caught all three.
- **A ceiling raised without its partner.** `SA-0197`'s revision raised turns
  and kept the budget. Check 7 should recompute both after a revision.
- **Two queued specs sharing a file with no edge.** `SA-0197` and `SA-0199`
  both touch `saffron/cli.py`. The pre-flight drove `build_queue` with no open
  pull request, and the overlap refusal needs one. Check 3 should read the
  overlap between sibling specs as well as parents.
- **My own hand edit.** The new §6 paragraph said a settled task "waits on
  nobody". Four settled states are ones §6 says need the operator. Check 8
  reads the spec against the documents. It should read the hand edits too.
- **An instruction a cell cannot follow.** `SA-0198` told the cell to stop on
  a red test. A red `tests` gate ends the cell `EXHAUSTED` instead. No check
  covers this class.

## Settled by hand

Three things went in by hand rather than through a writer.

- Writers twice filed a by-hand item for a glossary change. Both edits landed
  in the spec's own pull request instead, as the operator ruled on
  2026-09-23.
- Each writer appended a paragraph to the smoke test's docstring, and the
  `prose` hook refused it. The top paragraph was rewritten in place each time.
- The last round of `SA-0198` and `SA-0199` needed sentence edits only.

## Environment

`tests/test_spec_loop_driver.py::test_a_live_saffron_cell_is_found_by_its_spec_id`
failed twice under concurrent suites in other worktrees. It passed alone each
time. It reads the host's process table.
