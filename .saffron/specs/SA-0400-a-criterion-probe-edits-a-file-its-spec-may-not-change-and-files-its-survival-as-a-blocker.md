---
id: SA-0400
title: "A criterion probe edits a file its spec may not change, and files its survival as an adequacy blocker"
type: feature
priority: 3
risk: elevated
estimated_lines: 129
estimate_measured: true
touches:
  - saffron/cell/session.py
  - saffron/phases/review.py
  - tests/test_session.py
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
  - records/**
  - hooks/**
  - saffron/probe.py
  - saffron/intake.py
  - saffron/repos/**
  - saffron/gates/**
  - saffron/agents/**
  - saffron/cell/worktree.py
  - saffron/task.py
  - saffron/cli.py
  - tests/test_probe_check.py
  - tests/test_review.py
  - tests/test_queued_specs.py
  - tests/test_scheduler.py
budget_usd: 48
max_attempts: 3
max_turns: 200
acceptance:
  - claim: >-
      REVIEW refuses a criterion probe whose edit lies outside the spec's
      `touches` and off its own criterion's `subject`, before any cell
      applies it. `_apply_criterion_probes` normalises the edit's file as
      `probe_refusal` does. It refuses the pair when no `touches` glob
      matches that path under `scope.matches`, and the path differs from
      its criterion's `subject`. A refused pair is recorded `unproven`.
      Its reason names the normalised file, is its `summary`, and sits
      under `refusal`. It never reaches the mutator, files no adequacy
      finding, and counts among the refused on the REVIEW line. A list of
      only refused pairs enters no cell. A wrong version is never refused
      by this rule. A path `probe_refusal` refuses keeps that refusal's
      reason. The witness calls `_apply_criterion_probes` with touches
      src/*.py, lib/one.py and pkg/**. Probes on src/x.py,
      ./src/a.py, lib/one.py and pkg/deep/c.py reach the mutator.
      So do probes on other/s.py, ./other/s.py and pkg/z.py under a
      criterion whose subject is other/s.py, and a wrong version on
      elsewhere/w.py. Probes on src/deep/a.py, lib/one.pyc and
      ./lib/two.py are refused. So are one on other/t.py under that
      criterion and one on other/s.py under a criterion with no subject.
      A probe on tests/t.py and one on ../out.py keep their
      `probe_refusal` reasons. It asserts the mutator's exact sequence,
      each record, the one survivor's finding and the REVIEW line. A
      second call with one refused probe alone asserts that no cell is
      entered.
    witness: tests/test_session.py::test_a_criterion_probe_outside_the_specs_touches_is_refused_before_any_cell
    wrong_versions:
      - The rule applied to wrong versions too, so the wrong version on `elsewhere/w.py` is refused.
      - The glob matched with `fnmatch`, so `*` crosses a slash and `src/deep/a.py` reaches the mutator.
      - The glob matched as a prefix of the path, so `lib/one.pyc` reaches the mutator.
      - The raw path matched rather than the normalised one, so `./src/a.py` is refused.
      - The subject compared with the raw path, so `./other/s.py` is refused.
      - Any criterion's subject accepted, so the probe on `other/s.py` under the criterion with no subject reaches the mutator.
      - The subject's directory accepted, so `other/t.py` reaches the mutator.
      - A declared subject replaces `touches`, so `pkg/z.py` under the subject criterion is refused.
      - The scope rule asked before `probe_refusal`, so `tests/t.py` and `../out.py` carry the scope reason.
      - The pair recorded `unproven` with no `refusal` key, so the REVIEW line counts it as named.
      - A fixed sentence as the reason, which names no file.
      - The raw path named in the reason, so `./lib/two.py` appears in it.
      - The refusal made inside the probe cell, so a list of only refused pairs still enters one.
---

## Context

Backlog item **b-11e2ac**, found reviewing #1218 (`SA-0397`) and #1219
(`SA-0398`). It cites `DESIGN.md`
§5.4.1 and §5.5. Every line number below was read at `7219608c`.

**What happened**. Each spec's `touches` named one test file and nothing
else. Their texts sit under `~/.saffron/batches/v0/finish/89/ran/`. Every
surviving criterion probe edited a file the claims named only as
background. For `SA-0397` both survivors edited `.saffron/gates/prose.py`.
For `SA-0398` the four edited `saffron/gates/suite.py`,
`saffron/cell/worktree.py` twice and `saffron/cell/session.py`. Each
task's `criterion-probes.json` and `findings.json` under
`~/.saffron/batches/v0/` hold the edits and the six blockers. Each witness
stayed green, which was right. Both review seats on each pull request
judged all six to be edits aimed at code the witness never reads. REBUT
withdrew `SA-0398`'s four, and `SA-0397`'s two stayed as recorded
disagreement.

**Where a probe's edit is refused today**. The REVIEW block builds one
`pairs` list after the critic cell is torn down. Each criterion probe comes
first, paired with its criterion. Each wrong version follows, with its own
(`saffron/cell/session.py:3536-3555`). `_drive_cell` hands the list to
`_apply_criterion_probes` with `spec`, the task's `CellSpec`
(`saffron/cell/session.py:3559-3575`). That function opens at
`saffron/cell/session.py:2072`. Its first loop records a pair with no
edit as unproven. It then asks `probe_refusal` of the edit's file, and a
refused pair is recorded unproven with its reason under `refusal`
(`saffron/cell/session.py:2111-2122`). The inert-edit block follows
(`saffron/cell/session.py:2124-2144`). With no pair left the function
returns before any cell (`saffron/cell/session.py:2146-2147`).

**What `probe_refusal` reads**. Only the path
(`saffron/probe.py:156-170`). It normalises the file with
`posixpath.normpath` through `_repo_relative`
(`saffron/probe.py:144-153`). It refuses a path outside the tree, then a
repo with no test paths, then a path a declared test glob matches. It
matches each glob with `scope.matches`, where `*` stops at a slash and
`**` does not (`saffron/gates/core/scope.py:35-41`).

**What the host holds for each pair**. `CellSpec.touches` is the spec's
declared list (`saffron/cell/session.py:356`). A plan cannot be validated
against an empty one (`saffron/agents/artifacts.py:283-287`), so REVIEW
never runs with none. `Criterion.subject` is the path a claim is about,
`None` by default (`saffron/intake.py:168-171`). Load holds it to a
canonical path (`saffron/intake.py:86-90`, `:196-207`).

**How a wrong version is told from a criterion probe**. A wrong version's
entry carries a `version` key with the author's sentence
(`saffron/phases/review.py:726`, `:745`). A criterion probe's entry
carries `sentence` and never `version`
(`saffron/phases/review.py:627-632`). `_apply_criterion_probes` already
picks its edit noun by `entry.get("version")`
(`saffron/cell/session.py:2206-2208`). This spec relies on that `version`
key.

**What the criterion-probe session sees**. `criterion_probe_prompt`
substitutes the claim for `{spec}` and the diff, and nothing of
`touches` (`saffron/phases/review.py:508-525`). The prompt's own text,
`saffron/agents/prompts/criterion-probe.md`, names no file the
spec lists in `touches`.

**How refusals are counted**. `describe_criterion_probes` counts every
probe with a `refusal` key as refused, never as named
(`saffron/phases/review.py:651-673`). A pair this spec refuses is then
counted with no change to the function.

**The one direct caller in the tests**. `_run_apply_criterion_probes`
calls `session._apply_criterion_probes` with `spec=_spec()`
(`tests/test_session.py:15468`, `:15544`). `_spec` declares touches
`src/**` and `tests/**` (`tests/test_session.py:253`).

## Problem

In the first loop of `_apply_criterion_probes`, after `probe_refusal`
returns `None`, refuse a criterion probe that lies outside the spec's
scope. A pair whose entry carries a `version` key is a wrong version and
is never refused here. For a criterion probe, normalise the edit's file
as `probe_refusal` does. Refuse it when no glob in `spec.touches` matches
that path under `scope.matches`, and the path is not equal to the
criterion's `subject`. Use `scope.matches`, never `fnmatch` and never a
prefix test.

A refused pair is recorded as a `probe_refusal` refusal is: outcome
`unproven`, the reason as its `summary`, and the reason under `refusal`.
The reason names the normalised file and says it lies outside the
spec's `touches` and off the criterion's `subject`. The pair then joins
no later step.

Give `_run_apply_criterion_probes` an optional `spec` keyword, defaulting
to `_spec()`, so the witness can pass its own `touches`.

Reword the two docstrings that name only `probe_refusal` and `inert_edit`
as a refusal's source. They are `_apply_criterion_probes`'s
(`saffron/cell/session.py:2090-2099`) and `describe_criterion_probes`'s
(`saffron/phases/review.py:652-659`). The first is at ten lines already,
so reword it inside the lines it holds.

## Out of scope

- **The prompt**. The criterion-probe session is shown no `touches`, so a
  sentence telling it to stay inside them would name a list it cannot
  read. Showing it `touches` means a new placeholder and a new keyword on
  `run_criterion_probes`. A later spec can add both, and the host refusal
  holds either way. `saffron/agents/**` is forbidden here.
- **Wrong versions**. A spec's author declares them, and they stay as
  they are.
- **The session cost of a test-only spec**. Its criterion probes are all
  refused unless a criterion declares a `subject`, so their sessions buy
  nothing. A later spec can skip such a session.
- **Killed probes outside scope**. `SA-0398` also held three probes on
  `saffron/cell/worktree.py` that its witness killed. They would now read
  `unproven` and refused, and that kill is no longer recorded.
- **A glob in `subject`**. Load accepts a canonical path holding `*`. This
  rule compares the subject as a literal path.
- **Which files the inert read names**. Whether a pair this rule refuses
  joins the `files_after` read is left open, as `SA-0396` left it for a
  `probe_refusal` refusal.
- **A lens's own adequacy probe**. `probe_findings` checks it
  (`saffron/cell/session.py:1877`). This rule does not reach it.
- **A `retired_first`**. The new refusal declines edits REVIEW names,
  never a spec, so no queued spec is refused by it.
- **Hand edits, made in this spec's own pull request**. One sentence
  joins the `DESIGN.md` §5.4.1 paragraph on an edit a spec could not
  declare. It follows the sentence on the gate-only cell.

  > Before any cell, the host declines one whose file matches no `touches`
  > glob and is not its criterion's `subject`. It records the edit
  > `unproven` (`SA-0400`).

  `CONTEXT.md`'s Criterion probe entry gains one sentence after the one
  on the gate-only cell.

  > The host declines one whose file lies outside the spec's `touches` and
  > its criterion's `subject`. It records why under the probe's `refusal`
  > key (`SA-0400`).

## Notes for the agent

**The behaviour is new code**, so the criterion declares a witness and no
mutant, and `witness` will report `skip`. The refusal loop at
`saffron/cell/session.py:2113-2122` is extended rather than rewritten.

**At base the witness fails in its body**. Every probe reaches the
mutator, so the mutator's sequence is longer than the one it asserts.

**The witness** follows
`test_a_probe_cell_that_stops_is_entered_once_more_for_every_pair_left` in
`tests/test_session.py`. Call `_run_apply_criterion_probes` with a spec
built by `_spec(touches=[...])`, the three globs the claim names and no
`tests/**`. The helper's test paths are `tests/**`, so `tests/t.py` is
refused by `probe_refusal` first. Pass a mutator that records each edit's
`file`. Put the survivor first, on `src/x.py` with find `assert x == 1`,
so the helper's `read_at_head` stub finds its line. It is applied twice,
once for its witness and once for the whole `tests` gate. Script the
gate results as `pass`, `pass`, then `fail` for each later edit that
reaches the mutator, seven of them. Build the REVIEW line's input from
the probe entries, one entry per criterion. Use
`review.describe_criterion_probes`. It counts seven named over two
criteria, none unnamed and seven refused.

**Every other caller of `_apply_criterion_probes` in the tests** passes
`_spec()`, whose `src/**` covers each probe file they name. Each passed
unchanged under the prototype.

**The `prose` gate** counts each new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words.

**Size**. A prototype measured 101 changed tokens outside `tests/` and 416
under it, about 129 changed lines.
