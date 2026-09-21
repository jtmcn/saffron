# The pre-flight: what to run before a reviewer reads the spec

Each check names what it catches, the command where one exists, and what the
command cannot see. `findings.md` holds the evidence each check rests on.

Run them against the committed draft. `D` below is
`uv run .claude/skills/run-saffron-spec-loop/driver.py`.

## 1. Claim against witness

The largest class in both corpora, and the one readers keep missing.

For every claim, list each set it quantifies over. Sets hide in plain words:
"the forms of a call", "every id it declares", "the three headings", "the
usage failures", "the refusals". Name the members of each set, and mark which
member the witness drives. A set with an undriven member is a finding, because
a cell handling that one member passes.

Then check the complement. A claim that says "only the recursive forms" is also
a claim about the non-recursive ones, and the witness drives those too.

**Pin every measurement.** A writer who prototypes a behaviour on the real tree
quotes what it printed. A witness asserts that output, or the cell does not
build it. `SA-0115` quoted 19 of 35 calls resolving, pinned nothing, and
shipped a resolver that resolves none.

## 2. Criteria against each other

For each pair of criteria, find an input both of them answer. Two criteria that
answer it differently leave a cell nothing it can build. `SA-0114` and
`SA-0115` each carried one. A cut or a renumber is where they appear, so repeat
this check after any revision that removes a criterion.

## 3. Citations

`D cite <spec-path> --base <commit>` resolves every `file:line` the spec quotes
and reports the ones that moved or no longer exist.

What it cannot see. Its moved-text report is right about one time in four
(b-61993a), so read each flagged line rather than acting on the list. It passes
a line zero and a reversed range. After a stack rebase, resolve commit hashes
and base branch names by hand, because the command reads paths, not history.

## 4. Claims about the tree

Re-run every count the spec quotes, and read every sentence that says how the
code stands today at the base. The command in step 3 resolves a location. It
does not check that the sentence about that location is true.

## 5. What the change breaks

`D enumerators <spec-path> --base <commit>` lists the tests that enumerate a
directory the spec's `touches` add a file to. Such a test passes at base and
fails once the spec adds its file, and baseline subtraction does not absolve a
new failure.

What it cannot see. It resolves only literal receivers (b-f45f73), so on this
repository it reports every call as unresolved. An empty report means nothing.
Read the unresolved list for any receiver that names a directory in `touches`.

Two more breaks the command does not look for. A fixture writing a backlog id
into a file under `tests/` trips the live records check. So every id a witness
writes names a real record. And a test the spec asks the cell to delete fails
`census` on every attempt.

## 6. Ceilings and size

`D check <SA-ID>` compares the ceilings against cells of the same shape.

What it cannot see. A queued spec of the same shape that has not run prints no
row. Find the siblings in `.saffron/specs/` and read their ceilings as well.

Estimate size per part from `wc -l` of the files the change touches, against
`saffron/gates/core/size.py`. An estimate inside 100 lines of the ceiling is
split or cut before review, never argued in one.

## 7. Bookkeeping

`D bookkeeping <SA-ID>` prints three of the four edits a spec's commit owes:
the origin item's `specs:` line, the queue smoke test's paragraph with its
ordinal stepped, and its two pinned lines. It does not place a new record in
`docs/backlog/PRIORITY.md`. `make check` reports that one on its own.

## 8. Arrangements

A criterion can pin an order, a cut or a string. Where the helper producing it
exists at the base, run it over a scratch fixture and quote what it printed. A queue order took three review rounds on `SA-0112` and one run to
settle. Arguing an arrangement a command can answer costs a round every time.

## 9. The cell's own run

Two things decide whether the cell finishes, and neither is a finding a reader
looks for.

- Commit before the full suite. The turn wall cut the first cell of `SA-0116`
  before its first commit (b-36b551). So tell a long cell to commit as each
  witness passes.
- **Prose.** `python3 hooks/prose_limit.py --file <path>` on every new file. A
  new file compares against zero hits, and `make check` passes an unstaged one.

## Adding a check

A first review finding that no check above caught is the next check. Add it
here with its command, what the command cannot see, and the finding that
motivated it. A check that finds nothing over several runs goes.
