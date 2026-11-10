# Spec chain feedback, 2026-11-10

## SA-0362 (b-66e82d), after spec loop run 58

The writer drafted in 25 minutes with no question back. Its prototype killed all 23 wrong versions with assertion failures. One review took 4 minutes and ended the chain.

**Review 1: 0 blockers, 1 concern, 5 notes.**

- The new `failures` text reaches `events.jsonl` unredacted, since `EventLog.append` redacts only `Agent` events (§4.7). The delegate recorded the choice as out of scope, beside the unredacted `detail` fields. Pre-flight 8 missed it: §4.7's redaction sentence covers every field that carries cell text.
- Two notes were wrong citations: a test quoted as declaring `dead` declares `lint`, and a `def` cited two lines low. Pre-flight 5 missed both, since `cite` resolves a line and does not read what the spec says is on it.
- One note named the second REBUT re-run, which only criterion 4 drives. Both re-runs share `_judge`, so no wrong version tells them apart.
- One note was the multi-task `watch` line, which matches how `Baseline` already prints.
- The mutant ref was absent locally. The spec declares new behaviour with no mutants.

The delegate applied the concern's answer and both citations by hand, with no second round.

## Checks to build (SA-0362)

16. Pre-flight 8 should ask, for every new field that carries cell text, what §4.7 says about redacting it.
17. `cite` should compare a quoted token beside a citation with the cited line's text, not only resolve the line.
