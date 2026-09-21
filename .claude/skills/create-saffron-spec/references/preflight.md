# The pre-flight: what to run before a reviewer reads the spec

Each check names what it catches, the command where one exists, and what the
command cannot see. `findings.md` holds the evidence each check rests on. The
numbers match the list in `SKILL.md` step 6.

Run them against the committed draft. `D` below is
`uv run .claude/skills/run-saffron-spec-loop/driver.py`, run from a checkout of
`main`, because a base older than a command does not carry it.

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

**Every failure path the spec names has a witness.** Treat the list of failures
as a set. A path with no witness ships as an escaped exception.

## 2. Criteria against each other

For each pair of criteria, find an input both of them answer. Two criteria that
answer it differently leave a cell nothing it can build. `SA-0114` and
`SA-0115` each carried one. A cut or a renumber is where they appear, so repeat
this check after any revision that removes a criterion.

## 3. Every name the spec leans on

A spec tells the cell to read a field, key a line by a value, compare two
quantities, or look something up in a directory. List each such name, and read
it at the base.

- **A field or attribute:** it exists on the type the spec reads it from.
- **A key:** it identifies one thing. A value shared by two records, such as a
  spec id that many tasks carry, ties the wrong ones together.
- **A comparison:** both sides are the same unit. A character count and a byte
  size look alike and are not.
- **A lookup:** it covers every place the thing can be. A spec lookup that
  reads only the live queue misses every spec retired to `done/`.

## 4. The data flow

Trace every value the change reads to where it comes from, and every value it
writes to where it lands.

- **Each source is reachable from `touches`.** A value only a `forbidden` file
  holds, such as a path the command line chooses, cannot reach the change.
- **Each output has a named place.** A claim that a second write "replaces"
  the first needs the spec to say where the first went.
- **Each state the flow reads exists when it runs.** A batch-end step cannot
  read a state a later step writes.
- **What a dependent spec needs.** A queued child names this spec as its
  parent. Name what the child keys by, and check this spec produces it.

## 5. Citations and claims about the tree

`D cite <spec-path> --base <commit>` resolves every `file:line` the spec quotes
and reports the ones that moved or no longer exist.

What it cannot see. Its moved-text report is right about one time in four
(b-61993a), so read each flagged line rather than acting on the list. It passes
a line zero and a reversed range. After a stack rebase, resolve commit hashes
and base branch names by hand, because the command reads paths, not history.

Then re-run every count the spec quotes, and read every sentence that says how
the code stands today at the base. The command resolves a location. It does not
check that the sentence about that location is true.

## 6. What the change breaks

`D enumerators <spec-path> --base <commit>` lists the tests that enumerate a
directory the spec's `touches` add a file to. Such a test passes at base and
fails once the spec adds its file, and baseline subtraction does not absolve a
new failure.

What it cannot see. It resolves only literal receivers (b-f45f73), so on this
repository it reports every call as unresolved. An empty report means nothing.
Read the unresolved list for any receiver that names a directory in `touches`.

Three more breaks the command does not look for.

- **A pinned line the change alters.** A golden fixture outside `touches`
  fails when the change adds a field to it.
- **A backlog id a fixture writes.** One written into a file under `tests/`
  trips the live records check. So every id a witness writes names a real
  record.
- **A test the spec deletes.** `census` fails it on every attempt.

## 7. Ceilings and size

Estimate size per part from `wc -l` of the files the change touches, against
`saffron/gates/core/size.py`. An estimate inside 100 lines of the ceiling is
split or cut before review, never argued in one. A spec that states no estimate
gets one here.

`D check <SA-ID>` compares the ceilings against cells of the same shape. A
queued sibling that has not run prints no row. Read the siblings' ceilings in
`.saffron/specs/` as well.

## 8. The design

Read the spec against `DESIGN.md`, `CONTEXT.md` and the item it came from, the
way a reviewer would. Three shapes recur.

- **An argument a section does not make.** A spec justifying a carve-out by a
  design section quotes reasoning that section contains.
- **A change that breaks a `forbidden` caller.** A note offering "one statement
  doing both" can widen a shared function. Its other callers depend on what it
  does today.
- **A departure from the origin item, unstated.** Where the spec does less or
  other than the item asked, it says so.

## 9. Bookkeeping

`D bookkeeping <SA-ID>` prints three of the four edits a spec's commit owes:
the origin item's `specs:` line, the queue smoke test's paragraph with its
ordinal stepped, and its two pinned lines. It does not place a new record in
`docs/backlog/PRIORITY.md`, which `make check` reports on its own.

What it cannot see. It has no `--base`, and reads the checkout that holds the
driver. Run it from the branch the spec is committed on.

## 10. Arrangements

A criterion can pin an order, a cut or a string. Where the helper producing it
exists at the base, run it over a scratch fixture and quote what it printed. A
queue order took three review rounds on `SA-0112` and one run to settle.

## 11. The cell's own run

Two things decide whether the cell finishes, and neither is a finding a reader
looks for.

- Commit before the full suite. The turn wall cut the first cell of `SA-0116`
  before its first commit (b-36b551). So tell a long cell to commit as each
  witness passes.
- Prose. `python3 hooks/prose_limit.py --file <path>` on every new file, from
  `main`, where the flag exists. A new file compares against zero hits, and
  `make check` passes an unstaged one.

## Adding a check

A first review finding that no check above caught is the next check. Add it
here with its command, what the command cannot see, and the finding that
motivated it. A check that finds nothing over several runs goes.
