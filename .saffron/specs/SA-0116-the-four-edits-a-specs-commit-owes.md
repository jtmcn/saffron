---
id: SA-0116
title: the commit that adds a spec owes four edits to four other files, and every one of them is derived by hand
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
budget_usd: 24
max_attempts: 3
max_turns: 130
acceptance:
  - claim: >-
      `driver.py bookkeeping` takes a spec id, reads the working tree and no
      commit, and resolves that id to a file through `spec_files`, which covers
      `.saffron/specs` and `.saffron/specs/done`. It prints four headed blocks
      in this order: the origin item's `specs:` line, the `PRIORITY.md` lines
      owed, the queue smoke test's paragraph, and that test's two pinned
      `assert` lines. Each of the four is headed and printed on every
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
    witness: tests/test_spec_loop_driver.py::test_bookkeeping_prints_four_blocks_and_the_specs_line_its_origin_item_owes
  - claim: >-
      The second block prints one line for each record under `docs/backlog/`
      whose own `tier` `PRIORITY.md` does not name it under, and takes that
      judgement from `check_priority` over the working tree rather than from a
      second reading of the file. Each line gives the record's id, its tier and
      the `### Tier <n>` heading its entry belongs under. Three kinds of record
      draw no line: one `PRIORITY.md` already names under its own tier, one
      whose frontmatter carries no `tier` at all, and one named only in a
      violation `check_priority` reports against `PRIORITY.md` itself rather
      than against a record, which is the shape an id naming no record takes. A
      block with no line to print says the file is owed nothing.
    witness: tests/test_spec_loop_driver.py::test_bookkeeping_names_only_the_records_priority_md_leaves_unplaced
  - claim: >-
      The third block prints a draft paragraph for the queue smoke test. It
      opens `Re-measured <date>, a <ordinal> time:`, the date an ISO one, and
      `<ordinal>` is the ordinal word one past the first `a <ordinal> time` in
      that test's docstring as the working tree holds it, never a count of that
      docstring's `Re-measured` lines. The word it steps to covers the plain,
      the hyphenated and the boundary-crossing forms, so `ninth` becomes
      `tenth`, `nineteenth` becomes `twentieth` and `twenty-ninth` becomes
      `thirtieth`. The rest of the paragraph names the spec, its origin item,
      whether it declares `depends_on` and which ids, and then one of two
      things: the position it takes among the candidates, or the refusal it
      draws with the scheduler's own reason verbatim. Where
      `tests/test_scheduler.py` holds no function of that name, and where its
      docstring holds no `a <ordinal> time`, the paragraph is printed all the
      same, with `<Nth>` standing where the ordinal would be and a line saying
      which of the two happened.
    witness: tests/test_spec_loop_driver.py::test_bookkeeping_drafts_the_smoke_tests_paragraph_and_steps_its_ordinal
  - claim: >-
      The fourth block prints two lines, each a complete `assert` statement of
      the form `tests/test_scheduler.py:2109-2110` holds: the candidate spec
      ids in the order the queue gives them, and the refusals' file names cut
      to their first seven characters. Both come from one `build_queue` over
      `.saffron/specs` in the working tree, under a ledger this invocation
      creates empty rather than the one at ~/.saffron/ledger.db, with
      `repo_slug` set to joel/saffron and a `gh` reporting no open pull
      request, which is the
      arrangement at `tests/test_scheduler.py:2098-2105`. So both lines equal
      what that test asserts. `_ledger_and_repo` is not called.
    witness: tests/test_spec_loop_driver.py::test_bookkeeping_prints_the_two_assert_lines_the_smoke_test_pins
---

## Context

Backlog item **b-7d3810** is
`docs/backlog/b-7d3810-adding-a-spec-edits-four-files-by-hand.md`, tier 2. It
was filed on 2026-09-20 from `SA-0113`, one spec drafted outside a loop run. It
is third of three in `docs/backlog/PRIORITY.md:173-175`, behind **b-b69bb6**,
and tier 2 names it at `docs/backlog/PRIORITY.md:145`. Its sibling
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
what to write. The other two are pinned by hand, in a test docstring and in two
`assert` statements. Measured at this base: both functions return `[]` over the
working tree. The tree is clean, so what either reports after a spec is added
is what that spec's commit owes.

**The origin item is computable**. `first_cited_item` at
`tests/records/check.py:362-368` takes the first id of the first `_ITEMS` match
in document order. `_context_section` at `tests/records/check.py:371-374` hands
it the spec's `## Context`. Measured at this base: over
`.saffron/specs/SA-0115-the-tests-that-enumerate-a-directory-a-spec-adds-to.md`
the pair returns `b-b69bb6`. `spec_files` at `tests/records/check.py:283-285`
resolves a spec id to its file over the queue and `done/`. It returns 105
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
`tests/test_spec_loop_driver.py:19-26`. Every other file naming `driver.py` at
this base names it in prose and calls nothing. Those are the two agent
definitions, the skill's three documents, `.saffron/deadcode-allow.py`, the
queued and retired specs, and the backlog records. One more is
`tests/test_scheduler.py`, whose mention sits in the queue smoke test's own
docstring. The importer and the driver are in `touches`, and every other reader
is `forbidden`.

## Problem

Adding a spec edits four other files, and an author works all four out by
reading. `SA-0113`'s draft took 35.7 minutes of agent time. This tail is the
part of it that needs no judgement. The smoke test's paragraph recorded its
forty-ninth re-measurement in that commit. Every one of the forty-nine was
written by hand, from a queue the author had to compute anyway.

The command is `bookkeeping`. It takes a spec id and prints the four edits.

1. **The origin item's `specs:` line**. The item is what `first_cited_item`
   returns over the spec's `## Context`. That is the rule
   `check_specs_name_their_items` applies in the other direction. The line
   printed is the item's `specs:` with the spec id added and sorted, so the
   author pastes one line over one line. An item already listing the spec is
   the ordinary case on a second look at one. Printing a line that changes
   nothing, with no word about it, is what that case must not do.

2. **The `PRIORITY.md` lines**. The question is whether each record id appears
   in the file under its own tier, and `check_priority` answers it already. Its
   `tier` violations name the record and the tier. The heading an entry goes
   under is `### Tier <n>`, and `_TIER_HEADING` at `tests/records/check.py:390`
   is the pattern for it. That function's other violations are about
   `PRIORITY.md` itself, such as an id it names or strikes that no record
   carries. Those are reported against that file rather than against a record.
   They are a defect to fix rather than a line to paste, so this block leaves
   them to `make check`.

3. **The smoke test's paragraph**. What it says is computable: the spec, the
   item it came from, its `depends_on`, and either where it lands among the
   candidates or what refuses it. The ordinal is the one part the queue does
   not carry, and the tempting derivation of it is wrong. Measured over the
   tree this spec's commit leaves, the docstring at
   `tests/test_scheduler.py:1821` opens "Re-measured 2026-09-20, a fifty-second
   time". That same docstring holds **38** lines beginning `Re-measured`.
   Fourteen of the fifty-two are no longer in the file. So the ordinal comes
   from the topmost one plus one. A count of paragraphs would run fourteen
   short and read as right.

4. **The two pinned `assert` lines**. One `build_queue` over the working
   tree's `.saffron/specs` gives both. The arrangement has to be the smoke
   test's own, because the point is that the printed lines equal the asserted
   ones. That means a ledger created empty, so that nothing is filtered. It
   means a `gh` with no open pull request, so that the overlap refusal never
   fires.

Nothing here judges. The command prints four blocks and exits 0. The author
reads them and edits four files. Two of the four are judged already, by
`make check`, and a second verdict here would be a slower copy of that one.

## Out of scope

**Filing a record, and editing any of the four files**. The item's
`## Done looks like` is one command that prints, and the author pastes. This
command writes no file, stages nothing, and runs no git at all. It creates no
backlog record, adds no `PRIORITY.md` line and edits no docstring. The operator
settled that before this spec was written.

**A verdict, and an exit status carrying one**. Exit is 0 on every invocation
that read the spec, and 1 on the three usage failures. This is not `check`.
The two halves that can be judged are judged on every `make check`, by
`tests/records/test_records_integrity.py:13-21`. The other two are prose an
author edits. A command exiting 1 over an unwritten paragraph would fail on
every spec, every time, forever.

**The prose half**. Wiring this into the spec loop's `SKILL.md`, into
`.claude/agents/spec-writer.md`, or into a spec review's checks is a by-hand
edit after this cell lands. `.claude/agents/**` and the skill's `SKILL.md` are
`forbidden` here. That is the order `SA-0092`, `SA-0112`, `SA-0114` and
`SA-0115` took, which item b-281f0a records as settled. So this command is
called by nothing the day it lands, and that is the expected state rather than
an omission.

**Reading a commit**. `cite` and `enumerators` take a `--base` because they
compare a spec against a tree at a commit. This one does not. All four edits
are about the working tree as the author has it. `check_priority` over that
tree reports exactly the records left unplaced, and measured at this base it
reports none. So there is no `--base`, and `_git`, `_spec_at` and
`_ledger_and_repo` play no part.

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
`saffron.ledger.Ledger`, `records.load.load`, `records.kinds.KINDS`, and the
four functions from `tests.records.check` named in `## Context`. Importing
`tests.records.check` from the driver was measured at this base and works. It
is the right reuse rather than a convenience. `first_cited_item` and
`check_priority` are the rules `make check` applies, and a second copy of
either would drift from the thing it exists to predict.

**The empty ledger is this invocation's own**. Create it under a temporary
directory, and close it. `tests/test_scheduler.py:2101` upserts one repo row
into its fixture's ledger before calling `build_queue`. Measured at this base,
the candidate and refusal lists are identical with that row and with
`repo_id=None`. Either is right, and no claim pins one. What criterion 4 does
pin is that `~/.saffron/ledger.db` is not the ledger read.

**The ordinal words**. One list of the words for 1 to 99 serves both
directions. Find the docstring's word in it, and take the next. Build the list
from the nineteen unit words and the eight tens words, rather than writing
ninety-nine literals. A word the list does not hold is the same case as a
docstring carrying no `a <ordinal> time` at all.

**Name the wrong implementation each witness must kill**.

Criterion 1 kills ten. One reads the spec from a commit rather than from the
working tree. The witness catches it by writing the spec file into a scratch
tree no repository holds. One resolves the id under `.saffron/specs` alone and
misses `done/`. Put one fixture spec under `.saffron/specs/done/`, and assert
an invocation naming its id prints the four blocks and exits 0. One takes the
last item a `## Context` cites, or any of them. Give one fixture spec a
`## Context` naming two different items, and assert the block names the first.
One prints only the blocks with something to say.
Assert all four headings, in order, on an invocation whose second block is
empty. One appends the spec id to the item's `specs:` rather than sorting it
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

Criterion 2 kills six. One prints one line and stops. The fixture holds two
records `PRIORITY.md` leaves unplaced, and the witness asserts a line for each.
One prints every record with a missing tier line and every `PRIORITY.md`
violation beside it. Give the fixture a `PRIORITY.md` naming a bold id no
record carries, and assert that id draws no line here. One
prints every record in the directory. Give the fixture a record `PRIORITY.md`
already names under its own tier, and assert it draws nothing. One treats a
record with no `tier` as tier 0, or as unplaced. Give the fixture one with no
`tier` key, and assert it draws nothing. One prints the id and the tier without
the heading the entry goes under, killed by asserting `### Tier ` and the
number in the line. One prints an empty block with no line at all, killed by
asserting the owed-nothing sentence over a fixture whose records are all
placed.

Criterion 3 kills eight. One leaves the `depends_on` out of the paragraph. The
refused fixture spec declares one parent, and the admitted one declares none.
Assert the parent's id in the first paragraph, and the words for an empty
`depends_on` in the second. One counts the docstring's `Re-measured` lines.
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
queue admits, and assert the position. One omits the date, killed by matching
the opening against a four-digit year and two two-digit fields. Matching
today's date instead would flake at midnight.

Criterion 4 kills five. One opens the live ledger. Monkeypatch
`driver._ledger_and_repo` to raise, and assert the invocation still exits 0.
One prints the candidates and forgets the refusals, or the reverse. The
fixture's `.saffron/specs` holds two specs that queue and one child of the
second that is refused, and the witness asserts both lines. One sorts the
candidates instead of keeping the queue's order. Give the fixture's two
candidates a priority order opposite to their filename order, so that the two
readings differ. One prints the ids
rather than two pasteable statements. Assert the exact strings, `assert`
keyword included, so that what the author copies is what the test file wants.
One cuts the refusals to something other than seven characters, killed by
fixture spec file names whose eighth character differs from their seventh.

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
things under `tmp_path`. A `.saffron/specs/` holding three or four minimal
specs, of the shape at `tests/test_spec_loop_driver.py:1058-1061` plus a
`## Context` line naming an item. A `docs/backlog/` holding four short records
and a `PRIORITY.md`. A `tests/test_scheduler.py` holding nothing but the smoke
test's `def` and its docstring. The helper then monkeypatches `driver.REPO` and
`driver.SPECS_DIR`. A record file name must match
`^(\d{3}|b-[0-9a-f]{6})-[a-z0-9-]+\.md$` (`records/kinds.py:190`), and
`PRIORITY.md` is one of that kind's `hand_written` names
(`records/kinds.py:189`), so it is skipped rather than refused. Do not copy
this repository into the fixture.

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
head, and reads a rename as a removal. The four new tests belong at the end of
`tests/test_spec_loop_driver.py`, after
`test_only_probe_takes_a_command_after_the_separator` at
`tests/test_spec_loop_driver.py:1821`.

**The shape is about 490 changed lines, and nothing here raises the tier**.
Neither file in `touches` sits under `.saffron/policy.yaml:34-58`'s
`elevate_on`, and neither is under `protected` at `.saffron/policy.yaml:61-66`.
So this task runs at `risk: standard`, where `size` is advisory against the
`feature` ceiling of 600 (`saffron/gates/core/size.py:25`). The estimate is 175
in `driver.py` and 315 in the test file, derived per part. In `driver.py`: 32
for the origin item and the `specs:` line it owes, both over what
`tests/records/check.py` exports already. Then 14 for the `PRIORITY.md` lines,
which is a filter over `check_priority`'s result. Then 24 for the queue under
the smoke test's arrangement, temporary ledger included. Then 22 for the
ordinal list and the step, and 14 for finding the smoke test's docstring with
`ast`. Then 22 for the paragraph. Last, 42 for `cmd_bookkeeping` with its three
failures and four headed blocks, and 5 to register the subcommand. In the
tests: 60 for the helper that builds the scratch tree, then 95, 50, 70 and 40
for the four witnesses. Those four are wider than a first draft by about 35
lines, which is what the kills added on this spec's own self-review cost. The
comparable cell in these same two files is `SA-0112`, at 99 lines in
`driver.py` and 144 in the test file. That cell built one subcommand with five
verdicts and four witnesses. This one has four blocks rather than five
verdicts, and a larger fixture. Unlike `SA-0115` it parses no Python beyond one
`ast` lookup for a docstring, and it resolves no expression. Against the `size:`
lines the rows print, 490 sits between `SA-0089`'s 477 and `SA-0108`'s 494, and
above `SA-0016`'s 486. All three of those landed. 490 leaves 110 under the
ceiling that `SA-0106` (633) and `SA-0107` (1049) overshot. Do not go
looking for more to do. The four blocks are the whole of it, and a fifth thing
an author wants is item b-7d3810's next entry rather than this cell's work.

**The ceilings, against `driver.py history SA-0116`**. `max_turns: 130` stands
against a comparison row that is a floor. The line marks `SA-0106`'s peak of
101t "a floor", because that cell ended `IMPLEMENTING error_max_turns` at its
own ceiling. So the 29t of headroom printed there is narrower than it reads.
The highest peak among the printed rows that ran to its own end is `SA-0089`'s
88t, and 130 clears that by 42t. `budget_usd: 24` stands against `SA-0106`'s
pre-REVIEW total of $14.73, above by $9.27. The most any one printed row spent
after that point is `SA-0107`'s $2.81 review plus $3.17 rebut, $5.98. That sits
well inside the remainder. `max_attempts: 3` is this file's standing level, as
`SA-0112`, `SA-0114` and `SA-0115` ran.

Commit after each coherent step. Uncommitted work dies with the cell.
