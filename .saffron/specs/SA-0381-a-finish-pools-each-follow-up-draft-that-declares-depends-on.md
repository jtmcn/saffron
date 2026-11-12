---
id: SA-0381
title: "A finish pools each follow-up draft that declares `depends_on`, so finish 83 paid for six drafts and minted none"
type: bug
priority: 2
estimated_lines: 40
estimate_measured: true
touches:
  - saffron/follow_up.py
  - tests/test_follow_up.py
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
  - harness/**
  - images/**
  - records/**
  - hooks/**
  - saffron/agents/**
  - saffron/cli.py
  - saffron/intake.py
  - saffron/spec_review.py
  - saffron/task.py
  - saffron/batch.py
  - saffron/finish.py
  - saffron/qualify.py
  - saffron/ledger.py
  - saffron/scheduler.py
  - saffron/cell/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/record/**
  - tests/test_cli.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 30
max_attempts: 3
max_turns: 200
acceptance:
  - claim: >-
      `follow_up.write_follow_ups` cuts the lines of each top-level
      `depends_on` and `consumes` key from a parsed draft's frontmatter
      before `_validate` reads it, when the draft declares a `depends_on`
      entry. Every other line stays as the writer sent it, the body and
      block scalars included. `_validate`, `cite`, `judge`, the minted
      `Candidate`'s `spec` and `spec_sha`, the returned candidate's
      `spec_sha` and the recorded `follow_up` text all read the cut text. A
      cut text that does not parse leaves the draft as the writer sent it,
      so `_validate` pools it with `declares a depends_on entry`. The
      witness drives six groups. The first declares both keys in the flow
      form, and the second both in the indented block form. Both drafts
      of the third declare the indentless block form, and its first is
      judged red. The fourth also declares a budget above its origin's. The
      fifth reads its `depends_on` value again through a YAML alias. The
      sixth declares an empty list, which names no entry.
    witness: tests/test_follow_up.py::test_a_draft_declaring_depends_on_is_judged_minted_and_recorded_with_those_lines_cut
    wrong_versions:
      - The lines are cut after `_validate`, so the flow-form draft is still pooled.
      - Only the parsed spec drops its entries, and the cited, judged, minted and recorded text keeps the lines.
      - "The frontmatter is rendered again with `yaml.safe_dump`, so lines outside the two keys change."
      - The minted candidate keeps the session's own `spec_sha`.
      - The returned candidate keeps the session's own `spec_sha` while the minted one hashes the cut text.
      - "`judge` reads the session's own text."
      - "`cite` reads the session's own text."
      - Only the `depends_on:` key line is cut, and its block entries stay.
      - "`consumes` stays, so the block-form draft's cut text does not parse and it is pooled."
      - Every line in the whole text that starts with `depends_on:` is cut, the body's included.
      - An indented `depends_on:` line inside a folded claim is cut too.
      - A cut text that does not parse is sent back to the writer.
      - A cut text that does not parse pools with its own parse error.
      - Only a group's first draft is cut, so the resent draft is pooled.
      - A draft whose cut text does not parse is minted with its entries dropped, past `_validate`.
      - Every draft is cut, so the empty list's line is dropped from its text.
      - "`_validate` drops its `depends_on` check, so the alias draft is minted."
      - Only the flow form is cut.
---

## Context

Backlog item **b-4a9207**, filed 2026-11-02. It cites `DESIGN.md` §5.7.
Its 2026-11-12 Record line is this spec's evidence. Every line number below
was read at `049e53ed`.

**What a follow-up is.** ADR 7 says a follow-up has no `depends_on`, so it
is never a member spec (`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md:181`).
A follow-up stacks on the finishing layer, so every layer it grew out of
already sits below it. `CONTEXT.md`'s **Follow-up spec** entry says the same.

**How a draft is read now.** `write_follow_ups` parses each draft's text
(`saffron/follow_up.py:431-438`). It then calls `_validate`
(`saffron/follow_up.py:440-445`). `_validate` returns `declares a
depends_on entry` for any draft whose `depends_on` is not empty
(`saffron/follow_up.py:221-222`). A refusal charges the session and pools
the group at once, with no send-back (`saffron/follow_up.py:446-449`).
`cite` and `judge` run only after `_validate` passes
(`saffron/follow_up.py:454-470`). Both read `session.text`
(`saffron/follow_up.py:457`, `saffron/follow_up.py:465`). The minted
`Candidate` and the returned one carry `session.spec_sha`, and the recorded
text is `session.text` (`saffron/follow_up.py:488-511`).
`run_spec_writer` sets `spec_sha` to `hash_artifact` of the session's text
(`saffron/spec_review.py:690`).

**What reads the minted text later.** `record_spec_text` hashes the text it
records (`saffron/ledger.py:2089`). Before the cell, `_recorded_spec_text`
refuses a text that does not hash to its `spec_sha`
(`saffron/task.py:665-666`). It also refuses a text whose `depends_on`
differs from the handed spec's (`saffron/task.py:678-681`). So the minted
spec, its `spec_sha` and the recorded text must all be the same cut text.

**Why `consumes` goes too.** `Spec` refuses a `consumes` entry with no
`depends_on` (`saffron/intake.py:345-352`). A draft that copied both keys
would not parse with only `depends_on` cut.

## Problem

A finish pools every follow-up draft that declares a `depends_on` entry. It
pays for the whole draft first.

Finish 83 wrote three follow-up groups. Each became one `write` call, and
each call is one spec writer session in a critic cell
(`saffron/cli.py:1878-1913`). Each session made four agent calls: the
draft turn, its extraction turn, one in-session send-back and that
send-back's extraction turn. `SPEC_WRITER_SEND_BACKS` is 1
(`saffron/spec_review.py:580`). The session's own `faults` judged both
drafts with the policy's form gates (`saffron/spec_review.py:889`,
`saffron/cli.py:1176-1211`). Each judgement was a baseline suite and a head
suite. The finish log measured the three sessions as follows, with the SDK
turns of their four calls summed.

| group | origin | SDK turns | cost | suites |
| --- | --- | --- | --- | --- |
| `tests/test_qualify.py` | `SA-0378` | 30 | $1.85 | 4 |
| `saffron/qualify.py` | `SA-0378` | 48 | $4.00 | 4 |
| `tests/test_session.py` | `SA-0375` | 89 | $4.42 | 4 |

That is $10.27, 167 SDK turns and twelve suites. Each session ended, and
`_validate` pooled its group at once. The finishing suite never judged a
draft, and no citation was read. All six drafts declared
`depends_on: [SA-0378]` (`~/.saffron/batches/v0/83.follow-ups/events.jsonl`).
`SA-0378` is the top layer, whose head every session's cell sat on. The
third group's origin, `SA-0375`, declares no `depends_on` at all. So the
writer named the stack's top layer, not a copy of its origin's list.
`~/.saffron/batches/v0/finish/83/findings.json` holds the three pooled
findings with that reason.

It is not new. 55 findings in 16 of the 67 finish directories under
`~/.saffron/batches/v0/finish/` were pooled with `declares a depends_on
entry`. Finish 38 pooled 13 that way, and finish 73 pooled 11.

The fix is host-side and costs no prompt change. A follow-up's `depends_on`
says nothing the stack does not already hold.

1. **`saffron/follow_up.py`.** Add a helper that cuts the lines of each
   top-level `depends_on` and `consumes` key from a text's frontmatter. A
   key's lines are its own line and each indented or `- ` line after it.
   They end at the next top-level line or the closing `---`.
   In `write_follow_ups`, after the parse and before `_validate`, a draft
   whose parsed `depends_on` is not empty is parsed again from its cut text.
   When that parses, the cut text and its spec replace the draft's for
   everything after. When it does not, the draft stays as the writer sent
   it. Pass the cut text to `cite` and `judge`. Set both candidates'
   `spec_sha` to `hash_artifact` of it, and record it. Add one sentence to
   the module docstring. Leave the function docstring at its ten lines.
2. **`tests/test_follow_up.py`.** Two tests pin the old refusal. Each keeps
   its counts once its draft carries a second refusal. In `_eighteen_turns`,
   turn 5 also declares `budget=11.0`. Its needle in
   `test_a_group_the_host_refuses_or_the_sub_cap_cannot_cover_goes_to_the_pool`
   becomes `"budget"`. In
   `test_a_draft_sent_back_once_pools_on_its_second_refusal_and_never_past_the_sub_cap`,
   `depends_on_draft` also declares `budget=999.0`.

## Out of scope

- **A one-line finding fixed in the finishing layer.** The item's first
  "Done looks like" sentence stays open on b-4a9207.
- **The writer's prompt.** A prompt telling the writer to declare no
  `depends_on` would need a measured pass this spec does not carry.
  `saffron/agents/**` is forbidden.
- **A quoted key.** The cut reads a key spelled bare at the start of its
  line. A draft spelling `"depends_on":` keeps its line, parses with the
  entry, and `_validate` pools it as at base.
- **The send-back's quoted draft.** `send_back` quotes `session.text` to the
  writer (`saffron/follow_up.py:319-325`). It keeps quoting the writer's own
  text.
- **A log line naming the cut.** The writer's events log keeps the draft as
  sent, and the recorded text holds the cut one.
- **`removes` and `retired_first`.** Neither needs a `depends_on`, and both
  stay as the writer declared them.
- **`_validate`'s own check.** It stays, and pools a draft whose cut text
  does not parse.

## Notes for the agent

**The criterion is new code.** It declares no mutant, so `witness` will
report `skip` for it. The wrong versions under it name what its witness
must still catch.

**At base the witness fails in its body.** The first group's draft is
pooled, so the minted list is short. Import nothing the change adds at
module scope.

**Seeding the witness.** The prototype drove all six groups through one
`write_follow_ups` call with a `cite` double and a `judge` double. It read
each draft's id from the prompt's `id:` line, as
`test_a_draft_the_finishing_suite_fails_is_sent_back_once_with_its_failures_and_then_minted`
does. It wrote the flow, block, budget, alias and empty drafts by hand.
Each carried a body line starting with `depends_on:` and a folded claim
with an indented `depends_on:` line. The flow draft added
`consumes: [src/a.py:alpha]`, and the block draft added `consumes:` with
`  - src/a.py:alpha`. The alias draft added
`forbidden: *parents` after `depends_on: &parents [SA-0378]`. The third
group used `_candidate(..., depends_on=("SA-0378",))`, which writes the
indentless form, and its expected text is `_candidate` without it. Build
each expected text by hand as the draft with only those lines removed.
Compare it by `==` with the recorded text and with each text `cite` and
`judge` received. Compare `hash_artifact` of it with both candidates'
`spec_sha`.

**What the witness leaves undriven.** `consumes` in the indentless form,
since `_candidate` writes no `consumes`. The same key rule cuts it.

**Assert the positive half of each absence.** The cited list and the
judged list each equal five texts in order. They are the four cut texts of
groups one to three, then the sixth draft. That comes before the check that groups four and five were never
cited or judged. The fourth group's reason names its budget and not
`depends_on`. The fifth's reason equals `declares a depends_on entry`.

**No refusal of a queued spec.** This change pools fewer drafts and refuses
nothing new, so no `retired_first` entry applies.

**The `prose` gate** counts each new comment and docstring. Write none with
an em dash, a semicolon, a contraction, the perfect tense or a sentence
over 25 words.

**No `depends_on`.** No queued spec touches `saffron/follow_up.py` or
`tests/test_follow_up.py`.

**Size.** A prototype measured 158 changed tokens with `size_gate`, against
the `bug` ceiling of 1300, with 520 more under the test paths. It held the
helper, the cut, the witness and both updated pins. Every test in
`tests/test_follow_up.py` passed on it, with `tests/test_cli.py`'s follow-up
tests.
