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
      `tests/` at the base commit, and reports the enumerating calls whose
      directory resolves and reaches it. The call set is `.glob(...)`,
      `.rglob(...)` and `.iterdir()` on a receiver, and `os.walk(...)`,
      `os.listdir(...)` and `os.scandir(...)` where `os` is the name that file
      imported the `os` module under. For those three the directory is the
      first positional argument, and for the other three it is the receiver.
      `ast.walk(...)` and a `walk` the file defines itself are in neither. A
      directory resolves only where it is a string literal, `Path` of one
      string literal, or a `/` join whose two parts are each one of those three.
      It is read relative to the repository root. A call whose directory is the
      directory itself is reported as enumerating it, whatever its spelling and
      whatever its pattern, and the command exits 1. A call whose directory is
      an ancestor of it is reported as descending into it only where that call
      recurses, which is `.rglob`, `os.walk`, or `.glob` whose literal pattern
      carries `**`. A run whose reports are all descents exits 0. A call on any
      other directory is not reported, whatever its pattern. Each report names
      the file, the line and the function holding the call at that commit, and
      names `<module>` in the function's place where the call sits at that
      file's module scope rather than inside a function.
    witness: tests/test_spec_loop_driver.py::test_enumerators_reports_the_tests_that_enumerate_and_the_ones_that_descend
  - claim: >-
      A call with one of those six spellings whose directory does not resolve
      under criterion 2's three forms is listed as unresolved, with its file
      and line. That covers a name of any kind, a function parameter among
      them, an attribute, a subscript, `__file__` and anything built on it, a
      `/` join with any other part, a call other than `Path` of one string
      literal, and an `os` call with no positional argument. A `.glob` whose
      directory resolves to an ancestor of one criterion 1 took, and whose
      pattern is not a string literal, is listed as well. An unresolved call is never
      reported as an enumerator or a descent, and it is never dropped. The
      list is one group after the reports, one line per call, and it prints on
      every run that takes a directory. A run whose only output beyond the
      count line is unresolved calls exits 0.
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

**The blocker is in the tree**. `TURN_PROMPTS` at
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
round. Under this spec the call at `tests/test_context.py:384` is an
unresolved line rather than an enumerator report, because its receiver is an
attribute. **Out of scope** names the follow-up that resolves it.

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
   what fails a spec, and `tests/test_context.py:384` is that shape exactly. A
   call on a directory *above* it reaches the new file only where it recurses.
   Recursing is `.rglob`, `os.walk`, and `.glob` whose literal pattern carries
   `**`. Those are worth naming and are not the blocker shape. At this base
   `tests/test_citations.py:148` walks the repository root through `os.walk`.
   Once its receiver resolves, it reaches every directory a spec adds a file
   to. So the two are reported apart, and only the first sets the exit status.
   A non-recursive call on a directory above lists that directory's own
   entries and never the new file, so it draws no report. An ancestor `.glob`
   whose pattern is not a string literal says nothing about which of the two it
   is. Guessing either way is wrong in one direction, so that call goes to the
   unresolved list. A call on one of the directories itself is an enumerator
   whatever its pattern, because recursion decides nothing there.

5. **How a directory is resolved**. Three forms, and nothing else: a string
   literal, `Path` of one string literal, and a `/` join whose two parts are
   each one of the three. `Path("a") / "b"` is a join, and so is `"a" /
   Path("b")`. A resolved directory is read relative to the repository root,
   the form every `touches` entry takes. The set needs no name lookup, no
   import and no scope. Every other expression is unresolved. That covers a
   name, an attribute, a subscript, `__file__` and whatever is built on it,
   and a call other than `Path` of one literal. A `/` join with any other part
   is unresolved too, and so is an `os` call with no positional argument.
   Resolving through names and imports is the follow-up **Out of scope**
   names. One shape is left undriven, as
   `docs/agents/issue-tracker.md:110-111` asks a spec to say. An f-string is
   not a string literal, as a directory or as a `.glob` pattern, and no
   witness spells one. None occurs under `tests/` at this base.

6. **What is reported**. Against each directory taken, a resolved call is an
   enumerator, a descent, or draws nothing. A call is judged once per
   directory taken, and so one resolved call can appear under two. For
   `SA-0113`, a recursive call on `saffron/agents/prompts` enumerates that
   directory and descends into `saffron/agents/prompts/turns`. An unresolved
   call is listed, never dropped and never judged. The unresolved list is one
   group after the directories, one line per call. An ancestor `.glob` whose
   pattern is not a literal joins it once, however many directories it sits
   above. Measured at this base with a throwaway script over the three forms,
   **none of the 35 calls resolves**. Every receiver is a name, an attribute, or
   a `/` join built on one, as at `tests/test_citations.py:345`,
   `tests/test_context.py:384` and `tests/ontology/ontology_paths.py:10`. So
   until the follow-up lands, a run over this repository prints the count
   line and 35 unresolved lines, and exits 0. That is a bounded worklist in
   place of a read over 85 files. It is the whole of what this spec promises
   for the tree as it stands. The number measures a prototype and is
   not a criterion. Nothing asserts it. The list is printed because a command
   blind to 35 calls reads exactly like one with nothing to say.

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

**Resolving a receiver through names and imports**. The operator split this
out into a follow-up spec, designed outside the spec loop. It resolves a
receiver through a name assigned once, and through an imported module's
attribute in that module's own scope. It resolves `__file__` and its
`.resolve()`, `.parent` and `.parents[n]` chain. It decides scope precedence
between a module binding and a function binding. Four review rounds of this
spec found where such a resolver goes wrong, and the follow-up starts there.
`TURNS_DIR` is two hops from a path, `PROMPTS_DIR / "turns"` built on
`Path(__file__).resolve().parent / "prompts"` at
`saffron/agents/context.py:21-22`. `tests/test_context.py:8` imports
`context` as the second name of a multi-name `from` import. Each import form,
`import <module>` and `from <package> import <module>`, has to reach each use,
a module attribute and a `<module>.__file__`. A function binding shadows a
module binding of the same name, and the resolver has to honour that. Until that spec lands, `SA-0113`'s
`TURNS_DIR` case and every `ROOT`-rooted call, such as
`tests/test_citations.py:148` and `:345`, show as unresolved lines. They are
not enumerator or descent reports. Being listed is the whole of what this spec
promises for them.

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
Give the fixture an entry the commit does hold a file at. A fixture test
enumerates its directory on a string literal, so the call resolves. Keep that directory apart from the added entry's,
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

Criterion 2 kills twenty-three. Every call in its fixture sits on a
directory that resolves, a string literal, `Path` of one, or a join of those.
One knows only `.glob`. The fixture's tests must reach the added directory
through all six spellings the claim names, each in a place the witness asserts
on. Six calls in three short files covers that, and the cases below add
sixteen more. One resolves `Path` of a literal alone and misses a bare
string. Spell `os.listdir(...)` on a bare string literal naming the added
directory, and assert its report. One resolves a join only in one
arrangement. Spell `.iterdir()` on `Path("<a>") / "<b>" / "<c>"` and
`os.walk(...)` on `"<a>/<b>" / Path("<c>")`, each naming the added directory.
Between them the left part takes all three forms. The right part is a bare
string in one and `Path` of a literal in the other. Assert both reported.
Spell the aliased `scandir` below on `Path("<added directory>")`. The method
spellings and the `os` spellings then each meet `Path` of a literal and a
join. The `os` spellings meet a bare string too. One reads only the top level of `tests/`. The real cases sit lower,
at `tests/ontology/ontology_paths.py:10` and `tests/records/check.py:335`. So
put one of the three files in `tests/sub/`, holding one of the six calls. One
reads `tests/` from the working tree. After the fixture commit, write an
uncommitted test file that enumerates the added directory, and assert it
draws no report. Create a file at the added `touches` entry too, and assert
the committed calls are still reported. One lists the files with `git
ls-tree` and reads their content from disk. The line at
`tests/test_spec_loop_driver.py:1851` overwrites a committed file for that
reason. Rewrite one committed fixture test file in the working tree, shifting
its call down by a line. Assert its report still names the committed line.
One matches any `walk` at all. Put an `ast.walk(tree)` call and a locally
defined `walk` in the fixture's tests, and assert that neither is reported.
One matches the three `os` spellings on the bare name `os`, with no import
map behind it. The module under any other name then goes missing. Spell one
of those three calls through an aliased import. A fixture file with `import
os as o` calls `o.scandir(Path("<added directory>"))`, asserted as an enumerator
report like the other five. One reports every ancestor call. Give the fixture
a non-recursive `Path("<parent>").glob("*.md")` on the parent directory, and
assert it draws nothing. One tests recursion by the `.glob` pattern alone and
counts every other spelling as recursive. One counts `os.listdir` or
`os.scandir` as recursive. Put an `.iterdir()`, an `os.listdir(...)` and an
`os.scandir(...)` on that same parent, each asserted silent beside the
`.glob`. One treats `.rglob` as the only recursive form. Beside that `.glob`,
put all three recursive forms on that same parent: `.rglob(...)`,
`os.walk(...)`, and a `.glob` whose literal pattern carries `**`. The witness
asserts a descent for each of the three. One takes an ancestor to be the
parent alone, testing `receiver == d.parent` where `receiver in d.parents` is
meant. It misses the shape of `tests/test_citations.py:148`, a walk on a root
far above. Put an `os.walk` on a bare string literal naming a directory two
levels or more above the added one, such as `os.walk("fixture")`. Assert a
descent. One decides ancestry by string prefix, and so reads `a/b` as an
ancestor of `a/bc/x`. Give the added directory a sibling whose name is a
prefix of its own, such as `fix` beside `fixture`. Put an `.rglob(...)` on
`Path` of that sibling, and assert it draws nothing. One reads ancestry the
wrong way round. Put an `.rglob(...)` on `Path` of a directory below the
added one, and assert it draws nothing. One counts a descent as a defect,
killed by a case whose only report is a descent and whose exit status is 0.
One prints a file and line without the function holding the call. One assumes
every call sits inside a function. `tests/ontology/ontology_paths.py:10-12`
and `:14` are four module-scope `.glob` calls at this base, unresolved here
because each receiver joins onto a name. Put one module-scope call on
`Path("<added directory>")` in the fixture. Assert its report names
`<module>` where the others name a function. One reports a call on a sibling
of the added directory, as `:11` sits beside `:10`. Put a module-scope call
on `Path` of a sibling directory beside the first, and assert it draws
nothing. One lists a `.glob` whose pattern is not a literal as unresolved
wherever its receiver resolves. Spell that sibling call `.glob(name)`, its
name bound to a string. Assert it neither reported nor on the unresolved
list. One judges each call once, against the first directory it reaches.
Write a second spec file over the same commit, whose `touches` adds a file to
the parent directory as well. Assert that the parent's `.rglob(...)` is then
reported twice. It enumerates the parent and descends into the added
directory below it. One sends every `.glob` whose pattern is not a literal to
the unresolved list before it compares directories. One reports a call on a
directory itself only where its pattern matches the added file. Put a
`Path("<parent>").glob(name)` on the parent, its pattern a name bound to a
string. In the first run it is on the unresolved list. In the second run,
assert an enumerator report for it and for every other call on the parent.
That run still lists it once as unresolved, for the added directory below, as
item 6 says. Name the file the second spec adds so that `*.md` does not match
it. Assert exit 1 for both runs.

Criterion 3 kills nine. Put its calls in the shared fixture's test files,
beside criterion 2's. One drops the calls it cannot resolve. Give the fixture
eight calls whose directory does not resolve, and assert each listed with its
file and line. The first is a name, `DIR.glob("*")`, with `DIR` bound once at
module scope to `Path("<added directory>")`. The second is an attribute in
the real `TURNS_DIR` shape, `context.TURNS_DIR.glob("*.md")` under `from
<package> import <other>, context`. That is how `tests/test_context.py:8` and
`:384` spell it. The fixture holds no such module, and none is needed. The
third is `Path(__file__).resolve().parents[1].rglob("*")`, a subscript built
on `__file__`. The fourth is `Path(__file__).parent.glob("*")`, an attribute
built on it. The fifth is a function parameter, `os.walk(d)` inside a
function taking `d`. The sixth is a join onto a name, `(DIR /
"<child>").iterdir()`, the shape of `tests/ontology/ontology_paths.py:10`. The
seventh is `Path("<a>", "<b>").iterdir()`, a `Path` call with two literals.
The eighth is `os.listdir()`, an `os` call with no positional argument. One
resolves a name anyway. The first case kills it, since its name is bound to
the added directory. Assert that call is on the list and draws no enumerator
report. One resolves `__file__`. It resolves the third or the fourth case,
and then leaves it off the list. One resolves `Path` of any number of
literals. The seventh case names the added directory in two parts, so assert
it listed and not reported. One lists only the three method spellings and
drops an `os` call. The fifth and eighth cases kill it. One lists a call
whose directory resolves. Assert that none of criterion 2's calls is on the
list, save the parent's `.glob(name)`. One treats unresolved as a defect.
Write a third spec file over the same commit, with one added entry. Its
directory is neither at nor below any directory a fixture literal names.
Assert exit 0, and the count line and the eight unresolved lines as all it
prints. No second fixture is needed for it. One drops an ancestor `.glob`
whose pattern it cannot read. An implementation that resolves the receiver,
finds it an ancestor, and asks whether a literal pattern carries `**` passes
every case above. Criterion 2's `Path("<parent>").glob(name)` is that call.
In the first run, assert it on the unresolved list, neither absent nor
reported as a descent. One prints an unresolved call once per directory
taken. Run criterion 2's second spec, which takes two directories. Assert
each of the eight lines appears once, and the parent's `.glob(name)` once.

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
fixture repo's own `tests/`, one of them in `tests/sub/`, and commit them. The
three witnesses share that one fixture, and no witness builds a second. Do not
copy this repository into the fixture. The spec file each witness reads is
written in the fixture's working tree and committed nowhere.

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

**The shape is about 408 changed lines, and nothing here raises the tier**.
Neither file in `touches` sits under `.saffron/policy.yaml:34-58`'s
`elevate_on`. So this task runs at `risk: standard`, where `size` is advisory
against the `feature` ceiling of 600 (`saffron/gates/core/size.py:25`). The
estimate is derived per part for this narrowed spec, and the parts sum to
the total. In `driver.py`, 128 lines. 25 take the directories out of
`touches` and count the skips. 35 find the calls: the six spellings, each
file's name for `os`, which calls recurse, whether a pattern is a literal, and
the function holding each call. 15 resolve the three forms item 5 names. 45
are `cmd_enumerators` and what it prints. That covers the `GitError` catch
for an unresolvable `--base`, the order the usage failures take, and the
per-directory judging. It also covers the count line, the grouped reports and
the unresolved group. 8 register the subcommand. In the test file, 280 lines.
60 are a shared helper that builds the fixture repo and writes a spec file,
the fixture's calls included. Then 80, 95 and 45 for the three witnesses. So
128 and 280 make 408. A 25-line throwaway script held the call finder and
the three-form resolver, and ran over this base's `tests/`. It carried no
comments, no `_fail` paths and no report. Repo style and the reporting take that to 128.
`SA-0112` is the comparable cell in these same two files, at 99 lines in
`driver.py` and 144 in the test file. 408 sits 192 lines under the ceiling
that `SA-0106` (633) and `SA-0107` (1049) overshot. The turns fall with it.
The rate that put the 573-line draft of this spec at 145 to 169 implement
turns puts 408 lines at 103 to 120, against `max_turns: 150`. Do not go
looking for more to do. The three forms in item 5 are closed. A shape they do
not name belongs in the unresolved list rather than in a fourth form.

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