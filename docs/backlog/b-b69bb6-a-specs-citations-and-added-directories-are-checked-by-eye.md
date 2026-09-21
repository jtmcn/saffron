---
id: b-b69bb6
title: A spec's line citations and the directories it adds files to are checked by eye, and both are computable
status: partial
tier: 2
filed: 2026-09-20
specs: [SA-0114, SA-0115]
prs: [404, 406]
commits: []
cites: []
related: [b-281f0a, 130, b-865399]
---

## Problem

Filed 2026-09-20 from one spec taken end to end outside a loop run. `SA-0113`
was drafted by the `spec-writer` agent, read by `spec-reviewer`, revised, and
read again by a second reviewer. Branch `joel/spec-criterion-mutation`.

Three of the first review's six findings needed no judgement.

- The blocker. The spec added a file to `saffron/agents/prompts/turns/`, and
  `tests/test_context.py:383` globs that directory and compares it to a
  hand-written list of nine names. The test passes at base, so baseline
  subtraction does not absolve it, and the blocking `tests` gate fails every
  attempt. The file sat in `forbidden`, so the cell could not repair it.
- Two notes of citation drift. `saffron/agents/findings.py:41` was cited for a
  line that sits at `:42`, and `saffron/phases/review.py:413` for a helper
  ending at `:411`.

The second review then spent one of its six checks confirming by hand that
every citation resolves. Runs 8, 9 and 10 each recorded stale line numbers in
every spec they carried.

Both questions are computable. Resolve each `file:line` the spec quotes against
the base commit and report the ones that moved. For each directory the spec
adds a file to, find the tests that glob, iterate or enumerate it.

What the rounds cost, measured on this spec: the draft 35.7 minutes, the first
review 6.2, the revision 17.9, the second review 9.5.

## Done looks like

A command takes a spec path and a base commit. It prints the citations that no
longer say what the spec quotes, and the tests that enumerate a directory the
spec adds a file to. The `spec-writer` agent runs it before its own
self-review. The `spec-reviewer` agent's checks 2 and 6 then read its output in
place of deriving both by hand.

## Record

- 2026-09-20: filed from `SA-0113`'s two reviews. `SA-0092` and `SA-0112` are
  the precedent for the shape: a cell builds the command, and the prompt that
  reads it is a hand edit.
- 2026-09-20: where the command lives is open. `records/` is this repo's
  project-document package, "backlog items today, specs next", and item 170
  builds `saffron/record/` for the run record. The two names stand, settled
  with the session building 170, and a `CONTEXT.md` §8 entry separates them.
  `records/load.py:48` also holds a class `Record`, which the run record's
  protocol repeats.
- 2026-09-20: `SA-0114` is queued for the command. It goes in the spec loop's
  `.claude/skills/run-saffron-spec-loop/driver.py`, beside `check`, as
  `driver.py cite <spec-path> --base <commit>`. `records/` was the other
  candidate and is declined. It parses record frontmatter and reads no commit,
  where the driver already reads a tree at one (`_git`, `_spec_at`). `dead`'s
  roots cover `records/` and not `.claude/`. The prose half stays
  open here, as item `b-281f0a` left its own: the `spec-writer` agent running
  the command, and checks 2 and 6 reading its output, are by-hand edits after
  the cell lands.
- 2026-09-20: `SA-0114`'s spec review sized the two halves together at about
  540 changed lines, within 100 of the `feature` ceiling of 600. So the spec
  was cut to the citation half, and the directory half needs a second spec
  against this item. That half keeps the evidence gathered for the first:
  `tests/test_context.py:382-384` is the blocking listing. The call set is
  wider than `.glob`: `rglob`, `iterdir` and `os.walk` each enumerate a
  directory under `tests/` today (`tests/records/check.py:335`,
  `tests/test_cli.py:198`, `tests/test_saffron_gates.py:1009`,
  `tests/test_citations.py:148`). A witness that exercises one spelling passes
  an implementation knowing only that one.
- 2026-09-20: `SA-0115` is the directory half, queued behind `SA-0114`. Both
  specs edit the spec loop's `driver.py` and `tests/test_spec_loop_driver.py`,
  so the child declares `depends_on: [SA-0114]` and its cell is cut from that
  branch. It adds a second subcommand, `enumerators`, rather than more of
  `cite`. Two reasons. Nothing in it reads what `cite` prints. And a
  review at the child's own branch cannot check a sentence about code that
  sits on no branch yet. The call set was measured at `91ae49a0` while the spec was
  written. There are 35 enumerating calls under `tests/`, and a throwaway
  resolver over the declared set resolved 19 of them to a directory. Matching
  every `walk` attribute instead would add 12 calls that enumerate nothing,
  ten of them `ast.walk`.
- 2026-09-21: `SA-0114` built `cite` (#404) and `SA-0115` built `enumerators`
  (#406) in the spec loop's run 11. The directory half resolves only literal
  receivers, so on this repository it lists all 35 calls as unresolved.
  Resolution follows in item b-f45f73, and `cite`'s precision in item b-61993a.
- 2026-09-21: #404 and #406 merged, and `SA-0114` and `SA-0115` retire to
  `done/`. `partial`, because neither agent runs the commands yet.
