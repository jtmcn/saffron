# Spec chain feedback, 2026-11-04

The operator asked for specs for the next three tier 1 items, after the spec
loop's run 53. The delegate took b-d4b847, b-4eaaa4 and b-6677b6. It skipped
item 49, which waits on a runner role, and b-cab612, which is marked by hand.
All three touch the record's write path, so they are drafted in sequence as
one stack. One question settled each item's design arm before any writer ran.

## `SA-0334`, from b-d4b847

The writer drafted at no split: 39 lines, measured on a prototype. It ran 15
wrong versions there, and each was killed. It also measured that 306 of 371
live tasks hold no ref anywhere. The operator then settled the cutover:
`saffron migrate` runs before the cell's pull request merges.

| Round | Blockers | Concerns | Notes |
|---|---|---|---|
| First review | 1 | 4 | 3 |
| Second review | 1 | 1 | 3 |

Both blockers were one class. A claim said a path makes no fetch, and its
witness could not see a fetch.

- **Round 1.** No assertion observed "with no fetch". A build that fetched on
  every append and ignored the failure passed all four witnesses. Pre-flight
  check 1 asks which member of a set each witness drives. It does not ask
  whether a witness can observe a negative clause at all. The fix added a spy
  on the `git` argv.
- **Round 2.** The spy asserted only an absence, so a blind spy passed. A
  positional matcher misses `fetch` behind four `-c` items, and `Popen`
  bypasses a patched `subprocess.run`. The fix asserts one fetch on the
  refused append before it trusts the silence.

The concerns were the turn margin, the loops of criterion 3, a credential
prompt on the fetch, and a strict append stopping a whole `reconcile`. The
last one is the operator's settled arm, and the spec names it as out of scope.

**The check this run asks for.** A claim with a negative clause, such as "no
fetch", "no row" or "no event", needs a witness that first observes the
positive case through the same instrument. Pre-flight check 1 is the place
for it.

## `SA-0335`, from b-4eaaa4

The writer drafted at no split: 33 source lines measured, and about 3000 test
tokens over 15 criteria, one per writer the item lists. It found that eleven
existing CLI tests would push to GitHub at exit, so the spec adds a
`GIT_ALLOW_PROTOCOL=file` fixture.

| Round | Blockers | Concerns | Notes |
|---|---|---|---|
| First review | 1 | 6 | 3 |
| Second review | 0 | 3 | 4 |

- **Round 1's blocker** was the stack's class again. Re-pushing an up-to-date
  ref exits 0 and changes nothing, so "pushed once" had no instrument. The fix
  counts `git push` argv, and first sees one push for a key appended three
  times.
- **Round 2** found criterion 4's "no line names a pushed key" with no pushed
  key in its arrangement. A final pass added one, with no third review.
- The operator kept all 15 criteria. The budget went to $69 and the turns to
  360, since the closest row, `SA-0330`, was cut off at its ceiling.
- The writer measured the git behaviour in the cell image, whose git is
  2.47.3. The reviewers had assumed 2.39.5 from a stale agent prompt.

## `SA-0336`, from b-6677b6

The writer drafted at no split: 20 source lines measured. It landed the new
`RecordAppendEvent` kind by hand, in `events.py`, the vocabulary and its
render, since a cell cannot touch them.

| Round | Blockers | Concerns | Notes |
|---|---|---|---|
| First review | 2 | 2 | 3 |
| Second review | 0 | 2 | 3 |

- **Round 1's scope blocker** came from prototyping on the parents' source
  diffs without their tests. A regate test that `SA-0334` reseeds breaks once
  the append writes its task's log. A full suite stacked on both parents' whole
  diffs found that one test and no other.
- **Round 1's witness blocker** was an arrangement. Two tasks driven one after
  the other let "spec id from the newest task" pass.
- **Round 2** found a set check and a swallowed refusal that the witnesses
  would pass. A final pass pinned both, with no third review.

## What the chain says about the pre-flight

Five of the six blockers across the three specs were one class. A negative
clause or an ordering had a witness with no instrument that could see the
positive case. The sixth came from a prototype built without its parents'
tests. Two checks would have caught all six before any review:

- For each negative clause, name the instrument, and make the witness see the
  positive case through it first.
- Prototype a stacked spec on its parents' whole diffs, tests included, and run
  the full suite there.
