---
id: SA-0325
title: "The finish pools a follow-up draft that does not parse without sending it back to the writer"
type: bug
priority: 2
estimated_lines: 44
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
  - images/**
  - harness/**
  - records/**
  - hooks/**
  - saffron/finish.py
  - saffron/qualify.py
  - saffron/intake.py
  - saffron/spec_review.py
  - saffron/end_review.py
  - saffron/cli.py
  - saffron/batch.py
  - saffron/ledger.py
  - saffron/scheduler.py
  - saffron/agents/**
  - saffron/phases/**
  - saffron/record/**
  - saffron/gates/**
  - saffron/cell/**
  - saffron/repos/**
  - tests/test_finish.py
  - tests/test_qualify.py
  - tests/test_cli.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 20
max_attempts: 3
max_turns: 120
risk: standard
acceptance:
  - claim: >-
      In `write_follow_ups`, a group whose first draft `intake.parse_spec`
      refuses gets one more `write` call, made through the `send_back`
      seam. Its reason is `follow-up text did not parse: ` and the
      `SpecError` text. The witness drives three refusals. One draft has no
      frontmatter block. One has a list item that opens with a backtick, so
      its frontmatter is not valid YAML. One parses as YAML but lacks the
      required `title`. Each second prompt begins with the first prompt in
      full. After it come the reason, then the refused draft. `emit` gets a
      line naming the group's task key, its file and the reason. Each
      second draft parses and validates, and is minted under the next id.
      Each first session is charged to the origin task as one `WRITING`
      attempt at its own cost. Each second session is charged to its
      minted task. Nothing is pooled, and the batch's spend counts all six
      sessions.
    witness: tests/test_follow_up.py::test_a_draft_that_does_not_parse_is_sent_back_once_with_its_error_and_then_minted
    wrong_versions:
      - The second prompt carries the draft and the first prompt but not the reason.
      - The second prompt carries the reason and the first prompt but not the draft.
      - The second prompt is the reason and the draft alone, so the findings and the assigned id are gone.
      - The second prompt puts the reason before the first prompt.
      - The second prompt puts the draft before the reason.
      - Only a draft with no frontmatter block is sent back, matched on its message.
      - The refused session is not charged before the send-back.
      - No line is emitted for a send-back.
      - The emitted line names the group but not the reason.
  - claim: >-
      A group is sent back at most once. When its second draft also fails
      to parse, it pools with `follow-up text did not parse: ` and the
      second draft's error, and no third call is made. A second session
      that sets a reset time, carries an error, or raises is handled as a
      first one is. A reset time pools its group and every later group. An
      error pools the group with it. A raise from the second call pools the
      group with `write raised`, and the raise goes no further. A second
      draft `_validate` refuses for its type pools with that reason. A
      first draft `_validate` refuses for its id, type, `depends_on`, budget
      or `touches` pools after one call, never sent back. Every session but
      the raised one is charged to the origin task, once each. The witness
      reads the origin's `WRITING` attempts' session ids in order. Both
      sessions' costs
      count against `cap_usd`. The send-back is priced after the first
      session's cost is counted. When what is left cannot cover
      `SPEC_WRITER_SESSION_USD`, the group pools with its first draft's
      parse reason and no second call is made. The witness's sub-cap run
      makes that true only once each session's cost is counted.
    witness: tests/test_follow_up.py::test_a_draft_sent_back_once_pools_on_its_second_refusal_and_never_past_the_sub_cap
    wrong_versions:
      - A second parse failure is sent back again, so a group makes three calls.
      - A draft `_validate` refuses is sent back too.
      - A draft refused for its type alone is sent back.
      - The second call sits outside the `try`, so its raise escapes `write_follow_ups`.
      - The send-back is priced against what was left before the first session ran.
      - The send-back is not priced at all.
      - The second session is charged but its cost is left out of what the sub-cap has spent.
      - A send-back the sub-cap cannot cover pools with the sub-cap reason, not the parse reason.
      - A reset time on a second session pools its own group but leaves later groups to be written.
      - A second parse failure charges the first session again, not the second.
  - claim: >-
      The seam is one closure in `write_follow_ups`, `send_back(reason)`,
      and it owns the whole send-back step. It charges the loop's refused
      session to the origin task. It pools the group with `reason` when the
      group was already sent back, or when `cap_usd` less what is spent is
      below `SPEC_WRITER_SESSION_USD`. Otherwise it emits its line, then
      makes the `write` call and returns its session. It returns `None`
      when it pooled. The witness prices a send-back where what is left
      equals `SPEC_WRITER_SESSION_USD`, and it is sent back. It reads
      `write` calls and emitted lines from one log. The send-back line
      comes after the first call and before the second. The pooled line
      comes last, with the second draft's parse reason.
    witness: tests/test_follow_up.py::test_a_send_back_is_priced_at_its_boundary_and_logged_before_its_call
    wrong_versions:
      - The send-back pools when what is left equals the session price, by `<=` where the group check uses `<`.
      - The send-back line is emitted after the second `write` call returns.
  - claim: >-
      The prompt `write_follow_ups` gives the writer has a line naming
      `bug` and `feature`, and that line names none of the other four spec
      types. The witness checks each of the six names `intake.SpecType`
      lists, as a whole word.
    witness: tests/test_follow_up.py::test_the_writers_prompt_names_bug_and_feature_as_the_only_types
    wrong_versions:
      - The line names `bug` alone.
      - The line names `bug`, `feature` and `test`.
      - The prompt names no type at all.
---

## Context

Backlog item **b-781ea4**, under ADR 7 (a stack batch writes its own
follow-ups) and `DESIGN.md` §4.2.1's finish. Every line below was read at
`5a9ee6d7`.

**The runs that found it.** In the spec loop's run 47, `saffron finish 51`
drafted three follow-ups. Two failed with "spec frontmatter is not valid
YAML", at a list item that opens with a backtick. The third declared
`type: test`. All three were pooled, and the finish spent $20.66 and filed
nothing. Run 48's `saffron finish 55` and run 49's `saffron finish 58`
pooled three more drafts with "spec has no YAML frontmatter block".

**Where a draft is pooled today.** `write_follow_ups` calls `write` once per
group (`saffron/follow_up.py:353-357`). It adds the session's cost to
`spent` (`:359`). A reset time sets `reset_reason` and pools the group
(`:361-365`), and every later group pools with it (`:289-291`). A session
error pools the group (`:366-369`). Then `intake.parse_spec` reads the
text. A `SpecError` charges the session to the origin task and pools the
group with `follow-up text did not parse: ` and the error
(`:371-376`). `_validate` refuses a draft that parses for its id, type,
`depends_on`, budget, `touches` or mutant (`:186-224`). Its reason pools
the group too (`:378-388`). A draft that passes is minted, and its session
is charged to the minted task (`:390-399`).

**The parse errors.** `parse_spec` raises `SpecError` with "spec has no YAML
frontmatter block" when no fence matches (`saffron/intake.py:330-332`). It
raises "spec frontmatter is not valid YAML" on a YAML error (`:334-338`)
and "spec frontmatter is invalid" on a field error (`:361-364`). It has
four more reasons. Three sit at `:339-358`, and the fourth is
`DisclosedMutantError`, a `SpecError` subclass (`:60`, `:409`).

**The sub-cap.** Each group is priced before its call. When `cap_usd -
spent` is below `spec_review.SPEC_WRITER_SESSION_USD`, the group pools with
"the spec writer session's sub-cap cannot cover another session"
(`saffron/follow_up.py:293-298`). The finish passes what is left of the
writer's share as `cap_usd` (`saffron/cli.py:1718-1719`).

**The writer's prompt.** `_prompt` builds the user prompt as lines
(`saffron/follow_up.py:154-183`). It names the assigned id and the budget
cap, and no type. `_validate` refuses any type but `bug` and `feature`
(`:199-200`). The writer's system prompt is shared. `saffron draft` and a
spec review's revision build it too (`saffron/cli.py:1485-1487`,
`:1371-1372`), and those write a spec of any type.

**The caller's `write`.** The finish's `write` opens a fresh cell and a
fresh writer session on each call (`saffron/cli.py:1673-1701`). So a second
call for one group is a new session that reads only its prompt.

## Problem

A drafted follow-up whose text does not parse is pooled at once. The writer
never sees why. Three runs in a row lost findings this way.

1. **The seam.** Add a closure `send_back(reason: str) ->
   SpecWriterSession | None` inside `write_follow_ups`, beside `_pool` and
   `_charge` (`saffron/follow_up.py:268-282`). It reads the loop's current
   `group`, `prompt`, `session` and origin task id, and `spent`. In order:
   - Charge the refused `session` to the origin task through `_charge`.
   - When this group was already sent back, or `cap_usd - spent` is below
     `SPEC_WRITER_SESSION_USD`, pool the group with `reason` and return
     `None`. Price it with `<`, as the group check does (`:293-298`).
   - Otherwise mark the group sent back. Emit one line naming its task
     key, its file and `reason`.
   - Call `write(group, …)` once and return its session. The prompt is
     `prompt` in full, then a short instruction to fix and resend the
     whole spec, then `reason`, then the refused draft's text.
2. **The parse branch.** A first draft that does not parse calls
   `send_back` in place of today's charge and pool (`:373-376`). The
   reason is `follow-up text did not parse: ` and the `SpecError` text.
   Bind its return to a new name and end the group on `None`. Only then
   rebind `session`, so the closure's next charge reads the second session. A raise from it pools the group with `write raised`, as a
   first call's raise does (`:355-357`).
3. **The second session.** Run it back through the same handling from
   `spent` onward (`:359` to `:399`): the reset time, the error, the
   parse, `_validate` and the mint. A second parse failure calls
   `send_back` again, which pools it because the group was already sent
   back.
4. **The types.** `_prompt` gains one line telling the writer the type must
   be `bug` or `feature`. The line names no other type.
5. **Docstrings.** The module docstring and `write_follow_ups`'s say a draft
   that does not parse goes back to the writer once. `write_follow_ups`'s
   docstring is ten lines now by the `prose` gate's count, already at its
   limit (`saffron/follow_up.py:245-254`, `.saffron/gates/prose.py:67`,
   `:321`). Rewrite it rather than append.

## Out of scope

- A draft `_validate` refuses. It is not sent back, and pools as today.
  `_validate`'s `type` reason in run 47 is answered by the prompt line
  instead.
- A draft the finishing suite's gates fail. Its send-back is `SA-0327`.
- The writer's system prompt, `saffron/agents/prompts/spec-writer.md`,
  which `saffron draft` shares.
- `cli.py`'s `write` and its exception handler. `write` opens a new cell
  per call (`saffron/cli.py:1673-1701`). The handler pools each group no
  mint accepted, by its key (`:1723-1744`). Neither counts calls.
- A second send-back for one group, whatever its reason, or one for a
  raised call, a reset time or a session error.

## Notes for the agent

The send-back and the seam are new code, so every criterion declares a
witness and no mutant, and `witness` will report `skip` for each.

**For `SA-0327`.** The child calls `send_back(reason)` with its gate
failure as the reason. Its call site is inside `write_follow_ups`'s loop,
after `_validate` passes and before the candidate path is built and
`mint` runs (`saffron/follow_up.py:378-390` at base). A non-`None` return
re-enters the handling from `spent` onward, as the parse branch's does. A
group already sent back for its parse pools there with the gate reason.

**Charging.** Both sessions of a group that pools are charged to the origin
task, each as its own `WRITING` attempt through `_charge`. A second draft
that is minted is charged to its minted task, as every minted draft is
(`saffron/follow_up.py:398-399`). Both sessions add to `spent`. The
rebind after the `None` check also keeps `ty` reading the captured
`session` as `SpecWriterSession`. Assigning the return to `session`
directly made `ty` report eight errors against the prototype.

**Prompt order matters to a test double.** `_write_with_assigned_id` reads
the first `^id: ` line of the prompt (`tests/test_follow_up.py:1071-1094`).
The origin spec text and a refused draft both carry their own `id:` lines.
Keeping the first prompt first keeps the assigned id the first match.

**Three existing tests move.** Group 12's draft in `_eighteen_turns`,
`"not a spec at all\n"`, is now sent back (`tests/test_follow_up.py:458`).
Give `_eighteen_turns` a second refused draft right after it, one that is
not valid YAML. Then
`test_a_group_the_host_refuses_or_the_sub_cap_cannot_cover_goes_to_the_pool`
needs `cap_usd` of 4.5, not 4.25, for group 17 to stay accepted
(`tests/test_follow_up.py:520`). In that test the emitted lines become 19
(`:526`) and the write calls 16 (`:528`). The origin's writing attempts
become 12 (`:583`) and the batch spend 4.25 (`:585`). The reset call's
writing attempts become 13 (`:629`).
`test_an_accepted_follow_up_is_a_minted_task_with_its_text_and_its_writers_cost`
shares those turns and needs the same `cap_usd` of 4.5 (`:723`). The new
type line must not contain "before" or "after", which that test asserts
absent from the first prompt (`:786-787`).
In `test_a_follow_up_writers_attempt_records_the_model_its_session_names`
the wrong-id turn would become the parse group's second draft (`:849`).
Give the parse group a second unparsable turn with its own model, so the
wrong-id turn stays a first-draft id refusal. That model joins the pooled
list after the parse model (`:908-913`).

**The witnesses.** Build each on `_build`, `_stack`, `_q`, `_finding`,
`_candidate`, `_qualify_stub`, `_mint_stub` and `_write_stub`.
- Give each group its own finding claim, so two groups never compare
  equal. Compare groups with `==`. `write_follow_ups` rebuilds a group
  after the probe check, so `is` fails.
- Read each expected error from `intake.parse_spec` under `pytest.raises`,
  never from a copied string.
- Criterion 1's double returns a refused draft at cost 0.5 on each group's
  first call. On its second it returns a valid `_candidate` under the
  prompt's own assigned id. Assert each second prompt starts with its first
  prompt. In the rest, assert the error comes before the whole draft.
- Criterion 2 runs `write_follow_ups` twice on one `_build`. Use
  `_write_stub`, which numbers each session `s1`, `s2` and on
  (`tests/test_follow_up.py:317`). The first run
  has `cap_usd` 50 and eleven groups. Groups 1 to 4 each send a refused
  draft back. Their second turns are a draft that fails to parse, a type
  `test` draft, an error session and a `RuntimeError`. Groups 5 to 9 are first drafts
  `_validate` refuses for id, type, `depends_on`, budget and `touches`.
  Group 10 is sent back to a session with a reset time. Group 11 is never
  written. Assert the exact sequence of groups `write` saw. The second run
  sets `SPEC_WRITER_SESSION_USD` to 1.0 with `monkeypatch` and `cap_usd`
  to 1.5. Every session in it costs 0.25, `_write_stub`'s default for a
  text turn. Group 1 fails twice. Group 2's first session leaves 0.75, so
  it pools after one call. Priced before that session, 1.0 would remain
  and it would be sent back. Left out of `spent`, group 1's second session
  would also leave 1.0 there. Keep that cost at 0.25, or the version that
  drops it survives.
- Criterion 3 sets `SPEC_WRITER_SESSION_USD` to 1.0 and `cap_usd` to 1.25,
  with one group. Its first draft has no frontmatter block and its second
  is not valid YAML, each at 0.25. So 1.0 is left at the send-back. Let
  `write` and `emit` append to one list. Assert the kinds after the first
  emitted line run `write`, `emit`, `write`, `emit`.
- Criterion 4 reads the first prompt of one group written with
  `_write_with_assigned_id`. Find the six type names with a whole-word
  pattern on each line. Some line's set of names is exactly `bug` and
  `feature`.

**What the witnesses leave.** One first-draft refusal is not driven, a
mutant naming the group's own probe. A second draft is refused by
`_validate` only for its type. The rest reach the same `_validate` call as
the driven ones. The parse refusals not driven are "not a mapping", a reserved
key, both criteria forms and `DisclosedMutantError`. Each is a `SpecError`
caught by the same clause. No witness can see that the send-back is one
closure rather than inline code. Criterion 3's shape is held by review and
by `SA-0327`, which calls it.

A prototype of this change passed every test in `tests/test_follow_up.py`,
with the two edits above. Each witness failed with the source at base.
Each wrong version above was applied and run, and its criterion's witness
killed it.
