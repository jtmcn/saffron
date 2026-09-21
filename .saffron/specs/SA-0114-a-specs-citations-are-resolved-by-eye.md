---
id: SA-0114
title: a spec's line citations are resolved by eye, one review at a time, and the answer is computable
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
      commit. A cited path counts where it holds a `/`. A bare filename counts
      where it carries a dot and that suffix is one the base commit's tree
      carries. The empty suffix is not one of them, whatever the tree holds at
      no extension. The command reads both spellings. A citation takes the
      form `<path>:<n>` or the form `<path>:<n>-<m>`, and the command resolves
      both. A citation naming a path
      the commit holds no file at is
      reported, and so is one whose line number lies past the end of that file
      there. That line number is `<m>` for a range and `<n>` for a single
      line. A citation whose path and line both resolve at that commit draws
      no path-or-line report. A file the working tree changed after the commit
      is judged at the commit. The command exits 1 after reporting a defect and
      0 after reporting none. It prints a line counting the citations it
      checked on every run, defect or none, and that line is not itself a
      defect.
    witness: tests/test_spec_loop_driver.py::test_cite_resolves_a_specs_citations_at_the_base_commit
  - claim: >-
      A citation written as a line number with no path takes the path named
      last before it in its own paragraph, whether that path was written with a
      line number of its own or as a backticked path alone, and resolves
      against that path. One whose paragraph names no path before it is
      reported as anchored to nothing. A paragraph never inherits a path from
      the paragraph above it. The command reads a bare citation written as
      `:<n>-<m>` as well.
    witness: tests/test_spec_loop_driver.py::test_cite_anchors_a_bare_line_number_inside_its_own_paragraph
  - claim: >-
      A citation is reported as moved where the sentence around it holds
      backticked text, the cited file carries that text at the base commit,
      and no line of the cited range carries it. The report names the lines
      that do carry it. Backticked text a cited range carries suppresses that
      sentence's report, whatever the sentence's other names do. Backticked
      text a file carries nowhere draws no report either.
    witness: tests/test_spec_loop_driver.py::test_cite_reports_a_citation_whose_quoted_text_sits_on_other_lines
---

## Context

Backlog item **b-b69bb6** is
`docs/backlog/b-b69bb6-a-specs-citations-and-added-directories-are-checked-by-eye.md`,
tier 2. It was filed on 2026-09-20 from one spec carried end to end outside a
loop run. `SA-0113` was drafted, reviewed, revised and reviewed again. Three of
the first review's six findings needed no judgement: one blocker about a test
that globs a directory the spec adds a file to, and two notes of citation
drift. The second review then spent one of its six checks confirming by hand
that every citation resolves. This spec is the citation half of that item. The
directory half is under **Out of scope**.

Every sentence here about current code was read at `901916a8` on 2026-09-20,
which is the commit a cell is cut from.

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
docstring "`saffron/cli.py` reserves 2 for infrastructure".

**A spec review resolves this question by reading**. Check 6 at
`.claude/agents/spec-reviewer.md:126-132` asks a reader to check "every
sentence that says what the code does now" against `base`. Check 6's own rule
for a spec author is at `docs/agents/issue-tracker.md:167-174`: "Every sentence
that says what the code does now carries a `file:line` you read while writing
that sentence."

**Nothing in the tree resolves a `file:line`**. `tests/test_citations.py`
covers the neighbouring question and stops short of this one. Its module
docstring at `:1` says every `§N` and appendix citation resolves to something
that exists. `_ROOTED_PATH` at `:321-323` matches a repo-rooted path under
seven top-level directories, and `.claude` is not among them. It matches no
line number, and no test compares a cited line against what that line holds.

**The `prose` gate reads this driver and its tests**. `in_scope` at
`.saffron/gates/prose.py:188-193` sends a Python path under `CODE_DIRS` to the
comment and docstring rules. `CODE_DIRS` at `:48-58` holds `tests/` and
`.claude/`.

**Neither file in `touches` is scanned by `dead`**. `ROOTS` at
`.saffron/gates/dead.py:21-29` names `saffron`, `harness`, `images`, `records`,
`ontology`, `hooks` and `.saffron/gates`.

**One file holds every caller of this driver's code**. A `git grep -l` for
`driver.py` at this base returns forty-three files, the driver itself among
them.
`tests/test_spec_loop_driver.py` is the only importer. It execs the driver
through `importlib.util` at `tests/test_spec_loop_driver.py:19-26`. The other
forty-one name the command in prose and call nothing. They are the two agent
definitions, the skill's three documents, `.saffron/deadcode-allow.py`, and
this spec with the two queued beside it and two retired ones. The rest are
nineteen backlog records, ten
other documents under `docs/`, and `tests/test_scheduler.py`, whose mention
sits in the queue smoke test's docstring. The importer and the driver are in
`touches`, and every other reader is `forbidden`.

## Problem

One of a spec review's six checks rests on work with a right answer, and a
paid reader derives it one spec at a time.

- **A citation is resolved by opening the file**. The reviewer reads each
  `file:line` the spec quotes, opens that file at `base`, and decides whether
  the line still says what the sentence says. Runs 8, 9 and 10 each recorded
  stale line numbers in every spec they carried. On `SA-0113` the drift was
  two lines wide: `saffron/agents/findings.py:41` for a line sitting at
  `saffron/agents/findings.py:42`, and `saffron/phases/review.py:413` for a
  helper that ends above it. Both files were long enough that both citations
  resolved, so only the quoted text tells them apart from a good one.
- **The answer is computable and nothing computes it**. Resolving a
  `file:line` against a commit is two git reads.
- **What the rounds cost, measured on `SA-0113`**: the draft 35.7 minutes,
  the first review 6.2, the revision 17.9, the second review 9.5. Item
  b-b69bb6 is first of two in `docs/backlog/PRIORITY.md:174-179` for that
  reason.

The command is `cite`. It takes the spec's path and `--base`, and it prints
what it can prove wrong.

1. **What a citation is**. Backticked text of the form `<path>:<n>` or
   `<path>:<n>-<m>`, read out of the spec file as text. A form with no path,
   such as a backticked colon and a number, is a citation too. It takes the
   path named last before it in its own paragraph, which is the convention
   every recent spec writes in. `SA-0113` carries about forty of them.

2. **What counts as a path**. Backticked text takes a citation's shape for
   reasons that are not citations. A host and a port, a clock time and a dotted
   module name followed by a number all do. So a path part counts only where
   it holds a `/`. A bare filename counts where it carries a dot and that
   suffix is one the base commit's tree carries. `CLAUDE.md:12` and
   `.saffron/gates/format:12` are citations. `localhost:8080`, `06:30` and
   `importlib.util:3` are not. No file in the tree ends in `.util`, and the
   other two carry no dot at all. Take the empty suffix out of the set before
   you use it. The tree holds 22 paths at no extension, `Makefile` and
   `.saffron/gates/format` among them, so leaving it in makes `localhost` a
   filename. The same test decides what a
   bare line number anchors to. A paragraph naming `importlib.util` before a
   bare line number therefore anchors past it. One `git ls-tree -r --name-only`
   at base gives you the suffix set. A path with neither a `/` nor such a
   suffix, a bare `Makefile` among them, is missed. That is the direction item
   5 explains.

3. **Where each file is read**. The spec comes from the path on the command
   line, in the working tree, so a spec no commit holds yet is readable. Every
   cited file is read at `--base`, through the `git show` call at
   `.claude/skills/run-saffron-spec-loop/driver.py:1444`, inside `_spec_at`
   (`.claude/skills/run-saffron-spec-loop/driver.py:1425-1448`). The writer
   agent runs this before committing its draft, and the reviewer runs it
   against a branch head.

4. **What the command reports**. A path the base commit holds no file at. A
   line number past the end of that file there. A citation with no path and no
   path before it in its paragraph. And a citation whose quoted text moved,
   which is item 5. A citation with none of those defects prints nothing, so
   the output is a defect list rather than a table to read.

5. **What counts as moved**. The sentence around a citation names things in
   backticks, and one of them is what the sentence claims sits at that line.
   So take the backticked text in that sentence, leaving out the citations
   themselves. The cited file at base carries one of those strings on some
   lines. Where no line of the cited range is among them, the citation is
   reported as moved, naming the lines that do carry it. That is the
   `saffron/agents/findings.py` drift exactly, and it names the fix as well as
   the defect.

   **This report names what it can prove and stays quiet otherwise**. Text
   the cited range carries suppresses the report, even where the sentence's
   other names moved. A common word carried at the cited line by accident
   suppresses it too. The direction is deliberate. A reviewer who reads a short
   list of proven misses keeps check 6. A reviewer given a long list of guesses
   stops reading the list.

6. **What the exit status means**. 1 after reporting a defect, and 0 after
   reporting none. The count line criterion 1 requires prints on both, and it
   is not a defect. `cmd_check` at
   `.claude/skills/run-saffron-spec-loop/driver.py:1683-1712` returns 1 the
   same way, and `_fail` at
   `.claude/skills/run-saffron-spec-loop/driver.py:75-78` explains why 2 stays
   reserved. A spec path naming no file and a `--base` git cannot resolve are
   usage failures, and they take `_fail`'s 1 without reaching any citation.

## Out of scope

**The directory half of item b-b69bb6**. It finds the tests that enumerate a
directory a spec adds a file to. It wants a second spec against that item
rather than a criterion here. `TURN_PROMPTS` at
`tests/test_context.py:369-378` is a hand-written dict of nine turn prompt
names, and `test_every_turn_prompt_file_is_loaded_by_something` at
`tests/test_context.py:382-384` asserts that dict's keys equal
`{path.stem for path in context.TURNS_DIR.glob("*.md")}`. `TURNS_DIR` is
`PROMPTS_DIR / "turns"` at `saffron/agents/context.py:22`. The test passes at
base, so baseline subtraction absolves nothing, and `SA-0113`'s tenth prompt
file failed the blocking `tests` gate on every attempt. Two things that half
will need were established while writing this spec. The call set is wider than
`.glob`: `rglob` at `tests/records/check.py:335` and
`tests/test_cli.py:198`, `iterdir` at `tests/test_saffron_gates.py:1009` and
`os.walk` at `tests/test_citations.py:148` each enumerate a directory under
`tests/` at this base. And a witness exercising one spelling passes an
implementation that knows only that one, so that half's needs two. Adding that
half here puts the diff within 100 lines of the `feature` ceiling, which the
size note below measures.

**The prose half of item b-b69bb6**. The item asks that the `spec-writer` agent
run this command before its own self-review. It asks that the `spec-reviewer`
agent's checks 2 and 6 read its output. Check 2 is scope
(`.claude/agents/spec-reviewer.md:57-63`) and check 6 is claims about current
code (`.claude/agents/spec-reviewer.md:126-132`). The citation half this spec
ships serves check 6 alone, and check 2 waits on the directory half. Both
are prompts, and no test watches one. `.claude/agents/**` and the skill's
`SKILL.md` are `forbidden` here. This is the order `SA-0092` and `SA-0112`
took, which item b-281f0a records as settled: the cell ships the command, the
operator wires the prose to it afterwards. So the command this spec adds is
called by nothing the day it lands, and that is the expected state rather than
an omission. Two lines are the ones to leave alone rather than the ones to fix.
`.claude/agents/spec-reviewer.md:19-20` names `driver.py history <SPEC-ID>` as
what a review runs. `.claude/agents/spec-reviewer.md:30` limits a reviewer's
Bash to "those git commands and `driver.py history` only".

**The other checks a spec review runs**. Checks 1 to 5 stay where they are,
check 2 among them: it is the directory half that would reach it, and that half
is out of scope above. Item b-281f0a owns them, it is `partial`, and its one
open half is a parametrised-witness check in `tests/test_queued_specs.py`. That
file is `forbidden` here. A new test there passes with this diff's source
reverted, because that source is `driver.py`, which such a test never reads.

**`§` citations**. `tests/test_citations.py` covers every `§N` and appendix
citation over the whole tree, on every `make check`. Add nothing for them, and
edit nothing in that file. It is `forbidden`.

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
word `tests/test_citations.py` uses in its module docstring at
`tests/test_citations.py:1`. It covers a `§N` or an appendix reference there.
The command reports candidates for a reader, and files no finding, so `Finding`
and `Severity` keep the meanings `CONTEXT.md` gives them. `ontology/` is
`forbidden` here.

**`cite` is the subcommand name, and `--base` defaults to `origin/main`.** `uv
run .claude/skills/run-saffron-spec-loop/driver.py cite
.saffron/specs/SA-0114-a-specs-citations-are-resolved-by-eye.md`. Register it
beside `check` in `main`
(`.claude/skills/run-saffron-spec-loop/driver.py:1839-1843`). The default
matches what a spec review is told at `.claude/agents/spec-reviewer.md:15-16`.
There `base:` is the commit a cell would be cut from, and a prompt naming none
means `origin/main`. Do not name the command `preflight`.
`CONTEXT.md:521-522` defines
**Preflight** as per-repo readiness at batch start, and a second meaning for it
is a vocabulary defect rather than a naming choice.

**Read `REPO` inside the function, never as a default argument value**. A
default binds at definition time. `tests/test_spec_loop_driver.py:371` and
`tests/test_spec_loop_driver.py:613` monkeypatch `driver.REPO` to a scratch
root. Helpers that read the tree take the root as an argument, and `cmd_cite`
passes the module's `REPO`. The git fixture the witnesses need is already
there: `_git` and `_commit` at `tests/test_spec_loop_driver.py:116-127` and
`empty_repo` at `tests/test_spec_loop_driver.py:129-137`, which blinds the repo
to the host's git config.

**Name the wrong implementation each witness must kill.** Criterion 1 kills
twelve. One reads the cited file from the working tree, which the witness catches
by rewriting a committed file after the commit. One reports a citation that
resolves. One returns 0 after reporting a defect, or 1 after reporting none.
One reports a line number equal to the file's last line, which is inside the
file and not past its end. One treats any backticked `<text>:<n>` as a
citation. To kill that one, put a host and port and a dotted module name in the
clean spec. It then reports two paths the commit holds no file at, where the
witness asserts no defect and exit 0. One counts a path only where it holds a
`/`, and skips every bare filename. One counts a bare filename only, and skips a
slashed path with no suffix. To kill both, give the defective spec two
citations. One is a bare filename whose suffix the tree carries, at a line past
its end. Give it a suffix no hand-written allowlist would hold, such as
`run.zzz`, and commit that file into the fixture. Only a set derived from
`git ls-tree` then accepts it. One is a slashed path with no suffix, which the commit holds no file
at. The witness asserts a report for each. One matches `<path>:<n>` alone and
reads no range. One reads a range's `<n>` and drops `<m>`. To kill both, give
the defective spec a third citation, a range whose start line the file holds.
Its end line sits past that file's end, and the witness asserts a report for
it. One takes the empty suffix from the
tree into the set. To kill that one, commit a file with no extension into the
fixture, and put `06:30` in the clean spec beside the host and port. One prints
its defects and no count
line,
which the clean case kills by asserting that line on stdout beside the exit 0.
One prints the count line on the clean run alone. The witness asserts the line
on the defective run too, carrying the number of citations it checked.
The clean spec must draw no moved-text report either, since that case asserts
exit 0 and criterion 3 reports on a citation that resolves: give each clean
sentence backticked text the cited range itself carries, or text the cited file
carries nowhere. Drive a clean spec and a defective one in the same witness, so
the zero case is pinned beside the one case.

Criterion 2 kills seven, over a fixture spec of three paragraphs, P1, P2 and
P3. One anchors only to a path written with a line number of its own, never to
a backticked path written alone. This spec's own **Context** writes the second
shape in its `tests/test_citations.py` paragraph, where a bare-path mention
carries `:1` and `:321-323`. P1 kills that one: a bare-path mention followed
by a bare citation that resolves against it, and no report asserted. One partitions
the backticked spans into citations and
paths, and anchors a bare number to a path alone, so a `<path>:<n>` token never
anchors. That is the commonest form a spec writes. One anchors to the last
backticked `<text>:<n>` without applying the path test. P2 kills both: a
`<path>:<n>` anchor, then a dotted module name, then a bare citation that
resolves against the anchor. The witness asserts no report for P2, and both
anchor spellings are then driven. One drops a bare line number rather than
resolving it. One lets a paragraph inherit the path from the paragraph above
it. One drops an unanchored bare number without a word. P3 kills all three: it
names no path before its bare citation, and the witness asserts a report
reading anchored to nothing. Write that bare citation as `:<n>-<m>`, with
`<m>` past the end of the file P1 names and inside the file P2 names. An
inherited path then prints something other than that report. One reads a bare
`:<n>` and skips a bare range. A skipped range leaves the witness no report to
read.

Criterion 3 kills eight, over five fixture cases. One reports any citation
whose range lacks the
sentence's backticked text, which the third case kills: text the file carries
nowhere is a name from elsewhere, not a moved line. One searches the whole file
and never the range, which reports nothing at all. One reports the citation
without naming the lines that carry the text, which is what makes the report
worth reading. Put a second occurrence of the text in the file, so a report
naming one line and a report naming both are distinguishable. That arrangement
is the first case, and the witness asserts both line numbers. One runs the
moved-text check on citations carrying a path alone. Write the first case's
citation as a bare number, anchored to a path named earlier in its paragraph.
A moved-text check that skips a bare citation then prints nothing, and the
witness catches it. One reads a range's first line alone. The second case cites
a range as `<path>:<n>-<m>`, and the sentence's backticked text sits on a line
inside that range below its first. The witness asserts no report for it. One
reports where
any of the sentence's backticked strings is absent from the range. To kill that
one, give a fixture sentence two backticked strings. The cited range carries
the second, and the file carries the first elsewhere. Assert no report. That is
the fourth case. One reads the sentence's first backticked string alone. One
skips a sentence holding more than one backticked string. The fifth case kills
both. Its sentence holds two backticked strings, and neither sits in the cited
range. The file carries the second elsewhere and the first nowhere. The witness
asserts exactly one report for that sentence.

**Each witness is a plain `def`, never parametrised.** `criteria` matches a
bare node id against the names the suite collected, by exact string. A
`pytest.mark.parametrize` test collects under a name no criterion can name
(backlog item 159). Five cases in one witness is one `def` driving five.

**Each witness must fail with your source reverted.** `revert` re-runs every
test your diff adds, whether or not a criterion names it. So write no test that
passes at base. The module execs `driver.py` through `importlib.util` at
`tests/test_spec_loop_driver.py:19-26`, and a reverted run then fails on the
missing attribute, which is what `revert` needs to see. Load nothing new at
module scope: a module-scope import of a name this change adds turns that run
into a collection error, which `revert` reads as `skip`.

**Build the fixtures as real commits.** The command reads the tree at a commit.
A witness that stubs `_git` pins your own parsing rather than git's answer. The
file's own shape is real git in a temporary repo, which
`tests/test_spec_loop_driver.py:1-2` states. Write the source files, commit
them, and pass that commit as the base. The spec file each witness reads is
written in the working tree, and the witnesses need it committed nowhere.

**The spec file is read as text**. A refused spec still carries citations worth
resolving, and the body's citations are text either way. Decide whether you
parse the frontmatter at all, and say so in your notes. `load_spec` and
`parse_spec` come from `saffron.intake`, imported inside the function as
`cmd_size` does at `.claude/skills/run-saffron-spec-loop/driver.py:1346`.
Whichever way you go, a spec that fails intake must not crash the command.

**A sentence is what the moved-text check reads.** Split the paragraph's text on
sentence ends after joining its lines, because a spec wraps its prose. The
split is approximate: an abbreviation and a section number both carry a period.
An approximate split costs a report the command would otherwise print. It never
costs a false one: a wider sentence holds more text that suppresses the report.
Keep the paragraph as the unit for the path a bare line number anchors to.

**Print a count of what was checked.** A command that prints nothing reads the
same whether it resolved forty citations or found none to resolve. One line
naming how many citations resolved is the difference between a pass and a
no-op. It prints on a clean run and a defective one alike. `cmd_check` at
`.claude/skills/run-saffron-spec-loop/driver.py:1711` prints a clean-verdict
sentence for the same reason.

**The `prose` gate counts comment runs and docstrings per file.** It blocks
(`.saffron/policy.yaml:25`), and it subtracts the base's failures. A file
gaining a hit of one rule fails the attempt. Keep every comment to one or two
lines and every docstring under ten, `cmd_cite`'s included.
`hooks/prose_limit.py --file <path>` answers the same question for one file in
the working tree, and it is the cheap way to check before a gate does.

**Rename no existing test.** `census` compares collected names between base and
head and reads a rename as a removal. The three new tests belong at the end of
`tests/test_spec_loop_driver.py`, after
`test_only_probe_takes_a_command_after_the_separator` at
`tests/test_spec_loop_driver.py:1821`.

**The shape is about 485 changed lines, and nothing here raises the tier.**
Neither file in `touches` sits under `.saffron/policy.yaml:34-58`'s
`elevate_on`. So this task runs at `risk: standard`, where `size` is advisory
against the `feature` ceiling of 600 (`saffron/gates/core/size.py:25`). The
estimate is 200 in `driver.py` and 285 in the test file, derived per part. In
`driver.py`: 70 lines to extract citations in both spellings and anchor the
bare ones. Another 45 resolve a path and a line range at base. Then 37 for the
moved-text check, 40 for
`cmd_cite` and what it prints, and 8 to register the subcommand. In the
tests: 25 for a shared helper that writes a spec file and commits a fixture
tree, then 110, 75 and 75 for the three witnesses. The first carries two spec
texts, a multi-file commit and a count line asserted on both runs. `SA-0112` is the comparable
cell, in these same two files. It spent 99 lines in `driver.py` and 144 in the
test file, on one subcommand with five verdicts and four witnesses. This
command parses prose and reads a tree at a commit, where that one read rows
already in hand. Its witnesses build real git fixtures where that one used the
ledger fixture. Twice that cell is the estimate. The directory
half of item b-b69bb6 was cut from this spec for that reason. With it, the same
derivation gave 570 lines, inside 100 of the ceiling that `SA-0106` (633) and
`SA-0107` (1049) overshot. Do not go looking for more to do.

**The ceilings, against `driver.py history SA-0114`.** `max_turns: 150` stands
against a comparison row that is a floor. The line marks `SA-0106`'s peak of
101t "a floor", because that cell ended `IMPLEMENTING error_max_turns` at its
own ceiling. So the 49t of headroom printed there is narrower than it reads.
The highest peak among the printed rows that ran to its own end is `SA-0089`'s
88t, and 150 clears that by 62t. `budget_usd: 26` stands against `SA-0106`'s
pre-REVIEW total of $14.73, above by $11.27. The most any one printed row spent
after that point is `SA-0107`'s $2.81 review plus $3.17 rebut, well inside that
remainder. `max_attempts: 3` is this file's standing level, as `SA-0112` ran.

Commit after each coherent step. Uncommitted work dies with the cell.
