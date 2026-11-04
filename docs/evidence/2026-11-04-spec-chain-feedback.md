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
