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
      paragraph, and that test's two pinned `assert` lines. Three failures each
      print a message to stderr, print nothing on stdout and exit 1. The first
      is a spec id no file under `.saffron/specs` declares. The second is a
      spec file `load_spec` refuses, as one whose frontmatter is not YAML. The
      third is a file under `docs/backlog/` that `records.load.load` refuses,
      as a record the spec does not cite whose sections are out of order. Every
      other invocation prints all three headings in order and exits 0, in each
      of the first block's four cases below and for a spec under `done/`. The
      origin item is the first backlog item the spec's `## Context` cites. In
      the first case the block prints that item's whole `specs:` line with this
      spec's id added in sorted order. So `specs: [SA-0100, SA-0300]` becomes
      `specs: [SA-0100, SA-0201, SA-0300]`, and `specs: []` becomes
      `specs: [SA-0200]`. In the second, where the item already lists the spec,
      the line is printed unchanged and named as already carried. The item's id
      is numbered, as `32`, or random, as `b-7d3810`, and both resolve. In the third
      the `## Context` cites no item at all. In the fourth it cites an id no
      record under `docs/backlog/` carries. Those two print no `specs:` line,
      and the block says which of the two it met.
    witness: tests/test_spec_loop_driver.py::test_bookkeeping_prints_three_blocks_and_the_specs_line_its_origin_item_owes
  - claim: >-
      The second block prints a draft paragraph for the queue smoke test. It
      opens `Re-measured <date>, a <ordinal> time:` with an ISO date, and with
      `an` in place of `a` before a word that starts with `e`. The `<ordinal>`
      is the word one past the first `a <ordinal> time` or `an <ordinal> time`
      in that test's docstring as the working tree holds it. It is never a
      count of that docstring's `Re-measured` lines. The step covers each form
      a word takes on either side of it: `ninth` becomes `tenth`, `nineteenth`
      becomes `twentieth`, `twenty-ninth` becomes `thirtieth`, `fiftieth`
      becomes `fifty-first`, `fifty-second` becomes `fifty-third`, `seventh`
      becomes `an eighth` and `an eleventh` becomes `a twelfth`. The article
      reads the whole word's first letter, so `fifty-seventh` becomes
      `a fifty-eighth` and `an eightieth` becomes `an eighty-first`. The paragraph
      names this spec's id, and the id its `## Context` cites first where it
      cites one. It names every id the spec declares in `depends_on`, in the
      order declared, or says it declares none. It ends in one of three
      positions. An admitted spec reads `candidate <n> of <m>`, with `<n>`
      counted from one. A refused spec carries the scheduler's reason verbatim.
      A spec `spec_files` resolved under `done/` is named as retired there, and
      so in neither list. Two cases print the paragraph with `<Nth>` where the
      ordinal would stand, and a line naming which case it met. In the first,
      `tests/test_scheduler.py` is missing, does not parse, or holds no function
      of the smoke test's name. In the second, that function has no docstring,
      or its docstring yields no ordinal to step. It holds no
      `a <ordinal> time`, or it holds a word the command's list of ordinals
      lacks, or it holds `ninety-ninth`, the last word that list carries. Each
      of these prints all three headings and exits 0.
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
      `_ledger_and_repo` is not called, and no ledger file appears under the
      home directory's `.saffron/`.
    witness: tests/test_spec_loop_driver.py::test_bookkeeping_prints_the_two_assert_lines_the_smoke_test_pins
---

## Context

Backlog item **b-7d3810** is
`docs/backlog/b-7d3810-adding-a-spec-edits-four-files-by-hand.md`, tier 2. It
was filed on 2026-09-20 from `SA-0113`, one spec drafted outside a loop run. It
follows **b-b69bb6** in the tier-2 passage at `docs/backlog/PRIORITY.md:174-179`,
which strikes **b-929465** as done by #392. Tier 2 names it at
`docs/backlog/PRIORITY.md:145`. Its sibling **b-b69bb6** is the item `SA-0114`
and `SA-0115` serve. This one is the other half of the same tail: the edits
`docs/agents/issue-tracker.md` asks of the commit that adds a spec.

Every sentence here about current code was read on 2026-09-21 at `f3dcae7c`.
That commit is the head of `origin/saffron/SA-0115`, the branch `SA-0115`'s cell
pushed, and it is the base this cell is cut from. It carries `SA-0114`'s `cite`
and `SA-0115`'s `enumerators`, with their tests. "This base" below names that
commit. `main` holds neither parent's code, so its line numbers in the two
`touches` files differ from the ones cited here.

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
base: both functions return `[]` over the tree. The tree is clean, so
what either reports after a spec is added is what that spec's commit owes.

**The origin item is computable**. `first_cited_item` at
`tests/records/check.py:362-368` takes the first id of the first `_ITEMS` match
in document order. `_context_section` at `tests/records/check.py:371-374` hands
it the spec's `## Context`. Measured at this base: over
`.saffron/specs/SA-0115-the-tests-that-enumerate-a-directory-a-spec-adds-to.md`
the pair returns `b-b69bb6`. `spec_files` at `tests/records/check.py:283-285`
resolves a spec id to its file over the queue and `done/`. It keys on the file
name alone (`tests/records/check.py:274-280`), and it returns 106 entries here.

**The spec loop's driver is where a computed aid for a spec's commit lives**.
`cmd_check` at `.claude/skills/run-saffron-spec-loop/driver.py:1684-1713`
judges the ceilings comparison. It prints a sentence at
`.claude/skills/run-saffron-spec-loop/driver.py:1712` even with no blocker to
report. `_fail` at `.claude/skills/run-saffron-spec-loop/driver.py:76-79`
prints to stderr and returns 1. Its docstring reads "`saffron/cli.py` reserves
2 for infrastructure". `REPO` and `SPECS_DIR` are module constants at
`.claude/skills/run-saffron-spec-loop/driver.py:35` and `:37`.

**`SA-0115` is the parent, and this command does not call its code**. All three
of `SA-0114`, `SA-0115` and this spec declare the same two `touches`
(`.saffron/specs/SA-0115-the-tests-that-enumerate-a-directory-a-spec-adds-to.md:7-9`).
Without a `depends_on`, the overlap refusal at `saffron/scheduler.py:679-692`
would refuse this one against either open pull request. The exemption at
`saffron/scheduler.py:671-674` passes the ancestors `depends_on[0]` walks.
`SA-0115` is the later of the two, so it is the one named here. The subparsers
register in one block of `main`. `check` is at
`.claude/skills/run-saffron-spec-loop/driver.py:2214-2218`, `cite` at
`:2223-2228`, and `enumerators` at `:2230-2235`, the last before the argv split.
Nothing here reads `cmd_cite` or `cmd_enumerators`, edits either, or rests on
what either prints.

**Every import this command needs resolves from the driver**. Both
`records.load` and `tests.records.check` import from a script run under
`uv run`, measured at this base. `uv run` puts the repository root on the
path. `cmd_size` at `.claude/skills/run-saffron-spec-loop/driver.py:1346-1347`
is the shape to copy. It spells `from saffron.intake import load_spec` inside
the function rather than at module scope.

**The queue is `build_queue`**. `saffron/scheduler.py:725-731` takes the specs
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
`tests/test_spec_loop_driver.py:20-27`. One other file runs it.
`docs/evidence/scripts/2026-09-14-spec-reviewer-backtest.py` execs it the same
way at `:110-114` and shells `history` at `:169`. It reaches neither the
subcommand table nor anything this change adds. Every remaining file naming
`driver.py` names it in prose and calls nothing. Those are the two agent
definitions, the skill's three documents, `.saffron/deadcode-allow.py`, the
queued and retired specs, the backlog records, and evidence and plans under
`docs/`. One more is `tests/test_scheduler.py`, whose mention sits in the
queue smoke test's own docstring. The importer and the driver are in
`touches`. Every other reader is `forbidden`, `docs/**` and that script
included.

## Problem

Adding a spec edits four other files, and an author works all four out by
reading. `SA-0113`'s draft took 35.7 minutes of agent time. This tail is the
part of it that needs no judgement. `SA-0113`'s commit wrote the smoke test's
forty-ninth re-measurement. Its docstring now opens at the fifty-second
(`tests/test_scheduler.py:1821`). Every one of the fifty-two was written by
hand, from a queue the author had to compute anyway.

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
   non-recursively (`saffron/intake.py:340`) and `_retired_ids` reads `done/`
   on its own (`saffron/scheduler.py:523-528`). The ordinal is the one part
   the queue does not carry, and the tempting derivation of it is wrong. The
   docstring at `tests/test_scheduler.py:1821` opens "Re-measured 2026-09-20,
   a fifty-second time". That same docstring holds **38** lines beginning
   `Re-measured`. Fourteen of the fifty-two are no longer in the file. So the
   ordinal comes from the topmost one plus one. A count of paragraphs would
   run fourteen short and read as right. The article varies too.
   `tests/test_scheduler.py:2048` reads "an eighteenth time".

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
over the working tree. The first review counted the four-block shape at 555
changed lines, inside 100 of the `feature` ceiling of 600
(`saffron/gates/core/size.py:25`). So one block comes out. `PRIORITY.md` is the
one to cut. `check_priority` at `tests/records/check.py:441-491` reports it on
every `make check`, in a message naming both the record and its tier. What the
block added over that message is the `### Tier <n>` heading to paste under,
which is a grep. The other three blocks have no such report behind them. The
cost is that an author placing a new record still finds its heading by hand,
and item b-7d3810 keeps that quarter open. `check_priority` is then imported by
nothing here. The `records/` debt this spec's commit filed as b-262df1 rests on
the three names this command does import from `tests/records/check.py`:
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

**What the paragraph says with no origin item**. Criterion 2 pins the origin
item's id where the `## Context` cites one. What the paragraph says in its
place for a spec citing none is the cell's choice, and no witness reads it.

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
argument. Register it after the `enumerators` parser at
`.claude/skills/run-saffron-spec-loop/driver.py:2230-2235`, before the argv
split at `:2237-2241`, and edit no other parser.

**Read `REPO` and `SPECS_DIR` inside the function, never as default argument
values**. A default binds at definition time.
`tests/test_spec_loop_driver.py:372` and `:614` monkeypatch `driver.REPO` to a
scratch root, and `tests/test_spec_loop_driver.py:1064` monkeypatches
`driver.SPECS_DIR`. The witnesses here do both. Helpers that read a tree take
the root as an argument, and `cmd_bookkeeping` passes the module's constants.

**Import inside the function, as `cmd_size` does at
`.claude/skills/run-saffron-spec-loop/driver.py:1346-1347`**. What this command
needs is `saffron.intake.load_spec`, `saffron.scheduler.build_queue`,
`saffron.ledger.Ledger`, `records.load.load`, `records.kinds.KINDS`, and
`spec_files`, `first_cited_item` and `_context_section` from
`tests.records.check`. Importing `tests.records.check` from the driver was
measured at this base and works. It is the right reuse rather than a
convenience. `first_cited_item` is the rule `make check` applies, and a second
copy of it would drift from the thing it exists to predict.

**The empty ledger is this invocation's own**. Create it under a temporary
directory, and close it. `tests/test_scheduler.py:2101` upserts one repo row
into its fixture's ledger before calling `build_queue`. Measured at this base
over the fixture below, `repo_id=None` gives the same two lists the smoke test
pins. Either is right, and no claim pins one. What criterion 3 does pin is
that no ledger under the home directory is read or made. Pass `repo_slug` as
joel/saffron, as `tests/test_scheduler.py:2104` does, and criterion 3 pins that
too. `None` is not an equivalent spelling. `build_queue` skips `_open_prs`
outright when the slug is `None` (`saffron/scheduler.py:746-750` and `:808`).
The `gh` this command supplies is then never reached, and the overlap refusal
goes unasked rather than answered. Measured at this base over the fixture
below, with `saffron.scheduler.subprocess.run` patched to raise: with the slug
set and `gh=` left off, the patched `run` is reached. So the slug is what makes
the `gh` argument load-bearing at all.

**The ordinal words**. One list of the words for 1 to 99 serves both
directions. Find the docstring's word in it, and take the next. Build the list
from the nineteen unit words and the eight tens words, rather than writing
ninety-nine literals. The list ends at `ninety-ninth`, so that word has no next
one. A docstring holding it is the no-ordinal case, as is a word the list does
not hold. Every word needing `an` starts with `e`: `eighth`, `eleventh`,
`eighteenth`, `eightieth` and the `eighty-` words.

**Name the wrong implementation each witness must kill**. The cases below are
named per run, and each run kills several. Keep every one of them. A fixture
compacted to fit the size ceiling is how `SA-0115`'s review found six mutants
alive in cases its spec named.

Criterion 1 makes nine runs and kills twenty wrong implementations. The
scratch tree sits in no repository, which kills reading the spec from a
commit. Five runs succeed, and each asserts the three headings in order and
exit 0. That kills an implementation heading a block only when it has a line
to paste.

- **`SA-0201`**, in the queue. Assert the first block's line is exactly
  `specs: [SA-0100, SA-0201, SA-0300]`, key and brackets included. This one
  run kills five. One appends the id, and one prints the ids with no
  `specs: [` around them. One takes the last item the `## Context` cites, and
  one takes any of them. One reads the whole file rather than the
  `## Context`. The helper below gives `SA-0201` the arrangement each
  needs.
- **`SA-0203`**, whose item already lists it. Assert `specs: [SA-0203]`
  unchanged, and a word saying it is already carried. That kills an
  implementation printing the line and saying nothing.
- **`SA-0200`**, under `done/`. Assert `specs: [SA-0200]` exactly. That kills
  resolving the id under `.saffron/specs` alone, and a join that crashes or
  prints `[, SA-0200]` over an empty list. Its origin is record C, the one
  numbered item. That kills finding a record by file name, as by `name[:8]`
  or a glob of `f"{n}-*.md"`. The file is `032-`, so either reports an id no
  record carries.
- **`SA-0205`**, written by this witness with a `## Context` citing no item.
  **`SA-0206`**, written with a `## Context` citing a real live id the scratch
  `docs/backlog/` omits. Assert no `specs: [` in either output, and a
  different case line in each. That kills treating either as a crash, and
  treating one as the other.

Four runs fail, and each asserts exit 1, a message on stderr, and **empty
stdout**. Write the two broken files after the five runs above, so that no
passing run reads them. `SA-0299`, which no file declares. `SA-0207`, whose
frontmatter is not YAML, the refusal at `saffron/intake.py:186-187`. Then a
fourth scratch record whose sections are out of order. `SA-0201` runs again,
citing none of that record, and then `SA-0205`, citing no item at all. That
kills three implementations letting an error escape as a traceback instead of
`_fail`'s 1. Empty stdout also kills one printing its blocks before it
validates. The unrelated record kills one that parses the cited record alone
rather than calling `records.load.load`. The `SA-0205` run kills one that
loads records only once `first_cited_item` returns an id.
`load_spec` refuses on several grounds, and `records.load.load` on several.
This witness drives one of each, and the others reach the same `SpecError` and
`RecordError`.

Criterion 2 makes three runs over the helper's tree, then a table, and kills
twenty-seven. One `def` loops over the table, which is not a parametrised test.

- **`SA-0201`**, admitted. Match the opening against
  `Re-measured \d{4}-\d{2}-\d{2}, a tenth time:`. Assert `SA-0201`, its
  origin item's id, the words for an empty `depends_on`, and
  `candidate 2 of 2`. That kills a paragraph omitting the date, one naming
  neither the spec nor its item, and one leaving `depends_on` out. The
  position kills one that counts from zero, and one giving every candidate
  the first place. It also kills one that sorts by id, which puts `SA-0201`
  first. Matching today's date instead would flake at midnight.
- **`SA-0203`**, refused. Assert `SA-0203` and its origin item's id, `SA-0202`
  before `SA-0200`, and the scheduler's reason as the full string measured
  below. That kills printing `depends_on[0]` alone, reordering the ids, and a
  paragraph covering the candidate case alone.
- **`SA-0200`**, retired. Assert `SA-0200`, its origin item's id, and that it
  is retired to `done/`, with no `candidate` in it. That kills treating it as
  absent from the directory, or as a refusal it never drew.

The table rewrites the scratch `tests/test_scheduler.py` for each row and runs
`SA-0201` again. Every row keeps the earlier function the helper writes, whose
docstring reads `re-anchored a fourth time`. Each smoke-test docstring holds
two `Re-measured` lines. The first carries the row's phrase, and the second,
lower down, carries `a fourth time`. Nine rows step: `a ninth time`,
`a nineteenth time`, `a twenty-ninth time`, `a fiftieth time`,
`a fifty-second time`, `a seventh time`, `an eleventh time`,
`a fifty-seventh time` and `an eightieth time`. Assert the next phrase the
claim names for each.

Seven rows do not step, and four of them are the no-ordinal case. The first is
a docstring whose two lines both drop the phrase, since its second line would
otherwise supply one. Then come `a hundredth time`, `a ninety-ninth time`, and
a smoke test with no docstring at all. Three are the no-function case. One
file holds no function of the smoke test's name. One file does not parse. One
row deletes the file. Assert the three headings, `<Nth>`, exit 0, and the case line for each. The
line is the same within a case and differs between the two.

The two-line docstring kills a count of `Re-measured` lines, which gives
`third`, and a reader taking the last phrase, which gives `fifth`. The earlier
function kills a reader taking the first phrase anywhere in the file, which
gives `fifth` in every stepping row. It prints a phrase in the no-ordinal and
no-function rows too. The live file is why. Its first phrase is
`re-anchored a fourth time` at `tests/test_scheduler.py:1545`, in the test
starting at `:1542`, before the smoke test at `:1820`. The stepping rows kill a
list of plain words alone, one that misorders the tens against the hyphenated
words, and one printing no `an`. The `an eleventh` and `an eightieth` rows
kill a reader matching `a` alone. The `fifty-seventh` row kills two article
rules, and each prints `an fifty-eighth`. One judges the last hyphen part.
The other tests `"eigh" in word or "elev" in word`. The `eightieth` row also kills the
first of those, which prints `a eighty-first`. The seven rows that do not
step kill raising over each of them, `ninety-ninth` stepping past the list's
end included.

Criterion 3 makes two runs and kills eleven. Patch
`saffron.scheduler.subprocess.run` to raise for both. Monkeypatch
`driver._ledger_and_repo` to raise, and set `HOME` to a directory under
`tmp_path`.

- **The first run** asserts both lines as exact strings, `assert` keyword
  included, and exit 0. Assert that `.saffron/ledger.db` does not exist under
  the patched `HOME`. That kills opening the live ledger through
  `_ledger_and_repo`, and opening it through `Path.home()` directly. It kills
  omitting `gh=`, because `build_queue`'s default `run_gh` shells the real
  `gh`. It kills printing the candidates and forgetting the refusals, or the
  reverse. It kills sorting the candidates, because the fixture's candidate
  order is the reverse of its filename order. It kills printing the first
  refusal alone, or reordering the two. It kills printing bare ids rather than
  two pasteable statements. It kills a cut to anything but seven characters,
  because each refused file's eighth character is `-` where its seventh is a
  digit.
- **The second run** monkeypatches `saffron.scheduler._open_prs` to record its
  two arguments and return `[]`. Assert it recorded `joel/saffron` and a
  runner that is not `saffron.scheduler.run_gh`. That kills
  `repo_slug=None`, which skips `_open_prs` and leaves both lists unchanged,
  so no printed line can see it. Measured at this base over the fixture below,
  that patch records exactly that pair. The first run keeps `_open_prs` real,
  so the raising `subprocess.run` still guards the default runner.

**Each witness is a plain `def`, never parametrised**. `criteria` matches a
bare node id against the names the suite collected, by exact string. A
`pytest.mark.parametrize` test collects under a name no criterion can name
(backlog item 159). Several cases in one witness is one `def` driving several.

**Each witness must fail with your source reverted**. `revert` re-runs every
test your diff adds, whether or not a criterion names it, so write no test
that passes at base. The module execs `driver.py` through `importlib.util` at
`tests/test_spec_loop_driver.py:20-27`. A reverted run then fails on the
missing attribute, which is what `revert` needs to see. Load nothing new at
module scope. A module-scope import of a name this change adds turns that run
into a collection error, which `revert` reads as `skip`.

**Build one scratch tree, and keep it small**. No git is needed anywhere in
this witness set, because the command reads no commit. One helper writes three
things under `tmp_path`, and each witness calls it into its own `tmp_path`.

- A `.saffron/specs/` holding the five specs measured below. Each has the
  shape at `tests/test_spec_loop_driver.py:1059-1062` plus a `## Context`
  line naming an item. `SA-0201`'s `## Context` cites record A first and
  record B second. Its frontmatter `title:` cites a third live id as
  `item <id>`, one the scratch `docs/backlog/` omits. That is what kills a
  reader of the whole file. `SA-0203` cites record B, and
  `SA-0200`, `SA-0202` and `SA-0204` cite record C as `item 32`.
- A `docs/backlog/` holding three short records. Records A and B are random
  ids. Record A carries `specs: [SA-0100, SA-0300]` and record B
  `specs: [SA-0203]`. Record C is the numbered item `032-<slug>.md`, with
  `id: 32` and `specs: []`. Live, 177 of `docs/backlog/`'s records are
  numbered, and retired specs cite them first. `_ID` reads a numbered id as
  `\d{1,3}` (`tests/records/check.py:37`), and `as_id` turns the file's `032`
  into the `32` its `id` must equal (`records/load.py:170-173`). Each holds `## Problem`, `## Done looks like` and `## Record`,
  in that order and drawn from those three headings alone. `_sectioned`
  refuses prose before the first heading, an unknown heading, and a heading
  out of order (`records/load.py:114-136`, `records/kinds.py:160`).
  `_check_sections` refuses an empty `## Done looks like` under any `status`
  outside `done`, `superseded` and `wontfix` (`records/load.py:140-147`,
  `records/kinds.py:25`). A record missing any of that raises `RecordError`.
  This command reports that as its third failure, so every witness but that
  one would be measuring the wrong thing. A record file name must match
  `^(\d{3}|b-[0-9a-f]{6})-[a-z0-9-]+\.md$` (`records/kinds.py:190`), and its
  prefix must equal its `id` (`records/load.py:170-173`). `PRIORITY.md` is
  one of that kind's `hand_written` names (`records/kinds.py:192`), so a
  fixture writing one would be skipped rather than refused. This fixture
  writes none.
- A `tests/test_scheduler.py` holding two functions. The first is a test
  whose docstring reads `re-anchored a fourth time`, as
  `tests/test_scheduler.py:1545` does. The second is the smoke test's `def`,
  with a docstring whose two `Re-measured` lines read `a ninth time` and then
  `a fourth time`.

The helper then monkeypatches `driver.REPO` and `driver.SPECS_DIR`. Do not copy
this repository into the fixture. Criterion 1 writes its extra specs and its
broken record on top of what the helper wrote. Criterion 3 writes none, so the
queue it reads is exactly the five specs below.

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
the fixture that way and pin those strings. `SA-0200` is retired, which is the
third position criterion 2 asserts, and it is also the second id `SA-0203`
declares. A retired parent is credited (`saffron/scheduler.py:535-536`), so
`SA-0203`'s reason names `SA-0202` alone. Measured control at this base, the
same fixture with `SA-0200` moved out of `done/`: that reason gains
` (+1 more unmet)` (`saffron/scheduler.py:719-720`). Pinning the suffix-free
string is what holds the retired credit, and it costs no fixture of its own.

**Every `item <id>` a witness writes must name a record the live
`docs/backlog/` holds**. `first_cited_item` fires only on the `_ITEMS` pattern
(`tests/records/check.py:37-41`). So each fixture `## Context` carries a phrase
like "Backlog item b-b69bb6 is the origin", in this test file's own source.
`CITING` at `tests/records/check.py:23-30` includes `tests`, and
`_citing_files` at `tests/records/check.py:347-349` skips only
`tests/records/`. So `check_item_citations` at
`tests/records/check.py:352-360` reads those phrases as live citations. It
reports "cites backlog item {n}, which does not exist" for an invented id.
`tests/records/test_records_integrity.py:13-21` runs that over the live tree in
the `tests` gate. The failure is new, so the baseline subtracts nothing. Both
`tests/records/**` and `docs/**` are `forbidden`, so the cell cannot file the
record that would answer it. Record C's `32` is live, as
`docs/backlog/032-the-dependency-gate-asked-whether-a-parent-shipped-and-answered-from-a.md`.
For `SA-0206`, cite a real live id that the scratch `docs/backlog/` omits.

**Each block is headed and printed even when it is empty**. A command printing
nothing reads the same whether it had nothing to report or never looked. That
no-op is what the headings make visible. `cmd_check` at
`.claude/skills/run-saffron-spec-loop/driver.py:1712` prints a clean-verdict
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
`test_enumerators_lists_the_calls_whose_directory_it_cannot_resolve` at
`tests/test_spec_loop_driver.py:2454`, the last test `SA-0115` added.

**The shape is about 491 changed lines, and nothing here raises the tier**.
Neither file in `touches` sits under `.saffron/policy.yaml:34-58`'s
`elevate_on`, and neither is under `protected` at `.saffron/policy.yaml:61-66`.
So this task runs at `risk: standard`, where `size` is advisory against the
`feature` ceiling of 600 (`saffron/gates/core/size.py:25`). Derived per part,
it is 169 in `driver.py` and 322 in the test file.

- In `driver.py`: 34 for the origin item and the `specs:` line it owes, over
  what `tests/records/check.py` exports already. 26 for the queue under the
  smoke test's arrangement, with the temporary ledger and the `gh` passed in.
  25 for the ordinal list, the step and the article. 17 for finding the smoke
  test's docstring with `ast`, a missing or unparseable file included. 26 for the paragraph and its three positions.
  36 for `cmd_bookkeeping` with its three failures and three headed blocks,
  and 5 to register the subcommand. That is 169.
- In the tests: 53 for the helper that builds the scratch tree. 100 for
  criterion 1's nine runs, 112 for criterion 2's three runs and sixteen table
  rows, and 57 for criterion 3's two runs. That is 322.

No uplift is applied, and the parents are why. `SA-0114` estimated 485 and
landed 330 in `6aa8da85`. `SA-0115` estimated 520 and landed 659 in
`e4cf6388`, 206 in `driver.py` and 453 in the test file. Together that is 1005
estimated against 989 landed. The risk sits in the test file, where `SA-0115`
ran 168 over its own figure. 491 leaves 109 under the ceiling. If the test file
runs long anyway, keep every case above. `size` is advisory at this tier, and
an attempt spent shrinking a fixture to fit costs more than the overrun.

Against the `size:` lines `driver.py history SA-0116` prints, 491 sits
below `SA-0108`'s 494 and above `SA-0016`'s 486 and `SA-0089`'s 477, all merged. It sits well
above `SA-0114`'s 330 in these same two files. `SA-0115` at 659 and `SA-0107`
at 1049 overshot the ceiling. The comparable narrow cell in these files is
`SA-0112`, at 243. `PRIORITY.md` is cut for size, and a fourth thing an author
wants is item b-7d3810's next entry rather than this cell's work.

**The ceilings, against `driver.py history SA-0116`**. Its last line opens
`ceilings: max_turns=150 vs SA-0089's peak 88t (used), above by 62t`. It
closes `budget_usd=26.0 vs SA-0089's pre-review total $9.13, above by
$16.87`. The most
any one printed row spent after that point is `SA-0107`'s $2.81 review plus
$3.17 rebut, $5.98. That sits well inside the $16.87 left. `SA-0114`, the
nearest row in these files, peaked at 82t. Both ceilings are what `SA-0114`
and `SA-0115` declare
(`.saffron/specs/SA-0115-the-tests-that-enumerate-a-directory-a-spec-adds-to.md:38-40`).
`max_attempts: 3` is this file's standing level, as `SA-0112`, `SA-0114` and
`SA-0115` ran.

Commit after each coherent step. Uncommitted work dies with the cell.
