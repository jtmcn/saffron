---
id: SA-0115
title: the tests that enumerate a directory a spec adds a file to are found by reading, one review at a time, and the answer is computable
type: feature
priority: 2
depends_on: [SA-0114]
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
      `driver.py enumerators` takes a spec path and a base commit, and reads
      the spec from the working tree, so a spec no commit holds yet is read.
      Its directories come from the spec's `touches`. An entry the base commit
      holds no file at is a file the spec adds, and that entry's parent
      directory is one of them. An entry the commit does hold a file at yields
      no directory, and neither does an entry carrying `*` or `?`, the two
      metacharacters `_TOKENS` at `saffron/gates/core/scope.py:17` is built
      from, which is counted as skipped instead. Every run that gets as far as
      taking directories prints one count line, even a run that takes none. It
      counts the directories taken, the entries skipped and the files read
      under `tests/` at that commit, and it is not itself a report. A spec
      whose `touches` yields no directory draws no other output and exits 0. A
      spec path naming no file, a spec whose frontmatter intake refuses, and a
      `--base` git cannot resolve each print a message to stderr and exit 1,
      raising no traceback. Those three are decided before any directory is
      taken, so none of them prints the count line. A spec whose `touches`
      yields no directory and whose `--base` git cannot resolve exits 1
      rather than 0.
    witness: tests/test_spec_loop_driver.py::test_enumerators_takes_its_directories_from_the_touches_a_commit_holds_no_file_at
  - claim: >-
      For each of those directories the command reads every Python file under
      `tests/` at the base commit, and reports the enumerating calls that
      reach it. The call set is `.glob(...)`, `.rglob(...)` and `.iterdir()`
      on a path expression, and `os.walk(...)`, `os.listdir(...)` and
      `os.scandir(...)` where `os` is the name that file imported the `os`
      module under. `ast.walk(...)` and a `walk` the file defines itself are
      in neither. A call whose directory is the directory itself is reported
      as enumerating it, whatever its spelling and whatever its pattern, and
      the command exits 1. A call whose directory is an ancestor of it is
      reported as descending into it only where that call recurses, which is
      `.rglob`, `os.walk`, or `.glob` whose literal pattern carries `**`. An
      ancestor `.glob` whose pattern is no string literal goes to criterion
      3's unresolved list instead of either answer. A run whose reports are
      all descents exits 0. A call on any other directory is not reported,
      whatever its pattern. Each report names the file, the line and the
      function holding the call at that commit, and names `<module>` in the
      function's place where the call sits at that file's module scope rather
      than inside a function.
    witness: tests/test_spec_loop_driver.py::test_enumerators_reports_the_tests_that_enumerate_and_the_ones_that_descend
  - claim: >-
      The directory a call enumerates is resolved from its expression at the
      base commit, through a string literal and `Path(...)` of one, `/` with a
      literal on the right, `__file__`, `.resolve()`, `.parent`,
      `.parents[n]` and `<module>.__file__`. It also resolves through a name
      assigned exactly once at that file's module scope or in the function
      holding the call. It resolves through an attribute of an imported
      module, assigned exactly once at that module's own top level. That
      attribute's value resolves in that module's own scope, through its own
      names and its own `__file__`. An imported module is one imported as
      `import <module>` or `from <package> import <module>`, whose `.py` file
      the commit holds. Anything else resolves to nothing, including a name
      assigned more than once in the scope reached and a `<module>.__file__`
      whose module the commit holds no file for. A call whose directory
      resolves to nothing is listed as unresolved with its file and line,
      rather than reported against a directory or dropped in silence. So is a `.glob` whose pattern is not a string
      literal, where its directory is an ancestor of one criterion 1 took. An
      unresolved call is not an enumerator report, and a run whose only output
      is unresolved calls exits 0.
    witness: tests/test_spec_loop_driver.py::test_enumerators_lists_the_calls_whose_directory_it_cannot_resolve
---

## Context

Backlog item **b-b69bb6** is
`docs/backlog/b-b69bb6-a-specs-citations-and-added-directories-are-checked-by-eye.md`,
tier 2. It was filed on 2026-09-20 from one spec carried end to end outside a
loop run. It holds two computable questions a spec review answers by reading.
`SA-0114` ships the first, the `file:line` a spec cites. This spec is the
second, named in that spec's **Out of scope** at
`.saffron/specs/SA-0114-a-specs-citations-are-resolved-by-eye.md:230-247` and
in the item's own record at
`docs/backlog/b-b69bb6-a-specs-citations-and-added-directories-are-checked-by-eye.md:70-79`.
For each directory a spec adds a file to, find the tests that enumerate it.

Every sentence here about current code was read at `d5de5176` on 2026-09-20.
That commit is the head of `SA-0114`'s pushed branch, `origin/saffron/SA-0114`.
`depends_on` cuts this cell's worktree from that branch, so `d5de5176` is the
base this cell starts from. Every line cited below is a line of that commit.

**The blocker this computes is in the tree**. `TURN_PROMPTS` at
`tests/test_context.py:369-379` is a hand-written dict of nine turn prompt
names. `test_every_turn_prompt_file_is_loaded_by_something` at
`tests/test_context.py:382-384` asserts that its keys equal `{path.stem for
path in context.TURNS_DIR.glob("*.md")}`. `TURNS_DIR` is `PROMPTS_DIR /
"turns"` at `saffron/agents/context.py:22`, and `PROMPTS_DIR` is
`Path(__file__).resolve().parent / "prompts"` at
`saffron/agents/context.py:21`. `SA-0113` adds a tenth file to that directory.
`saffron/agents/prompts/turns/criterion-probe.md` is in its `touches` at
`.saffron/specs/SA-0113-no-session-names-the-edit-a-claim-rests-on.md:11`, so
every attempt that leaves `tests/test_context.py` alone fails that test. It
passes at base, so baseline subtraction absolves nothing. That spec was drafted
with the file in its `forbidden`, where no cell could repair it. Its first
review moved it into `touches`, at
`.saffron/specs/SA-0113-no-session-names-the-edit-a-claim-rests-on.md:14`,
which is where it sits at this base. So what the blocker cost was a review
round.

**The spec loop's driver is where a computed check for a spec review lives**.
`cmd_check` at `.claude/skills/run-saffron-spec-loop/driver.py:1683-1712`
judges the ceilings comparison and returns 1 on a blocker. `_git` at
`.claude/skills/run-saffron-spec-loop/driver.py:85-89` runs git in the repo,
and raises `GitError` on a non-zero status. `_spec_at` at
`.claude/skills/run-saffron-spec-loop/driver.py:1425-1448` reads `git ls-tree
-r` and `git show <commit>:<path>` to recover a spec as it stood at a commit,
through the call at `.claude/skills/run-saffron-spec-loop/driver.py:1444`.
`_fail` at `.claude/skills/run-saffron-spec-loop/driver.py:75-78` prints to
stderr and returns 1, with the comment "`saffron/cli.py` reserves 2 for
infrastructure".

**`SA-0114` is the parent, and this command does not call its code**. Both
specs declare the same two `touches`
(`.saffron/specs/SA-0114-a-specs-citations-are-resolved-by-eye.md:7-9`). The
overlap refusal at `saffron/scheduler.py:679-692` would refuse this one against
that one's open pull request. Both register a subparser in the same block of
`main`. Hence `depends_on: [SA-0114]`. `SKILL.md` at
`.claude/skills/run-saffron-spec-loop/SKILL.md:188-189` says a spec with
`depends_on` has its worktree cut from its parent's branch. So `cite` exists
where this cell runs. It is a separate subcommand all the same. Nothing here
reads `cmd_cite`, edits it, or rests on what it prints.

**A spec review answers this question by reading**. Check 2 at
`.claude/agents/spec-reviewer.md:57-63` asks a reader to list "every file the
change must edit", "tests that assert the old behaviour" among them. It asks
for the line at `base` that makes each one necessary.

**The `prose` gate reads this driver and its tests**. `in_scope` at
`.saffron/gates/prose.py:188-193` sends a Python path under `CODE_DIRS` to the
comment and docstring rules. `CODE_DIRS` at `.saffron/gates/prose.py:48-58`
holds `tests/` and `.claude/`.

**Neither file in `touches` is scanned by `dead`**. `ROOTS` at
`.saffron/gates/dead.py:21-29` names `saffron`, `harness`, `images`, `records`,
`ontology`, `hooks` and `.saffron/gates`.

**One file holds every caller of this driver's code**. A `git grep -l` for
`driver.py` at this base returns forty-three files, the driver itself among them.
`tests/test_spec_loop_driver.py` is the only importer. It execs the driver
through `importlib.util` at `tests/test_spec_loop_driver.py:19-26`. The other
forty-one name the command in prose and call nothing. They are the two agent
definitions, the skill's three documents, `.saffron/deadcode-allow.py`, and three
queued specs with two retired ones. This spec file is one of the three, and
`.saffron/**` is `forbidden`. The rest are nineteen backlog records, ten
other documents under `docs/`, and `tests/test_scheduler.py`, whose mention
sits in the queue smoke test's docstring. The importer and the driver are in
`touches`, and every other reader is `forbidden`.

**What the command reads is bounded**. `git ls-tree -r --name-only d5de5176
tests` lists 85 Python files.

## Problem

A spec that adds a file to a directory some test enumerates fails that test on
every attempt. The only thing between such a spec and a cell is a reader who
thought to look.

- **Baseline subtraction does not absolve it, and a `forbidden` file leaves
  the cell nothing to repair**. The test passes at base, so its failure
  belongs to the task. The file it lives in is `forbidden` where the spec is
  not about it, and `SA-0113` was drafted that way. Its first review moved
  `tests/test_context.py` into `touches`. That review round is what the
  blocker cost, and it is the one reason no cell paid for it.
- **The answer is computable and nothing computes it**. Which directories a
  spec adds a file to is in its `touches`. Which tests enumerate a directory
  is an `ast` walk over `tests/` at the base commit.
- **What the rounds cost, measured on `SA-0113`**: the draft 35.7 minutes,
  the first review 6.2, the revision 17.9, the second review 9.5. Item
  b-b69bb6 is first of two in `docs/backlog/PRIORITY.md:174-179` for that
  reason.

The command is `enumerators`. It takes the spec's path and `--base`, and it
prints the tests that will see the files the spec adds.

1. **Which directories**. Every entry of the spec's `touches` the base commit
   holds no file at is a file the spec adds. That entry's parent directory is
   what the scan looks for. An entry the commit does hold a file at adds
   nothing. `SA-0113`'s `touches` names seven entries, two of them new prompt
   files, so its directories are `saffron/agents/prompts` and
   `saffron/agents/prompts/turns`.

2. **What a `touches` glob does**. An entry such as `saffron/report/**` names
   no single file, so it yields no directory. The count line counts it as
   skipped rather than dropping it in silence. The metacharacters are `*` and
   `?`, the two `_TOKENS` at `saffron/gates/core/scope.py:17` is built from,
   and `_to_regex` at `saffron/gates/core/scope.py:21-28` is what expands
   them. An entry carrying neither is a path. A spec declaring a glob has a blind spot
   here, and the reader is the one who has to see it.

3. **What an enumerating call is**. Six spellings, each of which hands a test
   the contents of a directory: `.glob(...)`, `.rglob(...)` and `.iterdir()` on
   a path, and `os.walk(...)`, `os.listdir(...)` and `os.scandir(...)`.
   Measured at this base over the 85 Python files under `tests/`: **35 calls**.
   The spelling is what decides. A name match on `walk` alone is wrong, because
   matching every `walk` call adds **12 more calls** in four files. Ten of
   those are `ast.walk`, among them `tests/test_cli.py:200`,
   `tests/test_events.py:1200` and `tests/ontology/test_spans.py:21`. Two call
   a locally defined recursive helper by its bare name, at
   `tests/test_package.py:1161` and `tests/test_package.py:1163`. None of the
   twelve enumerates a directory. So `os.walk` counts only where `os` is the
   name that file imported the `os` module under.

4. **Which of them reach the directory**. A call on the directory itself is
   what fails a spec, and `tests/test_context.py:384` is that case exactly. A
   call on a directory *above* it reaches the new file only where it recurses.
   Recursing is `.rglob`, `os.walk`, and `.glob` whose literal pattern carries
   `**`. Those are worth naming and are not the blocker shape. At this base
   `tests/test_citations.py:148` walks the repository root through `os.walk`,
   and it would be listed for every spec that adds any file at all. So the two
   are reported apart, and only the first sets the exit status. A
   non-recursive call on a directory above lists that directory's own entries
   and never the new file, so it draws no report. An ancestor `.glob` whose
   pattern is a name rather than a literal says nothing about which of the two
   it is. Guessing either way is wrong in one direction, so that call goes to
   item 6's third kind. At this base it is `any(ROOT.glob(p))` at
   `tests/test_citations.py:345`. Its `p` is a comprehension variable, and its
   `ROOT` is the repository root (`tests/test_citations.py:40`). That root is
   an ancestor of every directory but itself. So the case fires on every run
   that takes a directory, save for a spec adding a file at the root. Item 6
   makes the call an enumerator there.

5. **How a directory is resolved**. The receiver is an expression, and
   resolving it is where this command earns its keep. The motivating call is
   spelled `context.TURNS_DIR`, two hops from a path. The set is a literal, a
   `Path(...)` of one, `/` with a literal on the right, `__file__`,
   `.resolve()`, `.parent`, `.parents[n]` and `<module>.__file__`. It also
   holds a name assigned exactly once in the file's module scope, or in the
   function holding the call. An attribute of an imported module assigned
   exactly once at that module's top level is in the set too. Its value
   resolves in that module's scope, as `TURNS_DIR` reads `PROMPTS_DIR` at
   `saffron/agents/context.py:21-22`. An imported module is one imported as
   `import <module>` or `from <package> import <module>`. It resolves to its
   `.py` file at the commit, and to nothing where the commit holds none. That
   is the whole of it. There is no control-flow analysis and no execution. A
   name assigned twice in the scope reached resolves to nothing rather than to
   its first binding. Three shapes are left undriven, as
   `docs/agents/issue-tracker.md:110-111` asks a spec to say. They are a dotted
   `import a.b` read as `a.b.X`, a package's `__init__.py`, and a name bound by
   `for`, `with` or `import` rather than by assignment.

6. **What is reported**. Three kinds of line: a call enumerating one of the
   directories, a call descending into one, and a call the command could not
   place. The third kind is a receiver that resolved to nothing, or an
   ancestor `.glob` whose pattern is no string literal. A call is judged once
   per directory taken, and so one call can appear under two. Against each
   directory, a kept call is one of the three kinds or draws nothing. The
   unresolved list is one group after the directories, one line per call
   however many directories it reached. For `SA-0113`, a recursive call
   on `saffron/agents/prompts` enumerates that directory and descends into
   `saffron/agents/prompts/turns`. The directory decides before the pattern
   does. A call on one of the directories itself is the first kind whatever
   its pattern, because recursion decides nothing there. So `ROOT.glob(p)`
   above is an enumerator report for a spec adding a file at the repository
   root. It is the third kind for every other spec. Measured at this base with
   a throwaway script over the resolution set above, the receivers of 19 of
   the 35 resolve and **16 do not**. Most of the sixteen are rooted at a `tmp_path` fixture or at
   a function's own parameter, and enumerate a scratch tree rather than the
   repository. Those numbers measure the author's prototype and are not a
   criterion. Nothing asserts them, and an implementation resolving more or
   fewer is not wrong on that account. The unresolved list is printed because
   a command blind to sixteen calls reads exactly like one with nothing to
   say. The reader deciding whether check 2 is done needs to know which it is.

7. **What the exit status means**. 1 where a call enumerating one of the
   directories was reported, and 0 otherwise, descents and unresolved calls
   included. `cmd_check` at
   `.claude/skills/run-saffron-spec-loop/driver.py:1683-1712` returns 1 the
   same way, and `_fail` at
   `.claude/skills/run-saffron-spec-loop/driver.py:75-78` explains why 2 stays
   reserved. A spec path naming no file, a spec frontmatter intake refuses, and
   a `--base` git cannot resolve are usage failures. Each takes `_fail`'s 1
   without reading a commit's `tests/` tree.

## Out of scope

**The citation half of item b-b69bb6**. `SA-0114` owns it, it is queued, and
this spec's cell is cut from its branch. Nothing here calls `cmd_cite`, and
nothing here edits it. The two subcommands share a file, a spec path argument
and a `--base`, and nothing else. The writer agent runs two commands. Folding them
into one is the operator's call later, and it is prose, which is the half
below.

**The prose half of item b-b69bb6**. The item asks that the `spec-writer` agent
run this before its own self-review. It asks that `spec-reviewer`'s check 2 at
`.claude/agents/spec-reviewer.md:57-63` read its output. Both are prompts, and
no test watches one. `.claude/agents/**` and the skill's `SKILL.md` are
`forbidden` here. This is the order `SA-0092`, `SA-0112` and `SA-0114` took,
which item b-281f0a records as settled: the cell ships the command, and the
operator wires the prose to it afterwards. So this command is called by nothing
the day it lands, and that is the expected state rather than an omission. Two
lines are the ones to leave alone rather than the ones to fix.
`.claude/agents/spec-reviewer.md:19-20` names `driver.py history <SPEC-ID>` as
what a review runs. `.claude/agents/spec-reviewer.md:30` limits a reviewer's
Bash to "those git commands and `driver.py history` only".

**Enumerating calls outside `tests/`**. `saffron/` reads directories too. The
prompt digest at `saffron/agents/context.py:212` rglobs `PROMPTS_DIR`, and a
tenth turn prompt changes what it hashes. A spec that adds a file there changes
a product's behaviour rather than failing a gate. The blocking gate this
command exists for is `tests`. Read `tests/**/*.py` at the commit and nothing
else.

**`glob.glob` and `glob.iglob`**. Measured at this base: no call site under
`tests/` spells either. The first argument of both is a pattern rather than a
directory. Supporting them is a second parser for a case the tree does not
have. Leave them out.

**Judging what it reports**. The command names candidates. It decides no
severity, edits no spec, moves no `touches` entry and writes no file. A test it
reports is sometimes one the spec is free to ignore.

**The test that would have caught `SA-0113`**. Add none to
`tests/test_context.py`, and edit nothing in that file. It is `forbidden`, and
this command reads it as data at a commit. Changing the shape it is written in
is a different change against a different item.

**`§` citations**. `tests/test_citations.py` covers every `§N` and appendix
citation over the whole tree on every `make check`. It is `forbidden`. Its
`os.walk` at `tests/test_citations.py:148` is input to this command rather than
something to change.

**Every other subcommand**. `snapshot`, `next`, `record`, `drop`, `hold`,
`probe`, `status`, `stack`, `rebase`, `size`, `history`, `check`, `pattern` and
`cite` keep the output and the exit status they have. Read no ledger here.
`enumerators` reads the tree and nothing else, so `_ledger_and_repo` at
`.claude/skills/run-saffron-spec-loop/driver.py:136-144` plays no part.

## Notes for the agent

**This change is new code, so no criterion declares a mutant** (§5.4.1). The
subcommand, its helpers and every sentence it prints do not exist at base, and
nothing there determines their spelling. Expect the `witness` gate to report
`skip`, with a summary saying the spec declares none. `SA-0112` ran under the
same limit in this same file.

**No term here is new, so no vocabulary follow-up is owed**. `CONTEXT.md`'s
vocabulary names factory concepts. *Enumerate* here describes a Python call
shape, in the word backlog item b-b69bb6 uses for it. The command reports
candidates for a reader and files no finding, so `Finding` and `Severity` keep
the meanings `CONTEXT.md` gives them. `ontology/` is `forbidden` here.

**`enumerators` is the subcommand name, and `--base` defaults to
`origin/main`.** `uv run .claude/skills/run-saffron-spec-loop/driver.py
enumerators .saffron/specs/SA-0113-no-session-names-the-edit-a-claim-rests-on.md`.
Register it in `main` after the `cite` parser at
`.claude/skills/run-saffron-spec-loop/driver.py:2010-2015`, the last one there.
`SA-0114` added that parser below `pattern`, which follows the `check` parser at
`.claude/skills/run-saffron-spec-loop/driver.py:2001-2005`. Add yours after
`cite`, and edit neither of those two parsers.
The default matches what a spec review is told at
`.claude/agents/spec-reviewer.md:15-16`. There `base:` is the commit a cell
would be cut from, and a prompt naming none means `origin/main`.

**Read `REPO` inside the function, never as a default argument value**. A
default binds at definition time. `tests/test_spec_loop_driver.py:371` and
`tests/test_spec_loop_driver.py:613` monkeypatch `driver.REPO` to a scratch
root, and the witnesses here do the same. Helpers that read a tree take the
root as an argument, and `cmd_enumerators` passes the module's `REPO`. The
trap is `_git` itself. Its own `cwd` default binds `REPO` at definition time,
at `.claude/skills/run-saffron-spec-loop/driver.py:85`. So pass `cwd=REPO` on
every call, as `cmd_cite` does at
`.claude/skills/run-saffron-spec-loop/driver.py:1876`.

**The spec is read through intake, the tree through git**. `touches` is
frontmatter, so use `load_spec` from `saffron.intake`, imported inside the
function as `cmd_size` does at
`.claude/skills/run-saffron-spec-loop/driver.py:1346`. A `SpecError` becomes
`_fail`'s message and exit 1, never a traceback. Every file the scan reads
comes from `git ls-tree -r --name-only <base> tests` and `git show
<base>:<path>` through `_git`. The working tree's copy of a test file is never
what gets parsed. Eighty-five `git show` calls is the measured size of that loop
at this base, and one call per file is fine.

**A file the commit holds that `ast` cannot parse is skipped, not fatal**. A
`SyntaxError` on one test file must not end the run. The count line says how
many files were read.

**Name the wrong implementation each witness must kill**. Criterion 1 kills
fifteen. One reads the spec at the base commit rather than the working tree,
which the witness catches by never committing the spec file. One asks the
working tree rather than the commit whether an entry holds a file. Without a
change after the commit, the two read the same tree. So after the fixture
commit, change only the working tree, as
`tests/test_spec_loop_driver.py:1850-1851` does for `cite`. Create a file at
the added `touches` entry, and assert its directory is still taken. Write an
uncommitted Python file under `tests/` as well, and assert the count of files
read leaves it out. One takes every `touches` entry as a file the spec adds.
Give the fixture an entry the commit does hold a file at, in a directory the
fixture's tests enumerate. Keep that directory apart from the added entry's,
and assert no report for it. One drops a glob entry in silence, and one knows
`*` alone and reads a `?` entry as a path. Give the fixture two glob entries,
one carrying `*` and one carrying `?`, in a directory no other entry names.
Assert a skipped count of 2. Two derive a count rather than counting it. One
takes the directories to be the entries not skipped. The other counts every
name `ls-tree` lists as a file read. One takes a directory once per added
entry rather than once. Add a second new entry in the added directory. Put
these five entries in one spec and run it once, after the working tree
changes. Assert all three numbers there. That run takes one directory, skips
two entries, and reads the Python files
the commit holds under `tests/`. Commit one file under `tests/` that is not
Python, so the third number leaves it out. The fixture holds no file `ast`
cannot parse, so that number is not in question. One prints no count line at
all, and one prints more than that line. In the case with no directories,
assert exit 0 and that line as all it prints. One exits 1 where nothing was
reported. One lets a spec intake refuses raise: write a second spec file with
broken frontmatter, and assert exit 1, a message on stderr and no count line
on stdout. One lets a spec path naming no file raise before intake reads it.
`load_spec` wraps an `OSError` in `SpecError` at `saffron/intake.py:269-273`.
A `resolve(strict=True)` or a `relative_to` made before that call raises on
its own all the same. Pass a path no file sits at, and assert the same three
things. One lets `_git` raise on a base no commit answers to. It raises
`GitError` on a non-zero status
(`.claude/skills/run-saffron-spec-loop/driver.py:85-89`). One resolves
`--base` only after taking directories, and returns 0 on a spec that yields
none. Pass `--base no-such-ref` over exactly that spec. Assert the call
returns 1 with a message on stderr and no count line on stdout. It must
neither raise out of the command nor report a clean run.

Criterion 2 kills twenty-one. One knows only `.glob`. The fixture's tests must
reach the added directory through all six spellings the claim names, each in a
place the witness asserts on. Six calls in three short files covers that, and
the cases below add eleven more. Spell one of the six on a `Path("tests/...")`
literal rather than on a name. One reads only the top level of `tests/`. The
real cases sit lower, at `tests/ontology/ontology_paths.py:10` and
`tests/records/check.py:335`. So put one of the three files in `tests/sub/`,
holding one of the six calls. One reads `tests/` from the working tree. After
the fixture commit, write an uncommitted test file that enumerates the added
directory, and assert it draws no report. Create a file at the added `touches`
entry too, and assert the committed calls are still reported. One lists the
files with `git ls-tree` and reads their content from disk. The line at
`tests/test_spec_loop_driver.py:1851` overwrites a committed file for that
reason. Rewrite one committed fixture test file in the working tree, shifting
its call down by a line. Assert its report still names the committed line.
One matches any `walk` at all. Put an `ast.walk(tree)` call and a locally
defined `walk` in the fixture's tests, and assert that neither is reported. One matches the
three `os` spellings on the bare name `os`, with no import map behind it. The
module under any other name then goes missing. Spell one of those three calls
through an aliased import: a fixture file with `import os as o` calling
`o.scandir(...)` on the added directory, asserted as an enumerator report like
the other five. That is also what forces the import map criterion 3 needs. One
reports every ancestor call: give the fixture a non-recursive `.glob("*.md")`
on the parent directory, and assert it draws nothing. One tests recursion by
the `.glob` pattern alone and counts every other spelling as recursive. One
counts `os.listdir` or `os.scandir` as recursive. Put an `.iterdir()`, an
`os.listdir(...)` and an `os.scandir(...)` on that same parent, each asserted
silent beside the `.glob`. One treats `.rglob` as the only recursive form.
Beside that `.glob`, put all three recursive forms on that same parent:
`.rglob(...)`, `os.walk(...)`, and a `.glob` whose literal pattern carries
`**`. The witness asserts a descent for each of the three. One takes an
ancestor to be the parent alone, testing `receiver == d.parent` where
`receiver in d.parents` is meant. It misses `tests/test_citations.py:148`,
which walks the `ROOT` bound at `tests/test_citations.py:40`. Put an `os.walk`
on the fixture root in that shape, two levels or more above the added
directory, and assert a descent. One decides ancestry by string prefix, and so
reads `a/b` as an ancestor of `a/bc/x`. Give the added directory a sibling
whose name is a prefix of its own, such as `fix` beside `fixture`. Put an
`.rglob(...)` there, and assert it draws nothing. One reads ancestry the wrong
way round. Put an `.rglob(...)` on a directory below the added one, and assert
it draws nothing. One counts a descent as a defect, killed by a case whose
only report is a descent and whose exit status is 0. One prints a file and
line without the function holding the call. One assumes every call sits inside
a function. `tests/ontology/ontology_paths.py:10-12` and `:14` are four
module-scope `.glob` calls at this base. Their `ONTOLOGY` and `FIXTURES`
resolve at `tests/ontology/ontology_paths.py:5-6`. A spec adding a `.ttl`
under `ontology/shapes` is one of this command's motivating cases in
`CLAUDE.md`. So for that spec the command reports the one at `:10`, and no
function holds that call. Put one module-scope call on the added directory in
the fixture, and assert its report names `<module>` where the others name a
function. One reports a call on a sibling of the added directory, as `:11`
sits beside `:10`. Put a module-scope call on a sibling directory beside the
first, and assert it draws nothing. One lists a `.glob` whose pattern is no
literal as unresolved wherever its receiver resolves. Spell that sibling call
`.glob(name)`, its name bound to a string. Assert it neither reported nor on
the unresolved list. One judges each call once, against the first directory
it reaches. Write a second spec file over the same commit,
whose `touches` adds a file to the parent directory as well. Assert that the
parent's `.rglob(...)` is then reported twice. It enumerates the parent and
descends into the added directory below it. One sends every `.glob` whose
pattern is no literal to the unresolved list before it compares directories.
One reports a call on a directory itself only where its pattern matches the
added file. Put a `.glob(name)` on the parent, its pattern a name bound to a
string. In the first run it is on the unresolved list. In the second run,
assert an enumerator report for it and for every other call on the parent.
That run still lists it once as unresolved, for the added directory below,
as item 6 says.
Name the file the second spec adds so that `*.md` does not match it. Assert
exit 1 for both runs.

Criterion 3 kills twelve. One resolves only literals. The fixture must reach
its directory through a module-scope name, and through a name assigned in the
function holding the call. Bind the module-scope name to `Path` of a string
literal. Spell one `os.listdir(...)` on a bare string literal, with no
`Path(...)` around it, and assert its report too. A third path to it is an
attribute of another module in the fixture tree. Give one call the shape
`tests/test_cli.py:196-198` has, a directory read through
`Path(<module>.__file__).resolve().parent`. Reach one through `.parents[n]`,
as `tests/test_spec_loop_driver.py:18` does, so that shape is driven too.
One resolves the attribute's value without that module's own names. It
passes on one constant with two joins and misses `tests/test_context.py:384`.
So spell the attribute as `saffron/agents/context.py:21-22` spells
`TURNS_DIR`, two constants, the second built on the first (`B = A / "x"`).
The first is built from `Path(__file__).resolve().parent` and a `/` join. One
reads that `__file__` in the test file's scope. Put the module outside
`tests/`, in a directory of its own, so that reading lands elsewhere. One
knows a single import form, or reads only the first name of a `from` import.
Import the module holding that constant as `from <package> import <other>,
<module>`, the module second, as `tests/test_context.py:8` takes `context`.
Import the module whose `__file__` a call reads with a plain `import
<module>`, so two import forms are driven. One reads the module from disk
rather than the commit. After the fixture commit, rebind the constant in the
module's working tree copy to another directory. Assert the committed
resolution stands. One drops the calls it cannot resolve, killed by asserting
the unresolved line for a receiver that is a function parameter. One treats
unresolved as a defect, killed by a case whose only output is unresolved calls
and whose exit status is 0. The shared fixture cannot hold that case. Its root
`os.walk` descends into every directory but the root. So this witness builds a
second small fixture with no root walk for that run. One resolves a name
assigned twice by taking the first binding. Assign one name twice at module
scope, and another twice in the function holding its call, each to two different directories. Assert both
unresolved rather than reported against either. One resolves a module
attribute assigned twice the same way. Assign a second constant twice at the
fixture module's top level, reach one call through it, and assert it
unresolved. One drops an ancestor `.glob` whose pattern it cannot read. An
implementation that resolves the receiver, finds it an ancestor, and asks
whether a literal pattern carries `**` passes every case above. It drops
`tests/test_citations.py:345` in silence on every run that takes a directory
below the root. Put a `.glob(pattern)` on the parent directory, its pattern a
name bound to a string. Assert it on the unresolved list, neither absent nor
reported as a descent. One resolves `<module>.__file__` for a module the
commit holds no file for. The command parses rather than imports, so a fixture
test file can import a module its commit does not hold. Reach one call through
that module's `__file__`, and assert it unresolved.

**Each witness is a plain `def`, never parametrised**. `criteria` matches a
bare node id against the names the suite collected, by exact string. A
`pytest.mark.parametrize` test collects under a name no criterion can name
(backlog item 159). Several cases in one witness is one `def` driving several.

**Each witness must fail with your source reverted**. `revert` re-runs every
test your diff adds, whether or not a criterion names it, so write no test that
passes at base. The module execs `driver.py` through `importlib.util` at
`tests/test_spec_loop_driver.py:19-26`, and a reverted run then fails on the
missing attribute, which is what `revert` needs to see. Load nothing new at
module scope. A module-scope import of a name this change adds turns that run
into a collection error, which `revert` reads as `skip`.

**Build the fixtures as real commits, and keep the fixture tree small**. The
command reads a tree at a commit, so a witness that stubs `_git` pins your own
parsing rather than git's answer. `tests/test_spec_loop_driver.py:1-2` states
that the file's shape is real git in a temporary repo. `_git` and `_commit` at
`tests/test_spec_loop_driver.py:116-127`, and `empty_repo` at
`tests/test_spec_loop_driver.py:129-137` which blinds the repo to the host's
git config, are what to build on. Write three or four short files under the
fixture repo's own `tests/`, plus the one module whose constant they import,
and commit them. That module sits outside `tests/`. Do not copy this
repository into the fixture. The spec file each witness reads is written in the fixture's working tree and committed
nowhere.

**The count line is one line**. Name the directories taken, the `touches`
entries skipped and the files read. Print it on every run that gets as far as
taking directories, including one with no directory to scan and no file to read.
A usage failure ends the run before that step and prints none. A command that
prints nothing reads the same whether it read eighty-five files or none, and
that no-op is what this line makes visible. `cmd_check` at
`.claude/skills/run-saffron-spec-loop/driver.py:1711` prints a clean-verdict
sentence for the same reason. Group the reports by directory in `touches`
order, and sort each group by path and line. Two runs over one commit then
print the same thing.

**The `prose` gate counts comment runs and docstrings per file**. It blocks
(`.saffron/policy.yaml:25`) and subtracts the base's failures, so a file
gaining a hit of one rule fails the attempt. Keep every comment to one or two
lines and every docstring under ten, `cmd_enumerators`'s included.
`hooks/prose_limit.py --file <path>` answers the same question for one file in
the working tree, and it is the cheap way to check before a gate does.

**Rename no existing test**. `census` compares collected names between base and
head, and reads a rename as a removal. The three new tests belong at the end of
`tests/test_spec_loop_driver.py`. At this base the last test there is
`SA-0114`'s `test_cite_reports_a_citation_whose_quoted_text_sits_on_other_lines`
at `tests/test_spec_loop_driver.py:1927`, so yours follow it.

**The shape is about 573 changed lines, and nothing here raises the tier**.
Neither file in `touches` sits under `.saffron/policy.yaml:34-58`'s
`elevate_on`. So this task runs at `risk: standard`, where `size` is advisory
against the `feature` ceiling of 600 (`saffron/gates/core/size.py:25`). The
estimate is 235 in `driver.py` and 338 in the test file, derived per part. In
`driver.py`: 25 lines to take the directories out of `touches` and count the
skips. 40 to find the calls and decide which of them recurse, the ancestor
`.glob` whose pattern is no literal among them. Then 25 for the file's import
map and the module lookup, and 90 for the resolver item 5 bounds. Last,
47 for `cmd_enumerators` and what it prints. That covers the `GitError` catch
for an unresolvable `--base`, the order the usage failures take, and the
`<module>` a module-scope call's report names. Then 8 to register the
subcommand. In the tests: 44 for a shared helper that builds the fixture repo
and writes a spec file, then 83, 123 and 88 for the three witnesses. The
derivation is measured rather than guessed. The author's prototype of the
resolver, the call finder and the import map ran over this base's `tests/` in
120 lines. It carried no comments, no `_fail` paths and no report. Repo style
plus the bounds above is what takes that to 235. `SA-0112` is the comparable
cell in these same two files, at 99 lines in `driver.py` and 144 in the test
file. That cell built one subcommand with five verdicts and four witnesses.
This one parses Python at a commit, where that one read rows already in hand.
573 leaves 27 lines under the ceiling that `SA-0106` (633) and `SA-0107`
(1049) overshot. The twenty over the first draft are the witness prescriptions
this spec's first review added, three ancestor calls asserted as descents and
a `--base` case. The twenty-five over that are the second review's. They are a
module-scope call and the `<module>` its report names, and an ancestor
`.iterdir()`. The other two are an ancestor `.glob` whose pattern is a name,
and a `<module>.__file__` the commit holds no file for. The forty-three over
that are the latest review's, each a fixture line and an assertion in a
witness already here. They change the working tree after a commit and add a
`?` glob entry. They add a nested test file and a grandparent walk, and assert
the three counts. The ten over that are the review after it. They add a second
entry in the added directory, and a sibling `.glob(name)`. They shift a
committed test file and rebind a committed constant in the working tree. They
build criterion 3's own small fixture for its unresolved-only run. Do not go
looking for more to do. The resolution set in item 5 is closed. A shape it
does not name belongs in the unresolved list rather than in a seventh case.

**The ceilings, against `driver.py history SA-0115`**. `max_turns: 150` stands
against a comparison row that is a floor. The line marks `SA-0106`'s peak of
101t "a floor", because that cell ended `IMPLEMENTING error_max_turns` at its
own ceiling. So the 49t of headroom printed there is narrower than it reads.
The highest peak among the printed rows that ran to its own end is `SA-0089`'s
88t, and 150 clears that by 62t. `budget_usd: 26` stands against `SA-0106`'s
pre-REVIEW total of $14.73, above by $11.27. The most any one printed row spent
after that point is `SA-0107`'s $2.81 review plus $3.17 rebut, $5.98, well
inside that remainder. `max_attempts: 3` is this file's standing level.
`SA-0112` ran at it, and `SA-0114` reached `READY_FOR_REVIEW` at $9.50 under
the same three ceilings as this spec
(`.saffron/specs/SA-0114-a-specs-citations-are-resolved-by-eye.md:36-38`).

Commit after each coherent step. Uncommitted work dies with the cell.