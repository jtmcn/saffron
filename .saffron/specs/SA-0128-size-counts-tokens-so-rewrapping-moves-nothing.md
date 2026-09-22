---
id: SA-0128
title: The `size` gate counts physical lines, so a cell near its ceiling packs code onto long lines to pass
type: feature
priority: 2
depends_on: [SA-0125]
touches:
  - saffron/gates/core/size.py
  - saffron/agents/artifacts.py
  - saffron/cell/session.py
  - tests/test_size.py
  - tests/test_artifacts.py
  - tests/test_session.py
  - tests/test_spec_loop_driver.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
  - README.md
  - pyproject.toml
  - uv.lock
  - .saffron/**
  - .claude/**
  - ontology/**
  - tests/ontology/**
  - docs/**
  - images/**
  - harness/**
  - saffron/agents/prompts/**
  - saffron/gates/contract.py
  - saffron/gates/suite.py
  - saffron/gates/core/integrity.py
  - saffron/gates/core/scope.py
  - saffron/repos/**
  - saffron/phases/**
  - saffron/record/**
  - saffron/report/**
  - saffron/events.py
  - saffron/ledger.py
  - saffron/intake.py
  - saffron/task.py
  - saffron/cli.py
  - tests/test_events.py
  - tests/test_suite.py
  - tests/test_cli.py
  - tests/test_ledger.py
  - tests/test_ledger_fold_task.py
  - tests/test_fold.py
  - tests/test_package.py
  - tests/test_scheduler.py
budget_usd: 24
max_attempts: 3
max_turns: 150
risk: elevated
acceptance:
  - claim: >-
      A change that only moves whitespace counts zero changed tokens. The
      witness drives nine such moves through a real `git diff`: a line split
      in two, two lines joined, a string spread over five lines packed onto
      one, a block re-indented, spaces widened inside a line, a tab replacing
      spaces, a blank line added, a blank line removed, and trailing spaces
      added. For each, the `size` summary starts `0 changed tokens`. The
      same move with one token of the file replaced starts `2 changed
      tokens`.
    witness: tests/test_size.py::test_a_change_that_only_moves_whitespace_counts_no_tokens
  - claim: >-
      For each file in a diff, `size` counts the tokens added and removed by
      the shortest edit between that file's old and new token streams. Each
      stream holds the file's context lines and its removed or added lines, in
      diff order. The witness drives nine diffs. One token inserted counts 1.
      One token deleted counts 1. One token replaced counts 2. A line of five
      tokens added counts 5, and removed counts 5. Two tokens swapped count
      2. A two-token line moved past an unchanged line counts 2. The
      replacement of `beta alpha beta` by `alpha gamma beta` counts 2. Three
      tokens removed from one file and added to another count 6.
    witness: tests/test_size.py::test_the_count_is_the_fewest_tokens_an_edit_of_each_files_stream_needs
  - claim: >-
      The `size` ceilings are 1300 changed tokens for `bug`, 3000 for
      `feature` and 4200 for `refactor`, and `test`, `docs` and `chore` take
      4200. For each of those six types, a diff at the ceiling passes with the
      summary `<n> changed tokens within the <type> ceiling of <ceiling>`. A
      diff one token over fails, and its failure message reads `<n> changed
      tokens exceeds the <type> ceiling of <ceiling>`.
    witness: tests/test_size.py::test_each_type_is_judged_against_its_re_measured_ceiling_in_tokens
  - claim: >-
      The plan checkpoint prices a plan's `estimated_lines` at 4 changed
      tokens a line, and judges that price against the token ceiling. The
      witness drives `bug`, `feature`, `refactor` and `docs`. For each, at
      `elevated`, the largest estimate whose price is within the ceiling is
      accepted, and one line more is rejected. That rejection's message holds
      the failure message `size_gate` returns for a diff of that many tokens.
      At `standard` the estimate one line over is not rejected, and the
      advisory sentence the checkpoint records for it names its price and the
      ceiling.
    witness: tests/test_artifacts.py::test_the_plan_checkpoint_prices_an_estimate_at_four_tokens_a_line
---

## Context

Backlog item **b-89ec93**, found in the spec loop's run 12 (#418). The `size`
gate and its ceilings are `DESIGN.md` §5.4. The core/repo boundary it must
keep is §2.1, and the plan checkpoint is §5.3.

This spec stacks on `SA-0125`. Every sentence below about current code was
read at `0531fcd7` on 2026-09-22, which is `SA-0125`'s spec on `main`.
Sentences about the plan checkpoint's estimate cite `SA-0125` itself, because
its cell writes that code.

**The gate counts physical lines.**

- `_changed_lines` adds one per hunk line that starts with `+` or `-`
  (`saffron/gates/core/size.py:37-72`, the increment at `:71`). File headers
  are skipped by position, before each block's first `@@`.
- `size_gate` compares that count with `_CEILINGS.get(spec_type,
  _DEFAULT_CEILING)` (`saffron/gates/core/size.py:172-173`). The ceilings are
  300, 600 and 1000 (`:25`), and every other type takes 1000 (`:34`).
- Its summaries say `changed lines` (`saffron/gates/core/size.py:184`,
  `:197` and `:203`).
- A declared binary block returns `error` where the gate blocks
  (`saffron/gates/core/size.py:161-170`). Every binary path is named in the
  summary (`:176-177`).
- The diff it reads carries three context lines around each hunk
  (`saffron/cell/worktree.py:150`).

**The plan checkpoint reads the same table.** `saffron/agents/artifacts.py:21`
imports `_CEILINGS` and `_DEFAULT_CEILING`. `Plan.estimated_lines` says it
is "the same count `size_gate` takes off the real diff"
(`saffron/agents/artifacts.py:70-73`). The plan prompt asks for the estimate
in lines (`saffron/agents/prompts/implement.md:26-29`). `SA-0125` moves the
ceiling check out of `validate_plan` into a new function in
`saffron/agents/artifacts.py`. That function rejects an estimate over the
ceiling only where `size` blocks. Its rejection holds the gate's own failure
message (`.saffron/specs/SA-0125-the-plan-checkpoint-rejects-on-a-ceiling-size-would-not-enforce.md:219-231`).

**Tests that pin the old unit.**

- `tests/test_size.py:14-26` builds removed lines named like the added ones,
  `line0` upward. Under a token count those match and cancel.
- `tests/test_size.py:265` asserts `1 changed lines` in a summary.
- `tests/test_size.py:121-125` expects 400 lines to fail the `bug` ceiling.
- `tests/test_spec_loop_driver.py:160-179` pins the summary text and the
  ceilings 300, 600 and 1000.
- `SA-0125` writes three witnesses in `tests/test_session.py` and rewrites
  three ceiling tests in `tests/test_artifacts.py`. All six read `_CEILINGS`
  as a count of estimated lines (lines 234-276 of its spec).

## Problem

`SA-0117` ran at `elevated`. The ledger holds a `size` result of 1035
changed lines over its `refactor` ceiling of 1000, then one of 979. Twelve
lines of `saffron/ledger.py` now run past 88 characters, the longest to 193
(`saffron/ledger.py:513`). The rest of that file writes SQL over several
lines. Ruff ignores `E501` (`pyproject.toml:86`), and no gate objects. A cell that writes
readable code pays for it in `size`, and one that packs it does not.

The unit becomes whitespace-separated tokens, counted per file by a token
diff, so rewrapping and re-indenting cost nothing. The gate stays
language-agnostic (§2.1): a token is a run of characters between whitespace,
in every file alike.

1. **Count tokens.** For each file block, build two token streams from its
   hunks. The old stream is every context line and removed line, in order.
   The new stream is every context line and added line, in order. Split each
   line's content, after its one-character marker, with `str.split()`. The
   count is the tokens a shortest edit adds plus those it removes: the two
   lengths minus twice their longest common subsequence. Sum it over files.
   Header lines stay excluded by position, as today. Any other line, such
   as `\ No newline at end of file`, adds nothing to either stream.
2. **Re-measure the ceilings.** `bug` 1300, `feature` 3000, `refactor`
   4200. The default stays `refactor`'s. The notes give the method and every
   row.
3. **Say tokens.** The pass summary and the failure message name `changed
   tokens` where they say `changed lines` today.
4. **Price the estimate.** The plan prompt asks for lines, and it stays as
   it is. So the checkpoint multiplies `estimated_lines` by 4 before it
   compares. Declare the 4 in `saffron/gates/core/size.py` beside the
   ceilings, with the measured ratio in its comment, and import it from
   there. The rejection holds `size_gate`'s failure message for the priced
   count. The advisory sentence `SA-0125` returns names the price and the
   ceiling. Rewrite the `estimated_lines` docstring, which stops being true.
5. **Keep `SA-0125`'s tests green.** Its six tests keep their names and move
   to the new arithmetic. The notes say how.

## Out of scope

- **Binary and unreadable blocks.** They keep today's handling: `error`
  where `size` blocks and the path is declared, and a named hole in the
  summary otherwise. The wording of the `error` summary is yours.
- **Punctuation that joins tokens.** `f(` and `a)` on two lines are two
  tokens, and `f(a)` is one. A formatter that moves a break next to
  punctuation still moves the count by a few tokens. The operator chose
  whitespace tokens knowing this.
- **The plan prompt.** `saffron/agents/prompts/**` is `forbidden`. A prompt
  change needs a measured pass that a cell cannot run
  (`.github/pull_request_template.md`). The prompt keeps asking for lines,
  and item 4 prices them.
- **`DESIGN.md` §5.4's table row.** It says `diff lines` and names the old
  ceilings (`DESIGN.md:815`). It is `protected`, and the operator rewrites it
  by hand after this merges.
- **The spec-loop skill's docs and driver.** `.claude/**` is `forbidden`.
  Its prose about sizing in lines is the operator's to update. The driver
  calls `size_gate` and prints its summary as is
  (`.claude/skills/run-saffron-spec-loop/driver.py:595-604`).
- **`FAMILIES` and the event line.** `saffron/events.py` and
  `tests/test_events.py` are `forbidden`. Change the checkpoint's sentence
  through the function that builds it, not through the event's renderer.
- **Rows already in the ledger.** Past `size` summaries keep saying lines.

## Notes for the agent

**No mutants.** The counting is new code. The ceilings and the rate are new
numbers. So no `find` text is known before you write them. Each witness
is written to kill the wrong implementations listed below. A prototype ran
the witnesses of criteria 1 to 3 against each of theirs. Criterion 4 drives
code `SA-0125` writes, so it was not run. `witness` will report `skip`.

**Commit as each witness passes.** A long cell can reach its turn limit
before its first commit.

**Criterion 1.** Reuse `_real_repo` and `_real_diff` from `tests/test_size.py`
(`:170` and `:191`). Give each move its own subdirectory of `tmp_path` and its
own repo. Put an unchanged line before and after the moved text, so the move
sits inside a hunk with context. For the paired case, replace one of those
unchanged lines' tokens with a new one. Judge each diff with
`size_gate(diff, "bug", touches=[])`. The prototype drove all nine moves this
way, with nine rows of `(before, after)` text in one dict.

**Criterion 2.** Build each case as diff text with one file header block and
one `@@` line, as `_diff` does. The `greedy` case and the `swapped` case
must carry no context line, or a greedy matcher finds the fewest edits by
luck. The `moved past` case is `-alpha beta`, ` keep`,
`+alpha beta`. Assert on the count function directly. Keep its name, `_changed_lines`.
`tests/test_size.py:6-11` imports it at module scope. A new name there fails
collection once `revert` restores the old source, and `revert` then reports
`skip`. Import any name this change adds inside the test body.

These wrong implementations each fail criterion 2 in the prototype:

- `difflib.SequenceMatcher`, even with `autojunk=False`, counts the greedy
  case as 4. It matches the longest block first, which is not the fewest
  edits. Over the 97 past diffs it overcounted by up to 22% (`SA-0080`, 1524
  against 1250).
- Streams without context lines count the moved line as 0.
- A token multiset per file counts the swap as 0.
- One stream for the whole diff counts the cross-file case as 0.
- The net difference of the two stream lengths counts a replacement as 0.

A line-by-line count fails criteria 1 and 2 both. The prototype used a
bit-parallel longest common subsequence over Python ints (Hyyrö, 2004). It
took 6 ms on a past diff of 30,813 tokens, and 42 ms on a rewrite of
20,000 tokens on each side. A textbook `n × m` table is correct and much
slower on a large rewrite.

**Criterion 3.** Drive the six types with `_diff(added=n, removed=0)`. Write
the ceilings as literals in the test, since the claim pins them. Assert the
whole summary and the whole failure message.

**Criterion 4.** Drive the function `SA-0125` added to judge the estimate,
which `plan_checkpoint` calls after `validate_plan`. Import it and
`size_gate` inside the test body, never at module scope. For each type, read
the ceiling from `_CEILINGS` and `_DEFAULT_CEILING`. The accepted estimate is
the ceiling divided by 4, rounded down, and the rejected one is a line more.
Write the 4 as a literal, since the claim pins it. Build the comparison diff
as `_diff`-shaped text of that many single-token added lines. Assert that
`size_gate`'s failure message is a substring of the rejection's text. At
`standard`, pass the over estimate with an empty `elevate_on`, and assert that
the advisory sentence holds the price and the ceiling as numbers.

These wrong implementations fail it:

- comparing the unpriced estimate with the token ceiling
- pricing at any rate other than 4
- a rejection naming the estimate's lines in place of the price
- rejecting at `standard`

At base the estimate one line over is accepted, because the base ceilings
are lines.

**Tests to update, names kept.** `census` fails a test that disappears, so
rename none of these.

- `tests/test_size.py:14-26`: name removed lines apart from added ones, say
  `gone0` upward. Three existing tests then pass unchanged.
- `tests/test_size.py:121-125`: make each side half the `bug` ceiling plus
  one, read from `_CEILINGS`.
- `tests/test_size.py:265`: the readable hunk adds `z2 = 2`, which is 3
  tokens.
- `tests/test_spec_loop_driver.py:160-179`: the new ceilings, and `1
  changed tokens`. Each branch there adds one file holding one token.
- `SA-0125`'s ceiling tests in `tests/test_artifacts.py`, and its three
  witnesses in `tests/test_session.py`: an estimate "at the ceiling" becomes
  the ceiling divided by 4, rounded down. The diff a `GateSuite` judges
  carries that estimate times 4 tokens. Criteria 2 and 3 of `SA-0125` put the
  estimate 20 lines over the ceiling. That becomes the ceiling divided by 4,
  plus 20.

Edit `saffron/cell/session.py` only if `SA-0125` builds the advisory sentence
there. It is in `touches` for that case alone.

**How the ceilings were measured.** The ledger at `~/.saffron/ledger.db`
holds a `size` result for every attempt, and `tasks.pushed_sha` each task's
head. For each of 97 tasks, the diff was rebuilt with `worktree.DIFF_FLAGS`.
Its base was the run's `base_sha`, or for a stacked task the commit on its own
line whose diff reproduced the recorded line count exactly. All 97 reproduced.
Each diff was then counted in tokens as item 1 describes. Tokens per changed
line: median 4.25, aggregate 4.19, tenth to ninetieth percentile 3.37 to 5.58.

For each type, the ceiling is a value that disagrees with the fewest past
rows on pass or block. Among ties it is the multiple of 100 nearest the old
ceiling times 4.19. `bug`: 1300 disagrees on one row, the fewest possible.
`feature`: 3000 disagrees on four, the fewest possible, and any value from
2955 to 3563 does the same. `refactor`: 4200 disagrees on none. Every row that
flips ran at `standard`, where `size` was advisory. So no past task stops
differently. The rate of 4 is 4.19 rounded down, so the plan
checkpoint errs toward accepting a plan.

Rows as `spec lines/tokens`. `*` was over the old line ceiling, and `!` flips
under the new token ceiling.

```
bug 300 lines to 1300 tokens, 43 rows:
  SA-0065 32/218, SA-0121 51/255,
  SA-0078 80/483, SA-0076 82/484, SA-0075 97/389, SA-0105 102/561,
  SA-0097 107/464, SA-0083 109/496, SA-0092 109/512, SA-0098 112/402,
  SA-0104 115/640, SA-0077 123/696, SA-0074 128/483, SA-0072 134/645,
  SA-0095 137/719, SA-0084 144/598, SA-0099 150/945, SA-0094 155/985,
  SA-0091 166/810, SA-0082 167/668, SA-0096 167/758, SA-0081 183/766,
  SA-0118 198/745, SA-0064 198/879, SA-0103 203/783, SA-0066 209/813,
  SA-0071 215/818, SA-0085 221/1016, SA-0068 224/1044, SA-0111 242/703,
  SA-0122 242/820, SA-0102 266/1097, SA-0086 269/1059, SA-0119 287/1105,
  SA-0087 293/906, SA-0080 294/1250, SA-0088 299/1056, SA-0101 300/982,
  SA-0070 312/1380*, SA-0100 314/863*!, SA-0052 315/1473*,
  SA-0067 316/1316*, SA-0073 324/1485*.
feature 600 lines to 3000 tokens, 43 rows:
  SA-0014 128/550,
  SA-0090 155/461, SA-0045 175/781, SA-0017 177/848, SA-0061 243/1055,
  SA-0112 243/1084, SA-0049 247/1098, SA-0046 251/1186, SA-0024 262/1175,
  SA-0063 293/1544, SA-0043 306/2435, SA-0022 328/1766, SA-0114 330/1681,
  SA-0028 336/2003, SA-0015 340/1322, SA-0023 349/1754, SA-0062 350/1766,
  SA-0056 401/1978, SA-0057 412/1867, SA-0069 432/1719, SA-0058 433/2120,
  SA-0018 462/2057, SA-0025 465/2245, SA-0110 471/1543, SA-0089 477/1778,
  SA-0048 478/1989, SA-0113 479/1923, SA-0016 486/2002, SA-0026 487/2891,
  SA-0108 494/1759, SA-0087 515/1952, SA-0120 517/1928, SA-0029 548/2383,
  SA-0050 576/2407, SA-0109 584/2206, SA-0027 585/2955, SA-0054 586/2209,
  SA-0019 592/2346, SA-0116 619/2298*!, SA-0106 633/2422*!,
  SA-0115 659/2097*!, SA-0040 683/2875*!, SA-0107 1049/3564*.
refactor 1000 lines to 4200 tokens, 9 rows:
  SA-0093 324/1245,
  SA-0051 347/1444, SA-0042 359/1066, SA-0093 371/1470, SA-0055 413/1623,
  SA-0060 578/2490, SA-0041 739/2558, SA-0030 787/2579, SA-0117 979/3916.
test 1000 lines to 4200 tokens, 2 rows:
  SA-0013 9/43, SA-0079 54/270.
```

**Size.** The host's `size` gate still counts lines when this cell runs, and
the `feature` ceiling is 600. The prototype of criteria 1 to 3 measured 81
changed lines in `tests/test_size.py` and 68 in `saffron/gates/core/size.py`,
with almost no docstrings. Expect about 350 in all: 110 in `size.py`, 20 in
`artifacts.py`, 160 in `tests/test_size.py`, 45 in `tests/test_artifacts.py`,
20 in `tests/test_session.py` and 6 in `tests/test_spec_loop_driver.py`. `size`
blocks here, because `risk` is `elevated`.

**Prose.** Each touched file's `prose` count must not rise. `size.py`'s
docstrings carry em-dashes today. New comments and docstrings take no em-dash,
semicolon, contraction, perfect tense or hedge. Keep a docstring within ten
lines and a comment within two. Check each file with
`python3 hooks/prose_limit.py --file <path>`.
