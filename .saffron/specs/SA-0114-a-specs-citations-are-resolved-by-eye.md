---
id: SA-0114
title: a spec's line citations and the directories it adds files to are resolved by eye, one review at a time, and both are computable
type: feature
priority: 2
depends_on: []
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
      `driver.py cite` takes a spec path and a base commit. It reads the spec
      from the working tree, and reads every path the spec cites at that
      commit. A citation naming a path the commit holds no file at is
      reported, and so is one whose line number lies past the end of that file
      there. A citation resolving at that commit draws no report. A file the
      working tree changed after the commit is judged at the commit. The
      command exits 1 after reporting anything and 0 after reporting nothing.
    witness: tests/test_spec_loop_driver.py::test_cite_resolves_a_specs_citations_at_the_base_commit
  - claim: >-
      A citation written as a line number with no path takes the path named
      last before it in its own paragraph, and resolves against that path. One
      whose paragraph names no path before it is reported as anchored to
      nothing. A paragraph never inherits a path from the paragraph above it.
    witness: tests/test_spec_loop_driver.py::test_cite_anchors_a_bare_line_number_inside_its_own_paragraph
  - claim: >-
      A citation is reported as moved where the sentence around it holds
      backticked text, the cited file carries that text at the base commit,
      and no line of the cited range carries it. The report names the lines
      that do carry it. Backticked text a cited range carries draws no report,
      and backticked text its file carries nowhere draws none either.
    witness: tests/test_spec_loop_driver.py::test_cite_reports_a_citation_whose_quoted_text_sits_on_other_lines
  - claim: >-
      For each `touches` entry naming no file at the base commit, `cite` names
      every test under `tests/` there that enumerates a directory of that
      path, each with its own file and line. A test enumerating an unrelated
      directory is left out, and so is one whose literal pattern rejects the
      added file's name. A `touches` entry naming a file at that commit
      contributes no candidate.
    witness: tests/test_spec_loop_driver.py::test_cite_names_the_tests_that_enumerate_a_directory_a_spec_adds_to
---

## Context

Backlog item **b-b69bb6** is
`docs/backlog/b-b69bb6-a-specs-citations-and-added-directories-are-checked-by-eye.md`,
tier 2. It was filed on 2026-09-20 from one spec carried end to end outside a
loop run. `SA-0113` was drafted, reviewed, revised and reviewed again. Three of
the first review's six findings needed no judgement: one blocker about a test
that globs a directory the spec adds a file to, and two notes of citation
drift. The second review then spent one of its six checks confirming by hand
that every citation resolves.

Every sentence here about current code was read at `3c746ac0` on 2026-09-20.

**The spec loop's driver is where a computed check for a spec review lives**.
`cmd_check` at `.claude/skills/run-saffron-spec-loop/driver.py:1683-1712`
judges the ceilings comparison and returns 1 on a blocker. `SA-0092` built the
`ceilings:` line and `SA-0112` built that verdict, both in this file, and both
left the prompt half to a by-hand edit. Item **b-281f0a** carries that split
and records it as settled.

**The driver reads any commit already**. `_git` at
`.claude/skills/run-saffron-spec-loop/driver.py:85-89` runs git in the repo. It
raises `GitError` on a non-zero status. `_spec_at` at `:1425-1448`
reads `git ls-tree -r` and `git show <commit>:<path>` to recover a spec as it
stood at a commit. `_fail` at `:75-78` prints to stderr and returns 1, with the
comment "`saffron/cli.py` reserves 2 for infrastructure".

**A spec review resolves both questions by reading**. Check 2 at
`.claude/agents/spec-reviewer.md:57-63` asks for every file the change must
edit, "tests that assert the old behaviour" among them. Check 6 at `:126-132`
asks a reader to check "every sentence that says what the code does now"
against `base`. Check 6's own rule for a spec author is at
`docs/agents/issue-tracker.md:157-164`: "Every sentence that says what the code
does now carries a `file:line` you read while writing that sentence."

**The blocking test that `SA-0113` ran into is a directory listing**.
`TURN_PROMPTS` at `tests/test_context.py:369-378` is a hand-written dict of
nine turn prompt names. `test_every_turn_prompt_file_is_loaded_by_something`
at `:382-384` asserts that dict's keys equal
`{path.stem for path in context.TURNS_DIR.glob("*.md")}`. `TURNS_DIR` is
`PROMPTS_DIR / "turns"` at `saffron/agents/context.py:22`. The test passes at
base, so baseline subtraction absolves nothing, and a tenth prompt file fails
the blocking `tests` gate on every attempt.

**Nothing in the tree resolves a `file:line`**. `tests/test_citations.py`
covers the neighbouring question and stops short of this one. Its module
docstring at `:1` says every `§N` and appendix citation resolves to something
that exists. `_ROOTED_PATH` at `:321-323` matches a repo-rooted path under six
top-level directories, and `.claude` is not among them. It matches no line
number, and no test compares a cited line against what that line holds.

**The `prose` gate reads this driver and its tests**. `in_scope` at
`.saffron/gates/prose.py:188-193` sends a `.py` path under `CODE_DIRS` to the
comment and docstring rules. `CODE_DIRS` at `:48-58` holds `tests/` and
`.claude/`.

**Neither file in `touches` is scanned by `dead`**. `ROOTS` at
`.saffron/gates/dead.py:21-29` names `saffron`, `harness`, `images`, `records`,
`ontology`, `hooks` and `.saffron/gates`.

**Two files hold every caller of this driver's code**. A `git grep` for
`driver.py` at this base returns `.claude/agents/spec-reviewer.md`,
`.claude/agents/spec-writer.md`, the skill's `SKILL.md`, `GOTCHAS.md` and
`REVIEW-PROMPT.md`, `.saffron/deadcode-allow.py`, two retired specs and a
dozen backlog records. Each names the command in prose and calls nothing.
`tests/test_spec_loop_driver.py` is the one importer: it execs the driver
through `importlib.util` at `:19-26`. Both files are in `touches`, and every
other reader is `forbidden`.

## Problem

Two of a spec review's six checks rest on work with a right answer, and a
paid reader derives it one spec at a time.

- **A citation is resolved by opening the file**. The reviewer reads each
  `file:line` the spec quotes, opens that file at `base`, and decides whether
  the line still says what the sentence says. Runs 8, 9 and 10 each recorded
  stale line numbers in every spec they carried. On `SA-0113` the drift was
  two lines wide: `saffron/agents/findings.py:41` for a line sitting at `:42`,
  and `saffron/phases/review.py:413` for a helper that ends above it.
- **A directory listing is found by searching for one**. A spec that adds a
  file to a directory some test enumerates fails the blocking `tests` gate on
  every attempt. The reviewer finds that test by guessing which search to run.
  On `SA-0113` the file also sat in `forbidden`, so the cell could not repair
  it.
- **The answers are computable and nothing computes them**. Resolving a
  `file:line` against a commit is two git reads. Finding the tests that
  enumerate a directory is a scan of the test tree for a listing call.
- **What the rounds cost, measured on `SA-0113`**: the draft 35.7 minutes,
  the first review 6.2, the revision 17.9, the second review 9.5. Item
  b-b69bb6 is first of three in `docs/backlog/PRIORITY.md:173-177` for that
  reason.

The command is `cite`. It takes the spec's path and `--base`, and it prints
what it can prove wrong. Items 1 to 4 below are the citation half, and items 5
and 6 are the directory half.

1. **What a citation is**. Backticked text of the form `<path>:<n>` or
   `<path>:<n>-<m>`, read out of the spec file as text. A form with no path,
   such as a backticked colon and a number, is a citation too. It takes the
   path named last before it in its own paragraph, which is the convention
   every recent spec writes in. `SA-0113` carries about forty of them.

2. **Where each half is read**. The spec comes from the path on the command
   line, in the working tree, so a spec no commit holds yet is readable. Every
   other file is read at `--base`, through the `git show` call at
   `.claude/skills/run-saffron-spec-loop/driver.py:1444`, inside `_spec_at`
   (`:1425-1448`). The writer agent runs this before committing its draft, and
   the reviewer runs it against a branch head.

3. **What the citation half reports**. A path the base commit holds no file
   at. A line number past the end of that file there. A citation with no path
   and no path before it in its paragraph. And a citation whose quoted text
   moved, which is item 4. A citation with none of those defects prints
   nothing, so the output is a defect list rather than a table to read.

4. **What counts as moved**. The sentence around a citation names things in
   backticks, and one of them is what the sentence claims sits at that line.
   So take the backticked text in that sentence, leaving out the citations
   themselves. The cited file at base carries one of those strings on some
   lines. Where no line of the cited range is among them, the citation is
   reported as moved, naming the lines that do carry it. That is the
   `saffron/agents/findings.py` drift exactly, and it names the fix as well as
   the defect.

   **This half reports what it can prove and stays quiet otherwise**. Text
   the cited range carries suppresses the report, even where the sentence's
   other names moved. A common word carried at the cited line by accident
   suppresses it too. The direction is deliberate. A reviewer who reads a short
   list of proven misses keeps check 6. A reviewer given a long list of guesses
   stops reading the list.

5. **What the directory half reads**. A `touches` entry naming no file at the
   base commit is a file the spec adds. Its directories are the ancestors of
   that path, from the file's own directory up to the repo root. A test
   enumerates one of them where it calls a listing function on an expression
   that names that directory. The call names it either as a string or through
   a constant spelled after it, which is what `context.TURNS_DIR` is at
   `saffron/agents/context.py:22`.

6. **What the directory half reports**. Each call site under `tests/` at base,
   with its file, its line and the directory it matched. A call carrying a
   literal pattern is dropped where that pattern rejects the added file's name.
   That keeps a scan for `*.py` files off a spec adding a `.md` one. The reader
   decides what to do about each candidate. The command reports them and judges
   none.

7. **What the exit status means**. 1 after reporting anything, and 0 after
   reporting nothing. `cmd_check` at
   `.claude/skills/run-saffron-spec-loop/driver.py:1683-1712` returns 1 the
   same way, and `_fail` at `:75-78` explains why 2 stays reserved. A spec path
   naming no file and a `--base` git cannot resolve are usage failures, and
   they take `_fail`'s 1 without reaching either half.

## Out of scope

**The prose half of item b-b69bb6**. The item asks that the `spec-writer` agent
run this command before its own self-review. It asks that the `spec-reviewer`
agent's checks 2 and 6 read its output. Both are prompts, and no test watches
one. `.claude/agents/**` and the skill's `SKILL.md` are `forbidden` here. This
is the order `SA-0092` and `SA-0112` took, which item b-281f0a records as
settled: the cell ships the command, the operator wires the prose to it
afterwards. So the command this spec adds is called by nothing the day it
lands, and that is the expected state rather than an omission. Two lines are
the ones to leave alone rather than the ones to fix.
`.claude/agents/spec-reviewer.md:19-20` names `driver.py history <SPEC-ID>` as
what a review runs. `:30` limits a reviewer's Bash to "those git commands and
`driver.py history` only".

**The other four checks a spec review runs**. Checks 1, 3, 4 and 5 stay where
they are. Item b-281f0a owns them, it is `partial`, and its one open half is a
parametrised-witness check in `tests/test_queued_specs.py`. That file is
`forbidden` here. A new test there passes with this diff's source reverted,
because that source is `driver.py`, which such a test never reads.

**`§` citations**. `tests/test_citations.py` covers every `§N` and appendix
citation over the whole tree, on every `make check`. Add nothing for them, and
edit nothing in that file. It is `forbidden`.

**Enumerators outside `tests/`**. `saffron/agents/context.py:212` builds a
digest over
`PROMPTS_DIR.rglob("*.md")`, and a file added under it moves that digest. The
directory half scans `tests/` alone, because the failure this item was filed
about is a blocking `tests` gate. A production enumerator matters through the
test that pins its result, which the scan finds by that test's own call or
misses. Say so in your notes rather than widening the scan.

**Judging what it reports**. The command names candidates. It decides no
severity, edits no spec, and rewrites no citation. A moved citation is
sometimes the sentence that is wrong rather than the number.

**Every other subcommand**. `snapshot`, `next`, `record`, `drop`, `hold`,
`probe`, `status`, `stack`, `rebase`, `size`, `history`, `check` and `pattern`
keep the output and the exit status they have at base. Read no ledger here.
`cite` reads the tree and nothing else, so `_ledger_and_repo` at
`.claude/skills/run-saffron-spec-loop/driver.py:136-144` plays no part.

## Notes for the agent

**This change is new code, so no criterion declares a mutant** (§5.4.1). The
subcommand, its helpers and every sentence it prints do not exist at base, and
nothing there determines their spelling. Expect the `witness` gate to report
`skip`, with a summary saying the spec declares none. `SA-0112` ran under the
same limit in this same file. The names of the helpers and the exact wording
of each reported line are yours.

**No term here is new, so no vocabulary follow-up is owed**. *Citation* is the
word `tests/test_citations.py` uses in its module docstring at `:1`. It covers
a `§N` or an appendix reference there. The command reports candidates for a
reader, and files no finding, so `Finding` and `Severity` keep the meanings
`CONTEXT.md` gives them. `ontology/` is `forbidden` here.

**`cite` is the subcommand name, and `--base` defaults to `origin/main`.** `uv
run .claude/skills/run-saffron-spec-loop/driver.py cite
.saffron/specs/SA-0114-a-specs-citations-are-resolved-by-eye.md`. Register it
beside `check` in `main`
(`.claude/skills/run-saffron-spec-loop/driver.py:1838-1842`). The default
matches what a spec review is told at `.claude/agents/spec-reviewer.md:15-16`:
"`base:` the commit a cell would be cut from. `origin/main` when your prompt
names none." Do not name the command `preflight`. `CONTEXT.md:521-522` defines
**Preflight** as per-repo readiness at batch start, and a second meaning for it
is a vocabulary defect rather than a naming choice.

**Read `REPO` inside the function, never as a default argument value**. A
default binds at definition time. `tests/test_spec_loop_driver.py:371` and
`:613` monkeypatch `driver.REPO` to a scratch root. Helpers that read the tree
take the root as an argument, and `cmd_cite` passes the module's `REPO`. The
git fixture the witnesses need is already there: `_git` and `_commit` at
`:116-127` and `empty_repo` at `:129-137`, which blinds the repo to the host's
git config.

**Name the wrong implementation each witness must kill.** Criterion 1 kills
four. One reads the cited file from the working tree, which the witness catches
by rewriting a committed file after the commit. One reports a citation that
resolves. One returns 0 after reporting a defect, or 1 after reporting none.
One reports a line number equal to the file's last line, which is inside the
file and not past its end. Drive a clean spec and a defective one in the same
witness, so the zero case is pinned beside the one case.

Criterion 2 kills three. One drops a bare line number rather than resolving it.
One lets a paragraph inherit the path from the paragraph above it. The witness
catches that with a second paragraph whose own bare citation would resolve
against the wrong file. One drops an unanchored bare number without a word.
Make the two paragraphs cite files of different lengths, so an inherited path
reports a defect the anchored one does not.

Criterion 3 kills three. One reports any citation whose range lacks the
sentence's backticked text, which the third case kills: text the file carries
nowhere is a name from elsewhere, not a moved line. One searches the whole file
and never the range, which reports nothing at all. One reports the citation
without naming the lines that carry the text, which is the half that makes the
report worth reading. Put a second occurrence of the text in the file, so a
report naming one line and a report naming both are distinguishable.

Criterion 4 kills four. One scans for listing calls and ignores which directory
they name. One takes every `touches` entry rather than those naming no file at
base. One ignores the literal pattern, which the `*.py` case kills. One matches
the file's own directory alone, so a test enumerating a parent directory is
missed. Build the fixture so the added file sits two directories deep, and put
the enumerating call on the parent.

**Each witness is a plain `def`, never parametrised.** `criteria` matches a
bare node id against the names the suite collected, by exact string. A
`pytest.mark.parametrize` test collects under a name no criterion can name
(backlog item 159). Four cases in one witness is one `def` driving four.

**Each witness must fail with your source reverted.** `revert` re-runs every
test your diff adds, whether or not a criterion names it. So write no test that
passes at base. The module execs `driver.py` through `importlib.util` at
`tests/test_spec_loop_driver.py:19-26`, and a reverted run then fails on the
missing attribute, which is what `revert` needs to see. Load nothing new at
module scope: a module-scope import of a name this change adds turns that run
into a collection error, which `revert` reads as `skip`.

**Build the fixtures as real commits.** Both halves read the tree at a commit.
A witness that stubs `_git` pins your own parsing rather than git's answer. The
file's own shape is real git in a temporary repo, which
`tests/test_spec_loop_driver.py`'s module docstring at `:1-2` states. Write the
source files, commit them, and pass that commit as the base. The spec file each
witness reads is written in the working tree, and the citation witnesses need
it committed nowhere.

**The spec file is read as text, apart from `touches`**. `load_spec` and
`parse_spec` come from `saffron.intake`, imported inside the function as
`cmd_size` does at `.claude/skills/run-saffron-spec-loop/driver.py:1346`. The
body's citations are text. A refused spec still carries citations worth
resolving. Decide which way you read it and say so in your notes. Whichever you
pick, a spec that fails intake must not crash the command.

**A sentence is what the drift half reads.** Split the paragraph's text on
sentence ends after joining its lines, because a spec wraps its prose. The
split is approximate: an abbreviation and a section number both carry a period.
An approximate split costs a report the command would otherwise print. It never
costs a false one: a wider sentence holds more text that suppresses the report.
Keep the paragraph as the unit for the path a bare line number anchors to.

**Match a directory by name, not by import.** Resolving `context.TURNS_DIR` to
a path means importing the module at base, which the command must not do. Read
the call's receiver as text instead, split it into words on non-word
characters and underscores, and compare those words with the directory names.
`TURNS_DIR` yields `turns`, and `(REPO / ".saffron" / "specs")` yields `specs`.
Python's own parser gives you the call sites and the receiver text without a
regular expression over source.

**The pattern test is a filename match.** Take the listing call's first
argument where it is a string literal. Compare the added file's name against it
with `fnmatch`, dropping a leading recursive segment. Where the argument is
absent or is not a literal, keep the candidate. A directory listing with no
pattern enumerates everything.

**Print a count of what was checked.** A command that prints nothing reads the
same whether it resolved forty citations or found none to resolve. One line
naming how many citations resolved and how many added files were searched for
is the difference between a pass and a no-op. `cmd_check` at
`.claude/skills/run-saffron-spec-loop/driver.py:1711` prints a clean-verdict
sentence for the same reason.

**The `prose` gate counts comment runs and docstrings per file.** It blocks
(`.saffron/policy.yaml:25`), and it subtracts the base's failures. A file
gaining a hit of one rule fails the attempt. Keep every comment to one or two
lines and every docstring under ten, `cmd_cite`'s included.
`hooks/prose_limit.py --file <path>` answers the same question for one file in
the working tree, and it is the cheap way to check before a gate does.

**Rename no existing test.** `census` compares collected names between base and
head and reads a rename as a removal. The four new tests belong at the end of
`tests/test_spec_loop_driver.py`, after
`test_only_probe_takes_a_command_after_the_separator` at `:1821`.

**The shape is about 410 changed lines, and nothing here raises the tier.**
Neither file in `touches` sits under `.saffron/policy.yaml:34-58`'s
`elevate_on`. So this task runs at `risk: standard`, where `size` is advisory
against the `feature` ceiling of 600 (`saffron/gates/core/size.py:25`). The
estimate is 175 in `driver.py` and 235 in the test file. `SA-0112` is the
comparable cell, in the same two files: one subcommand, one lifted selection
and four new tests, which its own estimate put at about 220. This change has
two halves rather than one, and the directory half walks a syntax tree. Do not
go looking for more to do.

Commit after each coherent step. Uncommitted work dies with the cell.
