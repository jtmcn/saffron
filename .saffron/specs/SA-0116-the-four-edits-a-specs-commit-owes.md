---
id: SA-0116
title: the commit that adds a spec owes four edits to other files, and a command derives three of them
type: feature
priority: 2
depends_on: [SA-0115]
touches:
  - .claude/skills/run-saffron-spec-loop/driver.py
  - tests/test_spec_loop_driver.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
  - README.md
  - pyproject.toml
  - uv.lock
  - .saffron/**
  - ontology/**
  - tests/ontology/**
  - docs/**
  - images/**
  - harness/**
  - saffron/**
  - records/**
  - hooks/**
  - tests/records/**
  - tests/test_queued_specs.py
  - tests/test_scheduler.py
  - tests/test_citations.py
  - tests/test_context.py
  - tests/test_cli.py
  - tests/test_saffron_gates.py
  - tests/test_spec_reviewer.py
  - .claude/agents/**
  - .claude/skills/run-saffron-spec-loop/SKILL.md
  - .claude/skills/run-saffron-spec-loop/GOTCHAS.md
  - .claude/skills/run-saffron-spec-loop/REVIEW-PROMPT.md
budget_usd: 26
max_attempts: 3
max_turns: 150
acceptance:
  - claim: >-
      `driver.py bookkeeping` takes a spec id, reads the working tree and no
      commit, and resolves that id to a file through `spec_files`, which covers
      `.saffron/specs` and `.saffron/specs/done`. It prints three headed blocks
      in this order: the origin item's `specs:` line, the queue smoke test's
      paragraph, and that test's two pinned
      `assert` lines. Each of the three is headed and printed on every
      invocation that got past the three failures below, whether or not it has
      anything to report, and such an invocation exits 0. Those three each
      print a message to stderr, print nothing on stdout and exit 1: a spec id
      no file under `.saffron/specs` declares, a spec file `load_spec` refuses,
      and a file under `docs/backlog/` that `records.load.load` refuses. Under
      the first block the origin item is the first backlog item the spec's
      `## Context` cites, and the line printed is that item's `specs:` with
      this spec's id added in sorted order. Where the item already lists the
      spec, the line is printed unchanged and named as already carried. Where
      the `## Context` cites no item at all, and where it cites an id no record
      under `docs/backlog/` carries, the block says which of the two and prints
      no `specs:` line.
    witness: tests/test_spec_loop_driver.py::test_bookkeeping_prints_three_blocks_and_the_specs_line_its_origin_item_owes
  - claim: >-
      The second block prints a draft paragraph for the queue smoke test. It
      opens `Re-measured <date>, a <ordinal> time:`, the date an ISO one, and
      `<ordinal>` is the ordinal word one past the first `a <ordinal> time` in
      that test's docstring as the working tree holds it, never a count of that
      docstring's `Re-measured` lines. The word it steps to covers the plain,
      the hyphenated and the boundary-crossing forms, so `ninth` becomes
      `tenth`, `nineteenth` becomes `twentieth` and `twenty-ninth` becomes
      `thirtieth`. The rest of the paragraph carries this spec's own id and its
      origin item's id, whether it declares `depends_on` and which ids — every
      id it declares, in the order it declares them — and then one of three
      things: the position it takes among the candidates, the refusal it draws
      with the scheduler's own reason verbatim, or, for a spec `spec_files`
      resolved under `done/`, that it is retired there and so in neither list.
      Two cases print the paragraph with `<Nth>` standing where the ordinal
      would be, and a line naming which of the two it met:
      `tests/test_scheduler.py` holds no function of that name, or that
      function's docstring yields no ordinal to step — it holds no
      `a <ordinal> time`, or the word it holds is one the command's list of
      ordinals does not carry.
    witness: tests/test_spec_loop_driver.py::test_bookkeeping_drafts_the_smoke_tests_paragraph_and_steps_its_ordinal
  - claim: >-
      The third block prints two lines, each a complete `assert` statement of
      the form `tests/test_scheduler.py:2109-2110` holds: every candidate spec
      id in the order the queue gives them, and every refusal's file name in
      that same order, each cut to its first seven characters. Both come from
      one `build_queue` over `.saffron/specs` in the working tree, under a
      ledger this invocation creates empty rather than the one at
      ~/.saffron/ledger.db, with `repo_slug` set to the joel/saffron that
      `tests/test_scheduler.py:2104` passes, and with a `gh` this invocation
      supplies that reports no open pull request, so `build_queue`'s default of
      `run_gh` (`saffron/scheduler.py:731`) is never reached and no `gh`
      subprocess runs. That is the smoke test's own arrangement at
      `tests/test_scheduler.py:2098-2105`, the half of it that decides what the
      queue returns, so both lines equal what that test asserts.
      `_ledger_and_repo` is not called.
    witness: tests/test_spec_loop_driver.py::test_bookkeeping_prints_the_two_assert_lines_the_smoke_test_pins
---

## Context

Backlog item **b-7d3810** is
`docs/backlog/b-7d3810-adding-a-spec-edits-four-files-by-hand.md`, tier 2. It
was filed on 2026-09-20 from `SA-0113`, one spec drafted outside a loop run. It
is second of three in `docs/backlog/PRIORITY.md:173-174`, behind **b-b69bb6**
and ahead of **b-929465**, and tier 2 names it at `docs/backlog/PRIORITY.md:145`. Its sibling
**b-b69bb6** is the item `SA-0114` and `SA-0115` serve. This one is the other
half of the same tail: the edits `docs/agents/issue-tracker.md` asks of the
commit that adds a spec.

Every sentence here about current code was read on 2026-09-20, over the tree
this spec's own commit leaves behind. That commit sits on `3cacea55`, and it
edits `tests/test_scheduler.py`, so the line numbers below are the ones a
reader of this spec's branch finds. "This base" below names that tree. That is
not where the cell starts.
`depends_on` cuts its worktree from `SA-0115`'s branch, and `SA-0114`'s branch
sits under that one. So every `driver.py` line cited below moves by whatever
those two cells land in the same file. Grep for the name a citation gives, and
read the line you find rather than trusting the number.

**What `issue-tracker.md` asks for**. The bullet at
`docs/agents/issue-tracker.md:44-51` carries three of the four edits. It says
the commit that adds a spec updates the pinned list in
`tests/test_scheduler.py::test_saffron_queue_smoke_reproduces_this_repos_measured_queue`.
It says the same commit "adds a 'Re-measured' paragraph to the top of its
docstring". It says the commit "also lists it in its origin item's `specs:`",
naming "the item its `## Context` cites first". The fourth edit sits in a test
rather than in that bullet. `check_priority` at
`tests/records/check.py:441-491` reports "item {n} is tier {t}, but
PRIORITY.md does not name it under tier {t}", at
`tests/records/check.py:488`.
`tests/records/test_records_integrity.py:13-21` runs the whole battery over the
live tree on every `make check`.

**Two of the four are judged already, and none of the four is printed**.
`check_specs_name_their_items` at `tests/records/check.py:415-438` reports
"`{spec_id}` cites this item and is not listed" for the first edit.
`check_priority` reports the fourth. Both say what is missing. Neither says
what to write. But `check_priority`'s message carries the record and its tier,
which is nearly the whole of the line an author pastes. That is why
`PRIORITY.md` is the one of the four this spec leaves out, under
*Out of scope*. The other two are pinned by hand, in a test docstring and in
two `assert` statements, and nothing reports them at all. Measured at this
base: both functions return `[]` over the working tree. The tree is clean, so
what either reports after a spec is added is what that spec's commit owes.

**The origin item is computable**. `first_cited_item` at
`tests/records/check.py:362-368` takes the first id of the first `_ITEMS` match
in document order. `_context_section` at `tests/records/check.py:371-374` hands
it the spec's `## Context`. Measured at this base: over
`.saffron/specs/SA-0115-the-tests-that-enumerate-a-directory-a-spec-adds-to.md`
the pair returns `b-b69bb6`. `spec_files` at `tests/records/check.py:283-285`
resolves a spec id to its file over the queue and `done/`. It returns 106
entries here.

**The spec loop's driver is where a computed aid for a spec's commit lives**.
`cmd_check` at `.claude/skills/run-saffron-spec-loop/driver.py:1683-1712`
judges the ceilings comparison. It prints a sentence at
`.claude/skills/run-saffron-spec-loop/driver.py:1711` even with no blocker to
report. `_fail` at `.claude/skills/run-saffron-spec-loop/driver.py:75-78`
prints to stderr and returns 1. Its comment reads "`saffron/cli.py` reserves 2
for infrastructure". `REPO` and `SPECS_DIR` are module constants at
`.claude/skills/run-saffron-spec-loop/driver.py:34` and `:36`.

**`SA-0115` is the parent, and this command does not call its code**. All three
of `SA-0114`, `SA-0115` and this spec declare the same two `touches`
(`.saffron/specs/SA-0115-the-tests-that-enumerate-a-directory-a-spec-adds-to.md:7-9`).
The overlap refusal at `saffron/scheduler.py:679-692` would refuse this one
against either open pull request. `SA-0115` is the later of the two, so it is
the one named here. All three register a subparser in the same block of `main`,
after `.claude/skills/run-saffron-spec-loop/driver.py:1839-1843`. Nothing here
reads `cmd_cite` or `cmd_enumerators`, edits either, or rests on what either
prints.

**Every import this command needs resolves from the driver**. Measured at this
base by running a script from `.claude/skills/run-saffron-spec-loop/`, both
`records.load` and `tests.records.check` import. `uv run` puts the repository
root on the path. `cmd_size` at
`.claude/skills/run-saffron-spec-loop/driver.py:1346` is the shape to copy. It
spells `from saffron.intake import load_spec` inside the function rather than
at module scope.

**The queue is `build_queue`**. `saffron/scheduler.py:725-733` takes the specs
directory, a `repo_id` and a ledger, with keyword `repo_slug` and `gh`. The
smoke test calls it at `tests/test_scheduler.py:2103-2105`. Its ledger is
created empty by the fixture at `tests/test_scheduler.py:26-30`, and its `gh`
returns no pull request. It asserts the two lists at
`tests/test_scheduler.py:2109-2110`.

**The `prose` gate reads this driver and its tests**. `in_scope` at
`.saffron/gates/prose.py:188-193` sends a Python path under `CODE_DIRS` to the
comment and docstring rules. `CODE_DIRS` at `.saffron/gates/prose.py:48-58`
holds `tests/` and `.claude/`.

**Neither file in `touches` is scanned by `dead`**. `ROOTS` at
`.saffron/gates/dead.py:21-29` names `saffron`, `harness`, `images`, `records`,
`ontology`, `hooks` and `.saffron/gates`.

**One file holds every importer of this driver's code**.
`tests/test_spec_loop_driver.py` execs the driver through `importlib.util` at
`tests/test_spec_loop_driver.py:19-26`. One other file runs it.
`docs/evidence/scripts/2026-09-14-spec-reviewer-backtest.py` execs it the same
way at `:110` and shells `history` at `:169`, and it reaches neither the
subcommand table nor anything this change adds. Every remaining file naming
`driver.py` names it in prose and calls nothing. Those are the two agent
definitions, the skill's three documents, `.saffron/deadcode-allow.py`, the
queued and retired specs, and the backlog records. One more is
`tests/test_scheduler.py`, whose mention sits in the queue smoke test's own
docstring. The importer and the driver are in
`touches`. Every other reader is `forbidden`, `docs/**` and that script
included.

## Problem

Adding a spec edits four other files, and an author works all four out by
reading. `SA-0113`'s draft took 35.7 minutes of agent time. This tail is the
part of it that needs no judgement. The smoke test's paragraph recorded its
forty-ninth re-measurement in that commit. Every one of the forty-nine was
written by hand, from a queue the author had to compute anyway.

The command is `bookkeeping`. It takes a spec id and prints three of the four.
The fourth, `PRIORITY.md`, is cut for size, and *Out of scope* gives the
reason.

1. **The origin item's `specs:` line**. The item is what `first_cited_item`
   returns over the spec's `## Context`. That is the rule
   `check_specs_name_their_items` applies in the other direction. The line
   printed is the item's `specs:` with the spec id added and sorted, so the
   author pastes one line over one line. An item already listing the spec is
   the ordinary case on a second look at one. Printing a line that changes
   nothing, with no word about it, is what that case must not do.

2. **The smoke test's paragraph**. What it says is computable. The spec, the
   item it came from, its `depends_on`, and one of three positions: where it
   lands among the candidates, what refuses it, or retired. A spec under
   `done/` is in neither list, because `discover_specs` globs
   non-recursively (`saffron/intake.py:338`) and `_retired_ids` reads `done/`
   on its own (`saffron/scheduler.py:522-528`). The ordinal is the one part the queue does
   not carry, and the tempting derivation of it is wrong. Measured over the
   tree this spec's commit leaves, the docstring at
   `tests/test_scheduler.py:1821` opens "Re-measured 2026-09-20, a fifty-second
   time". That same docstring holds **38** lines beginning `Re-measured`.
   Fourteen of the fifty-two are no longer in the file. So the ordinal comes
   from the topmost one plus one. A count of paragraphs would run fourteen
   short and read as right.

3. **The two pinned `assert` lines**. One `build_queue` over the working
   tree's `.saffron/specs` gives both. The arrangement has to be the smoke
   test's own, because the point is that the printed lines equal the asserted
   ones. That means a ledger created empty, so that nothing is filtered. It
   means a `gh` with no open pull request, so that the overlap refusal never
   fires.

Nothing here judges. The command prints three blocks and exits 0. The author
reads them and edits two files, the origin item and
`tests/test_scheduler.py`. The first of the three blocks is judged already, by
`make check`, and a second verdict here would be a slower copy of that one.

## Out of scope

**The `PRIORITY.md` block, cut on size**. The first draft printed a fourth
block: one line per record `PRIORITY.md` leaves unplaced, from `check_priority`
over the working tree. The review's own size count put the four-block shape at
555 changed lines, and the fixes this revision applies add about 35 more. That
is inside 100 of the `feature` ceiling of 600
(`saffron/gates/core/size.py:25`), so one block comes out. `PRIORITY.md` is the
one to cut. `check_priority` at `tests/records/check.py:441-491` reports it on
every `make check`, in a message naming both the record and its tier. What the block
added over that message is the `### Tier <n>` heading to paste under, which is
a grep. The other three blocks have no such report behind them. The cost is
that an author placing a new record still finds its heading by hand, and item
b-7d3810 keeps that quarter open. `check_priority` is then imported by nothing
here. The `records/` debt this spec's commit filed as b-262df1 rests on the
three names this command does import from `tests/records/check.py`:
`spec_files`, `first_cited_item` and `_context_section`.

**Filing a record, and editing any of the four files**. The item's
`## Done looks like` is one command that prints, and the author pastes. This
command writes no file, stages nothing, and runs no git at all. It creates no
backlog record, adds no `PRIORITY.md` line and edits no docstring. The operator
settled that before this spec was written.

**A verdict, and an exit status carrying one**. Exit is 0 on every invocation
that read the spec, and 1 on the three usage failures. This is not `check`.
The half that can be judged is judged on every `make check`, by
`tests/records/test_records_integrity.py:13-21`. The other two blocks are prose
an author edits. A command exiting 1 over an unwritten paragraph would fail on
every spec, every time, forever.

**The prose half**. Wiring this into the spec loop's `SKILL.md`, into
`.claude/agents/spec-writer.md`, or into a spec review's checks is a by-hand
edit after this cell lands. `.claude/agents/**` and the skill's `SKILL.md` are
`forbidden` here. That is the order `SA-0092`, `SA-0112`, `SA-0114` and
`SA-0115` took, which item b-281f0a records as settled. So this command is
called by nothing the day it lands, and that is the expected state rather than
an omission.

**Reading a commit**. `cite` and `enumerators` take a `--base` because they
compare a spec against a tree at a commit. This one does not. All three blocks
are about the working tree as the author has it. So there is no `--base`, and
`_git`, `_spec_at` and `_ledger_and_repo` play no part.

**Every other subcommand**. `snapshot`, `next`, `record`, `drop`, `hold`,
`probe`, `status`, `stack`, `rebase`, `size`, `history`, `check`, `pattern`,
`cite` and `enumerators` keep the output and the exit status they have.

**`tests/test_scheduler.py` and `tests/records/check.py`**. Both are
`forbidden`. This command reads the first as text and imports functions from
the second. Neither is changed, and neither gains a test.

**Judging what the queue says**. A spec `build_queue` refuses is reported with
its refusal, in the paragraph and in the refusals list. The command does not
decide whether that refusal is right, and it proposes no `depends_on`.

## Notes for the agent

**This change is new code, so no criterion declares a mutant** (§5.4.1). The
subcommand, its helpers and every sentence it prints do not exist at base, and
nothing there determines their spelling. Expect the `witness` gate to report
`skip`, with a summary saying the spec declares none. `SA-0112` ran under the
same limit in this same file.

**No term here is new, so no vocabulary follow-up is owed**. `CONTEXT.md`'s
vocabulary names factory concepts. *Bookkeeping* here is the word
`docs/agents/issue-tracker.md` and item b-7d3810 use for the edits a commit
owes, and it names no factory concept. *Candidate* and *refusal* keep the
meanings `CONTEXT.md` gives them, because they come from `build_queue`
unchanged. `ontology/` is `forbidden` here.

**`bookkeeping` is the subcommand name, and its one argument is a spec id**.
`uv run .claude/skills/run-saffron-spec-loop/driver.py bookkeeping SA-0116`.
An id rather than a path, for two reasons. `spec_files` then resolves it the
same way `check_specs_name_their_items` does, and `check` takes the same
argument. Register it in `main` after the `check` parser at
`.claude/skills/run-saffron-spec-loop/driver.py:1839-1843`. The branch this
cell is cut from carries two parsers in that block that this base does not,
`SA-0114`'s `cite` and `SA-0115`'s `enumerators`. Add yours after all of them,
and edit none.

**Read `REPO` and `SPECS_DIR` inside the function, never as default argument
values**. A default binds at definition time.
`tests/test_spec_loop_driver.py:371` and `:613` monkeypatch `driver.REPO` to a
scratch root, and `tests/test_spec_loop_driver.py:1063` monkeypatches
`driver.SPECS_DIR`. The witnesses here do both. Helpers that read a tree take
the root as an argument, and `cmd_bookkeeping` passes the module's constants.

**Import inside the function, as `cmd_size` does at
`.claude/skills/run-saffron-spec-loop/driver.py:1346`**. What this command
needs is `saffron.intake.load_spec`, `saffron.scheduler.build_queue`,
`saffron.ledger.Ledger`, `records.load.load`, `records.kinds.KINDS`, and
`spec_files`, `first_cited_item` and `_context_section` from
`tests.records.check`. Importing
`tests.records.check` from the driver was measured at this base and works. It
is the right reuse rather than a convenience. `first_cited_item` is the rule
`make check` applies, and a second copy of it would drift from the thing it
exists to predict.

**The empty ledger is this invocation's own**. Create it under a temporary
directory, and close it. `tests/test_scheduler.py:2101` upserts one repo row
into its fixture's ledger before calling `build_queue`. Measured at this base,
the candidate and refusal lists are identical with that row and with
`repo_id=None`. Either is right, and no claim pins one. What criterion 3 does
pin is that `~/.saffron/ledger.db` is not the ledger read. Pass `repo_slug` as
joel/saffron, as `tests/test_scheduler.py:2104` does, and criterion 3 pins that
too. `None` is not an equivalent spelling. `build_queue` skips `_open_prs`
outright when the slug is `None` (`saffron/scheduler.py:746-750` and `:808`).
The `gh` this command supplies is then never reached, and the overlap refusal
goes unasked rather than answered. Measured at this base over the fixture
below, with `saffron.scheduler.subprocess.run` patched to raise. With the slug
set and `gh=` left off, the patched `run` is reached. With the slug `None` and
`gh=` left off it is not, and both lists come back unchanged. So the slug is
what makes the `gh` argument load-bearing at all.

**The ordinal words**. One list of the words for 1 to 99 serves both
directions. Find the docstring's word in it, and take the next. Build the list
from the nineteen unit words and the eight tens words, rather than writing
ninety-nine literals. A word the list does not hold is the same case as a
docstring carrying no `a <ordinal> time` at all.

**Name the wrong implementation each witness must kill**.

Criterion 1 kills eleven. One reads the spec from a commit rather than from the
working tree. The witness catches it by writing the spec file into a scratch
tree no repository holds. One resolves the id under `.saffron/specs` alone and
misses `done/`. Put one fixture spec under `.saffron/specs/done/`, and assert
an invocation naming its id prints the three blocks and exits 0. One takes the
last item a `## Context` cites, or any of them. Give one fixture spec a
`## Context` naming two different items, and assert the block names the first.
One heads a block only when it has a line to paste. Assert all three headings,
in order, on the invocation whose `## Context` cites no item. That first block
has no `specs:` line, and its heading must stand above the sentence saying
which case it met. Assert the same three headings, in the same order, on the
invocation whose item already carries the spec. The claim's "every invocation"
then reaches two of them. One appends the spec id to the item's `specs:` rather than sorting it
in. Give the fixture's item a `specs:` already holding an id above this spec's
and one below. Assert the printed line carries all three in order. One prints
the line and says nothing where the item already carries the id. One treats a
`## Context` citing no item as a crash. One treats a `## Context` citing an id
no record carries as the same case as no citation at all. The fixture needs a
spec of each shape, and the block must say which of the two it met. Three
more let an error escape as a traceback instead of `_fail`'s 1: an unknown spec
id, a spec file whose frontmatter `load_spec` refuses, and a record file
`records.load.load` refuses. Assert exit 1, a message on stderr, and **empty
stdout** for each. That last assertion also kills an implementation printing
its blocks before it validates.

Criterion 2 kills eleven. One leaves the `depends_on` out of the paragraph,
and one prints `depends_on[0]` alone. The refused fixture spec `SA-0203`
declares two parents, `SA-0202` and the retired `SA-0200`, and the admitted one
declares none. Assert both ids in the refused spec's paragraph, in the order
that spec declares them. Assert the words for an empty `depends_on` in the
admitted one's. One counts the docstring's `Re-measured` lines.
Every
fixture docstring in this witness must hold a count different from its own
ordinal, which is the shape the real docstring has. One steps the plain words
alone. Assert `ninth` to `tenth`, `nineteenth` to `twentieth`, and
`twenty-ninth` to `thirtieth`, three fixtures in the one `def`. One reads the
last `a <ordinal> time` in the docstring rather than the first. Put two of them
in one fixture, the second lower down and different. One raises over a
`tests/test_scheduler.py` holding no function of that name, and one raises over
a docstring holding no ordinal. Both must print the paragraph with `<Nth>` in
it, print a line saying which happened, and exit 0. One covers the candidate
case alone. Run the command over a spec the fixture queue refuses, and assert
the scheduler's own reason reaches the paragraph. Then run it over one the
queue admits, and assert the position. One treats a spec `spec_files` resolved
under `done/` as absent from the directory, or reports it as a refusal it never
drew. Run the command over criterion 1's `done/` fixture spec, and assert the
paragraph says it is retired to `done/`. One writes a paragraph naming neither
the spec nor the item it came from, which reads as a paragraph about nothing.
Assert this spec's own id and its origin item's id in the paragraph, on the
admitted run and on the refused one. One omits the date, killed by matching
the opening against a four-digit year and two two-digit fields. Matching
today's date instead would flake at midnight.

Criterion 3 kills eight. One opens the live ledger. Monkeypatch
`driver._ledger_and_repo` to raise, and assert the invocation still exits 0.
One omits `gh=` and takes `build_queue`'s default of `run_gh`, which shells the
real `gh` against joel/saffron. Patch `saffron.scheduler.subprocess.run` to
raise for every run this witness makes, and assert each still prints both lines
and exits 0. One passes `repo_slug=None`, which skips `_open_prs` and leaves
both lists unchanged, so no printed line can see it. Monkeypatch
`saffron.scheduler._open_prs` to record its two arguments and return `[]`, and
assert it recorded `joel/saffron` and a runner that is not
`saffron.scheduler.run_gh`. Measured at this base over the fixture below, that
patch records exactly that pair. One prints the candidates and forgets the
refusals, or the reverse. One sorts the candidates instead of keeping the
queue's order. Both are killed by the fixture queue below, whose candidate
order is the reverse of its filename order. One prints the first refusal alone,
or reorders them: the fixture draws two, and the asserted line is the whole
list in the queue's order. One prints the ids rather than two pasteable
statements. Assert the exact strings, `assert` keyword included, so that what
the author copies is what the test file wants. One cuts the refusals to
something other than seven characters, killed by fixture spec file names whose
eighth character differs from their seventh.

**Each witness is a plain `def`, never parametrised**. `criteria` matches a
bare node id against the names the suite collected, by exact string. A
`pytest.mark.parametrize` test collects under a name no criterion can name
(backlog item 159). Several cases in one witness is one `def` driving several.

**Each witness must fail with your source reverted**. `revert` re-runs every
test your diff adds, whether or not a criterion names it, so write no test
that passes at base. The module execs `driver.py` through `importlib.util` at
`tests/test_spec_loop_driver.py:19-26`. A reverted run then fails on the
missing attribute, which is what `revert` needs to see. Load nothing new at
module scope. A module-scope import of a name this change adds turns that run
into a collection error, which `revert` reads as `skip`.

**Build one scratch tree, and keep it small**. No git is needed anywhere in
this witness set, because the command reads no commit. One helper writes three
things under `tmp_path`. A `.saffron/specs/` holding the five specs measured
below, of the shape at `tests/test_spec_loop_driver.py:1058-1061` plus a
`## Context` line naming an item. A `docs/backlog/` holding three short
records, each one `## Problem`, `## Done looks like` and `## Record`, in that
order and drawn from those three headings alone. `_sectioned` refuses prose
before the first heading, an unknown heading, and a heading out of order
(`records/load.py:114-136`, `records/kinds.py:160`). `_check_sections` refuses
an empty `## Done looks like` under any `status` outside `done`, `superseded`
and `wontfix` (`records/load.py:140-147`, `records/kinds.py:25`). A three-line
record raises `RecordError`. This command reports that as its third failure,
so every witness but that one would be measuring the wrong thing. A `tests/test_scheduler.py` holding nothing but the smoke test's `def`
and its docstring. The helper then monkeypatches `driver.REPO` and
`driver.SPECS_DIR`. A record file name must match
`^(\d{3}|b-[0-9a-f]{6})-[a-z0-9-]+\.md$` (`records/kinds.py:190`).
`PRIORITY.md` is one of that kind's `hand_written` names
(`records/kinds.py:192`), so a fixture writing one would be skipped rather than
refused, and this fixture writes none. Do not copy this repository into the
fixture. Each witness calls the helper into its own `tmp_path`. Criterion 1
writes its extra `## Context` shapes on top of what the helper wrote.
Criterion 3 writes none, so the queue it reads is exactly the five specs
below.

**The fixture queue is measured, not reasoned**. Run at this base over a
scratch directory of exactly this shape, with the ledger created empty and
`repo_slug` set to joel/saffron. `SA-0201-alpha.md` at `priority: 3`,
`SA-0202-bravo.md` at `priority: 1`, `SA-0203-charlie.md` at `priority: 2`
declaring `depends_on: [SA-0202, SA-0200]`, `SA-0204-echo.md` at `priority: 3`
declaring `depends_on: [SA-0201]`, and `done/SA-0200-delta.md` at
`priority: 2`. `build_queue` returned the candidates `['SA-0202', 'SA-0201']`
and two refusals in this order: `SA-0203-charlie.md`, reading `depends_on
SA-0202 has no task at its current spec_sha, so nothing says it merged: it has
not run, or not since it was last edited`, and `SA-0204-echo.md`, reading that
same sentence about `SA-0201`. So the third block's second line reads
`assert [r.path.name[:7] for r in refusals] == ["SA-0203", "SA-0204"]`. Build
the fixture that way and pin those strings. The candidate order is the reverse
of the filename order, so an implementation sorting by id dies. Each refused
file's eighth character is `-` where its seventh is a digit, so a cut to any
other length dies as well. `SA-0200` is retired, which is the third position
criterion 2 asserts, and it is also the second id `SA-0203` declares. A retired
parent is credited (`saffron/scheduler.py:535-536`), so `SA-0203`'s reason
names `SA-0202` alone. Measured control at this base, the same fixture with
`SA-0200` moved out of `done/`: that reason gains ` (+1 more unmet)`
(`saffron/scheduler.py:719-720`). Pinning the suffix-free string is what holds
the retired credit, and it costs no fixture of its own.

**Every `item <id>` a witness writes must name a record `docs/backlog/`
holds**. `first_cited_item` fires only on the `_ITEMS` pattern
(`tests/records/check.py:37-41`). So each fixture `## Context` carries a phrase
like "Backlog item b-b69bb6 is the origin", in this test file's own source. `CITING` at `tests/records/check.py:23-30` includes `tests`, and
`_citing_files` skips only `tests/records/` (`:347-349`). So
`check_item_citations` (`:352-360`) reads those phrases as live citations and
reports "cites backlog item {n}, which does not exist" for an invented id.
`tests/records/test_records_integrity.py:13-21` runs that over the live tree in
the `tests` gate. The failure is new, so the baseline subtracts nothing. Both
`tests/records/**` and `docs/**` are `forbidden`, so the cell cannot file the
record that would answer it. For criterion 1's case of a citation no record
carries, cite a real live id that the scratch `docs/backlog/` omits.

**Each block is headed and printed even when it is empty**. A command printing
nothing reads the same whether it had nothing to report or never looked. That
no-op is what the headings make visible. `cmd_check` at
`.claude/skills/run-saffron-spec-loop/driver.py:1711` prints a clean-verdict
sentence for the same reason.

**The `prose` gate counts comment runs and docstrings per file**. It blocks
(`.saffron/policy.yaml:25`) and subtracts the base's failures, so a file
gaining a hit of one rule fails the attempt. Keep every comment to one or two
lines and every docstring under ten, `cmd_bookkeeping`'s included.
`hooks/prose_limit.py --file <path>` answers the same question for one file in
the working tree, and it is the cheap way to check before a gate does.

**Rename no existing test**. `census` compares collected names between base and
head, and reads a rename as a removal. The three new tests belong at the end of
`tests/test_spec_loop_driver.py`, after
`test_only_probe_takes_a_command_after_the_separator` at
`tests/test_spec_loop_driver.py:1821`.

**The shape is about 505 changed lines, and nothing here raises the tier**.
Neither file in `touches` sits under `.saffron/policy.yaml:34-58`'s
`elevate_on`, and neither is under `protected` at `.saffron/policy.yaml:61-66`.
So this task runs at `risk: standard`, where `size` is advisory against the
`feature` ceiling of 600 (`saffron/gates/core/size.py:25`). Derived per part,
the three-block shape is 161 in `driver.py` and 286 in the test file, 447. In
`driver.py`: 32 for the origin item and the `specs:` line it owes, both over
what `tests/records/check.py` exports already. Then 26 for the queue under the
smoke test's arrangement, the temporary ledger, the `gh` passed in and the
retired case included. Then 22 for the ordinal list and the step, and 14 for
finding the smoke test's docstring with `ast`. Then 26 for the paragraph and
its three positions. Last, 36 for `cmd_bookkeeping` with its three failures and
three headed blocks, and 5 to register the subcommand. In the tests: 46 for the
helper that builds the scratch tree, then 98, 88 and 54 for the three
witnesses. The four-block draft this one replaces counted 490 the same way, and
the review counted that same draft at 555. That is 13% over, on identical
content, so 447 derived here reads as about 505 on the review's basis. Take 505
as the planning figure. The second review's fixes account for 9 of those test
lines: the fifth fixture spec, the second `depends_on` id, the second refusal
in the same asserted list, and the `_open_prs` patch that pins the slug. The comparable cell in these same two files is
`SA-0112`, at 99 lines in `driver.py` and 144 in the test file. That cell built
one subcommand with five verdicts and four witnesses. This one has three blocks and
a larger fixture. Unlike `SA-0115` it parses no Python beyond one `ast` lookup
for a docstring, and it resolves no expression. Against the `size:` lines the
`history` rows print, 505 sits eleven lines above `SA-0108`'s 494, and above
`SA-0016`'s 486 and `SA-0089`'s 477. All three landed. The rows below those, at
243, 243, 177, 175, 155 and 128, are narrower cells than this one. 505 leaves
95 under the ceiling that `SA-0106` (633) and `SA-0107` (1049) overshot. That
margin is thinner than the 100 this file's specs aim for, so do not go looking
for more to do. The three blocks are the whole of it. `PRIORITY.md` is cut for size, and
a fourth thing an author wants is item b-7d3810's next entry rather than this
cell's work.

**The ceilings, against `driver.py history SA-0116`**. `max_turns: 150` stands
against a comparison row that is a floor. The line marks `SA-0106`'s peak of
101t "a floor", because that cell ended `IMPLEMENTING error_max_turns` at its
own ceiling. So the 49t of headroom printed there is narrower than it reads.
The highest peak among the printed rows that ran to its own end is `SA-0089`'s
88t, and 150 clears that by 62t. `budget_usd: 26` stands against `SA-0106`'s
pre-REVIEW total of $14.73, above by $11.27. The most any one printed row spent
after that point is `SA-0107`'s $2.81 review plus $3.17 rebut, $5.98. That sits
well inside the remainder. Both are what `SA-0114` and `SA-0115` declare
(`.saffron/specs/SA-0115-the-tests-that-enumerate-a-directory-a-spec-adds-to.md:38-40`),
for estimates of 405 and 520 lines either side of this one's 505.
`max_attempts: 3` is this file's standing level, as `SA-0112`, `SA-0114` and
`SA-0115` ran.

Commit after each coherent step. Uncommitted work dies with the cell.
