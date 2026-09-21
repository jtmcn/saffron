# What the reviews found, and what the cells found after them

The evidence this skill's checks come from. Two corpora over the same four
specs, `SA-0113` to `SA-0116`, written 2026-09-20 and run through cells in the
spec loop's runs 11 and 12.

Read the second corpus first. It is the one the checks exist to empty.

## Corpus 2: what survived every review and a cell found

Each of the four specs passed two authoring reviews and more rounds in the
loop's step 1b. Each then reached a cell, and the cell or the review seats
after it found defects no reader had.

| Spec | Found after the cell | Where |
|---|---|---|
| `SA-0113` | four witnesses passed with the behaviour they guard broken | `748c6976` |
| `SA-0113` | the prompt told a session it could not see what its diff shows | `748c6976` |
| `SA-0114` | an anchored bare citation never reached the past-end report | `fb8d1200` |
| `SA-0114` | `cite` flags moved text at about one hit in four | b-61993a |
| `SA-0115` | thirteen mutants survived, six in cases the spec named and the fixture left out | `9d6b5ceb` |
| `SA-0115` | `enumerators` resolves only literal receivers, so all 35 calls here are unresolved | b-f45f73 |
| `SA-0116` | the witness never checked the three headings' order or presence | `e00d8b7d` |
| `SA-0116` | its first cell was cut by the turn wall before any commit | b-36b551 |

Three lessons in that table, and each one is a check in `preflight.md`.

**Witness holes are the dominant class, and reading does not find them.** Four
in `SA-0113`, thirteen surviving mutants in `SA-0115`, one in `SA-0116`. Two
authoring reviews and the loop's step 1b read all three specs. The seats found
the holes by breaking the code and running the witness. Item b-2750d5 is the
cell doing that itself.

**A measurement no witness pins is not built.** `SA-0115`'s writer prototyped
the resolver and measured 19 of 35 calls resolving on this tree. The spec said
no criterion asserted that number, a reviewer marked it unverified, and the
cell shipped a resolver that resolves none. The prototype proved the claim was
buildable, and nothing made the cell build it.

**A stack rebase moves every citation in a spec.** `SA-0116`'s step 1b found
citations naming `SA-0115`'s branch as base. It also found commit hashes from
before the operator's rebase, which a cell cut from main cannot resolve.

## Corpus 1: what eight authoring review rounds found

The same four specs, reviewed twice each before any cell ran, about 45 findings
in all. Classed by what could have caught each one before a reviewer read it.

| Class | Count | Examples |
|---|---|---|
| A claim over a set whose witness drives one member | 14 | recursion forms, the `os` alias, the refusals list |
| A claim about the tree that stopped being true | 14 | citations off by a line, a file count, a `forbidden` claim |
| Two criteria disagreeing on one input | 4 | an enumerator report against an unresolved line |
| An arrangement argued rather than run | 3 | candidate order, the refusal string |
| Size or ceilings | 4 | a thin margin, siblings `history` could not see |
| A change breaking a live check or test | 3 | a globbed directory, fixture ids the records check scans |
| Judgement about the design | 3 | withholding a node id the diff discloses |

Two findings in the first corpus were false: a reviewer's `terms` claim, which
the gate's `AVOIDED` set disproves. Both were answered with evidence and not
applied.

## The two corpora together

Corpus 1 is what readers catch, and corpus 2 is what they miss. The quantified
set class appears in both. Readers caught 14 instances before the cells ran,
and the cells still found at least seven more. A rule in
`docs/agents/issue-tracker.md` names the class, and item b-250dc7 records that
the rule did not stop a writer producing it.

So the target this skill measures itself by is two numbers, not one. The first
review finds nothing. And the cell's review seats find nothing the pre-flight
could have run.
