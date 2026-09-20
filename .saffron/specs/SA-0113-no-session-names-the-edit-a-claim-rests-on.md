---
id: SA-0113
title: No session names the edit an acceptance claim rests on, so nothing can put that claim's witness under one
type: feature
priority: 1
depends_on: []
touches:
  - saffron/phases/review.py
  - saffron/cell/session.py
  - saffron/agents/prompts/criterion-probe.md
  - saffron/agents/prompts/turns/criterion-probe.md
  - tests/test_review.py
  - tests/test_session.py
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
  - saffron/probe.py
  - saffron/intake.py
  - saffron/ledger.py
  - saffron/task.py
  - saffron/batch.py
  - saffron/cli.py
  - saffron/events.py
  - saffron/report/**
  - saffron/gates/**
  - saffron/repos/**
  - saffron/agents/findings.py
  - saffron/agents/context.py
  - saffron/agents/artifacts.py
  - saffron/cell/worktree.py
  - saffron/cell/runtime.py
  - saffron/cell/proxy.py
  - saffron/phases/implement.py
  - saffron/phases/rebut.py
  - saffron/phases/package.py
  - saffron/agents/prompts/implement.md
  - saffron/agents/prompts/rebut-verdict.md
  - saffron/agents/prompts/review-adequacy.md
  - saffron/agents/prompts/review-contract.md
  - saffron/agents/prompts/review-correctness.md
  - saffron/agents/prompts/turns/extraction.md
  - saffron/agents/prompts/turns/implement.md
  - saffron/agents/prompts/turns/notes.md
  - saffron/agents/prompts/turns/plan.md
  - saffron/agents/prompts/turns/rebut-extract.md
  - saffron/agents/prompts/turns/rebut.md
  - saffron/agents/prompts/turns/review.md
  - saffron/agents/prompts/turns/salvage.md
  - saffron/agents/prompts/turns/verdict.md
  - tests/fixtures/**
  - tests/test_context.py
  - tests/test_corpus.py
  - tests/test_events.py
  - tests/test_queued_specs.py
  - tests/test_witness_gate.py
budget_usd: 26
max_attempts: 3
max_turns: 160
acceptance:
  - claim: >-
      REVIEW buys one fresh session for each entry in the spec's acceptance
      list, inside the critic cell, after every lens has run. Each session is
      given one entry's claim and no other entry's, and no witness node id
      reaches any of them through the prompt the host builds. Each holds the
      read-only tool set a lens
      holds, and the per-session ceiling the same review gave its lenses. Every
      one of these sessions is charged to the task, so the cell's spend carries
      their cost.
    witness: tests/test_session.py::test_each_claim_is_asked_of_its_own_session_that_is_never_shown_a_witness
  - claim: >-
      The task directory carries `criterion-probes.json`, one entry per
      criterion in the spec's own order, pairing that criterion's witness and
      claim with the edit its session named as `file`, `find` and `replace`,
      and with the reason that session gave, word for word. A session that
      named no edit keeps its entry, with no edit and its reason. REVIEW emits
      one line after the last session, counting the named and the unnamed over
      that same record. A spec that declares no criterion writes no record and
      emits no such line, driven over the same stubbed runtime.
    witness: tests/test_session.py::test_the_record_pairs_each_claim_with_the_edit_its_own_session_named
  - claim: >-
      A naming session that fails, and one whose output the schema refuses,
      each leave an entry naming what went wrong and carrying no edit. Every
      later criterion is asked all the same, and a session is never re-prompted
      to repair its output.
    witness: tests/test_review.py::test_a_session_that_answers_nothing_usable_is_recorded_and_the_next_is_still_asked
---

## Context

Backlog item **b-2750d5** is
`docs/backlog/b-2750d5-no-cell-mutates-the-line-that-satisfies-each-criterion.md`,
tier 1, and first under the run 8 paragraph of `docs/backlog/PRIORITY.md:111`.
It was filed on 2026-09-19 out of the spec loop's run 8. After every cell of
that stack, the loop's delegate mutated by hand the line each acceptance
criterion rests on. It then ran that criterion's witness. The surviving edit was
a witness hole in all five pull requests, and five review commits fixed them.

Every sentence below about current code was read at `ca55c57e` on 2026-09-20.

**Item 117's half of this shipped and this half did not**. `SA-0109` gave the
host the adequacy lens's own vacuity probe. `_probe_adequacy`
(`saffron/cell/session.py:1255`) applies every anchored adequacy finding's edit
once in a Gate-only cell. `saffron.probe.check_probe` (`saffron/probe.py:148`)
then decides the finding from the suite's answer. That path reads findings and
never criteria (`saffron/cell/session.py:1281`). A claim no lens wrote about is
probed by nothing.

**The only edit a criterion carries is one the spec author declared**.
`witness_gate` keeps the criteria whose `mutant` is set
(`saffron/gates/core/witness.py:130`). It reports `skip` for a spec that
declares none (`:131-134`). `DESIGN.md` §5.4.1 names the limit that leaves. A
spec whose change is new code declares a witness and no mutant
(`DESIGN.md:950-952`). The text a mutant would pin does not exist while such a
spec is written. This spec is one of them, and so were four of the five rows in
item 117's own table.

**The author of that edit does not have to be the spec author**.
`DESIGN.md:972` gives the reason the spec declares it rather than an agent: "A
cell is untrusted, and a mutant it authored is a mutant chosen to be killed."
That reason is about the implementer. The implementer wrote the code and the
tests, and knows which edit its own tests would miss. A session that wrote
neither, shown one claim and no witness, is a different author with nothing to
protect.

**REVIEW already drives fresh sessions, and holds a cell that can drive one
more**. `run_review` (`saffron/phases/review.py:278`) loops over `LENSES`
(`:39`) and calls `run_lens` (`:190`) once per lens. Every lens is a fresh
session the host invokes itself. Each reads the diff the critic cell exported
(`saffron/cell/session.py:2303`), with the read-only tools `REVIEW_TOOLS` names
(`saffron/phases/review.py:35`). `run_lens` builds its options through
`implement.agent_options` (`saffron/phases/implement.py:94`) and catches
`AgentFailed`. Output the schema refuses becomes a `LensReview` carrying an
error (`saffron/phases/review.py:224-233`). All of it runs inside one
`critic_cell` (`saffron/cell/session.py:2286`). That cell is torn down before
`_probe_adequacy` enters a cell of its own.

**Nothing pairs a fresh session with a single claim**. The claims reach a lens
as a block appended to the spec body, through `context.criteria_section`
(`saffron/agents/context.py:120`), called at `saffron/cell/session.py:2316`. The
witness ids reach the implementer through `context.witnesses_block`
(`saffron/agents/context.py:89`). No caller asks one session about one claim,
and no caller withholds the witness from a critic.

## Problem

A criterion's claim and the edit that falsifies it are one thought. One reader
in the whole task ever has it: the person writing the spec, before the code
exists. So the thought goes unrecorded, and a person probing by hand finds the
hole after the pull request opens.

Build the half of item b-2750d5 that authors the edit. Applying it and running
the criterion's witness is the child spec named under "Out of scope". This spec
stops at the record.

1. **Where it runs**. Inside the critic cell, after `run_review` returns and
   before the `with` block at `saffron/cell/session.py:2286` exits. These
   sessions read files and run nothing. So `SA-0087`'s rule about executing
   model-authored code in the critic cell does not reach them. The Gate-only
   cell belongs to the child, which has tests to run. A lens that errored
   changes none of this. `_probe_adequacy` sits on the same path today
   (`saffron/cell/session.py:2352`), ahead of the `review_state` call that
   reads an errored lens (`:2394`). A patch the critic cell refuses is the
   other way round. That raises before any session is bought
   (`saffron/cell/session.py:2333`), so no record is written at all.

2. **What it asks**. One fresh session per entry in `spec.acceptance`
   (`saffron/cell/session.py:263`), in the order the spec declares them. Each
   session gets the diff the lenses judged, the vocabulary and standing
   instructions a lens gets, and exactly one claim. Each is asked for the
   smallest edit to the source that would make that claim false. The edit has
   to leave the code able to run. Every entry is asked about, a `preserves`
   entry included. A vacuous witness is no less likely over a claim about
   preserved behaviour. An exemption there would be a branch with nothing
   measuring it.

3. **What is withheld, and why it is the point**. The witness node id never
   reaches the session, and neither does any other criterion's claim. An author
   shown the test can pick the edit that test would miss. That is the shape of
   a vacuity probe, and the opposite of what this answers. The verdict the
   child spec reads is worth something only over an edit chosen against the
   claim alone. This is `DESIGN.md` §5.4.1's own rule about disclosure, turned
   around. A mutant is evidence about a witness only where its author could not
   see the witness.

   **The withholding is a prompt-level control, and item 80 is why it is named
   as one**. The critic cell holds the tree at `base_sha` with the patch
   applied. The spec file is on disk there, and a read-only tool reads it.
   `forbidden` says what a cell cannot change, never what it cannot read.
   Backlog item 80 is open over that for a criterion's own mutant, and the same
   limit lands here. So the claim above is about the prompt the host builds,
   which is what a test can observe. The prompt itself tells the session it
   holds everything it needs. Item 80's fix covers this one as well.

4. **What comes back**. One `<output>` block per session, holding an object
   with an edit and a reason. The edit is the three fields `Mutant` declares
   (`saffron/intake.py:71-89`), validated through that model. `Finding.probe`
   already uses that model for a lens-authored edit
   (`saffron/agents/findings.py:41`). The reason is the session's own account
   of why the edit falsifies the claim. A session that finds no such edit
   answers with no edit and a reason. That is the honest answer over a claim
   whose subject the diff never touched. The host validates and stores. It
   compares nothing against the tree, and it applies nothing.

5. **What it records**. `criterion-probes.json` in the task directory, written
   the way `probes.json` is written (`saffron/cell/session.py:2366`). One entry
   per criterion, in the spec's own order. An entry carries the criterion's
   witness and claim, the edit or no edit, and the reason word for word. It
   also carries what the session cost, and the error where there was one.
   REVIEW then emits one line counting the named and the unnamed. Derive that
   line from those entries, and never count a second way. `review.describe_probes`
   (`saffron/phases/review.py:402`) is the precedent for a line counted over
   the record it summarises.

6. **What it costs**. Each session is paid for out of the budget the lenses
   draw on, under the ceiling those lenses got. `critic_budget`
   (`saffron/cell/session.py:138`) computes that ceiling once, at
   `saffron/cell/session.py:2328`, and `run_review` hands the one value to
   every lens (`saffron/phases/review.py:289`, `:315`). Give these sessions the
   same value, for the same reason: a ceiling per session is what the review
   already runs on. Give them `spec.max_turns` as well, which is what the
   lenses get (`saffron/cell/session.py:2327`). The cost of all of them is
   added to the cell's spend beside the lenses'
   (`saffron/cell/session.py:2378`).

A spec that declares no acceptance entry buys no session, writes no record and
emits no line. Two things ride on that. The watch golden fixture pins REVIEW's
lines for a driven run (`tests/fixtures/watch-golden.txt:25-27`), and the spec
that run drives declares no criteria (`tests/test_session.py:146-154`). The
fixture
and `tests/test_events.py` are both `forbidden` here. So the golden staying
green is a constraint on the design, rather than a file to edit.

## Out of scope

**Applying the edit, and the verdict**. The child spec takes each entry of
`criterion-probes.json` and applies the edit in a Gate-only cell. It runs that
criterion's witness over the edit, and turns a surviving edit into a blocker
finding routed to REBUT. It is the rest of item b-2750d5, and it depends on
this spec. None of `saffron/gates/**`, `saffron/probe.py` or
`saffron/phases/rebut.py` is writable here. Write no code for the child, and
leave no seam claiming to be ready for it. The `dead` gate reports a symbol no
production caller reaches.

**Anything downstream of a finding**. No finding is filed by this step. So
`findings.json`, the ledger's findings rows, the queue line's concern count,
REBUT's blocker list and the pull-request body all keep today's behaviour.
`saffron/phases/rebut.py`, `saffron/ledger.py` and `saffron/report/**` are
`forbidden`.

**The vocabulary and the design record**. This spec coins *criterion probe* for
the edit a fresh session names against the source one claim rests on. Backlog
item b-0c1d69 owns three things: the entry in `ontology/factory.ttl`, the
`CONTEXT.md` render of it, and the `DESIGN.md` §5.4.1 paragraph at `:972`. That
paragraph reads as a refusal of agent-authored edits. Both files are
`protected`, and `CONTEXT.md` is generated, so a cell cannot land either half.
Use the term in code and comments. Do not edit a glossary.

**Narrowing which criteria are asked**. Every entry is asked about, including
one whose `mutant` the spec declared and which `witness_gate` already ran. Two
edits over one claim are two answers, and the cheaper rule has no branch in it.
Add no cap on the number of sessions either. Say so in your notes if you think
one is needed.

**Repairing a session's output**. `run_lens` re-prompts one lens once over
output the schema refuses (`saffron/phases/review.py:226-265`). These sessions
do not. A lens costs a whole remit, where a naming session costs one claim.
Criterion 3 pins the difference.

**The adequacy probe path**. `_probe_adequacy` and everything it calls keep the
behaviour `SA-0109` gave them. `saffron/probe.py` is `forbidden`, `probes.json`
keeps its name and its shape, and the two records stay separate files.

## Notes for the agent

**This change is new code, so no criterion declares a mutant** (§5.4.1). The
`witness` gate will report `skip`, with a summary saying the spec declares
none. Nothing at base determines the spelling of a function, a record key, or a
line of the prompt text this change adds. A mutant here would pin text this
spec had to dictate. Every name below is a description of a job, rather than a
spelling to copy.

**Each witness must fail with your source reverted**. `revert` judges every
test you add, whether or not a criterion names it. Criterion 2's last sentence
is the one to read twice. A test that only asserts absence passes with the
source reverted. So that witness drives the stubbed runtime twice. The first
run declares two criteria and asserts the record and the line are there. The
second declares none and asserts no turn past the lenses, no file and no line.
Write the presence half first.

**Name the wrong implementation each witness must kill**. Criterion 1 has four
sentences, and its witness asserts all four from one drive. Five
implementations have to die under it. One asks a single session about the whole
acceptance list. One hands a session the witness ids through the block
`context.witnesses_block` builds (`saffron/agents/context.py:89`). One asks
before the lenses rather than after. One gives these sessions the implementer's
tools, or a ceiling of its own. One leaves their cost out of the spend.

Criterion 2 kills three. One drops the entry for a session that named no edit.
One pairs edits with criteria by position after such a drop. So the two claims
and the two edits in that witness have to be distinguishable from each other.
One writes an empty record over a spec with no criteria, or emits a line
reading zero.

Criterion 3 kills three. One lets `AgentFailed` out of the loop. One stops at
the first failure. One re-prompts a session, the way `run_lens` re-prompts a
lens.

**The prompt is two files, and the tree is scanned**. Write a system prompt
file beside the lens prompts, and a turn prompt under `prompts/turns/`. That is
how every other phase is built (`saffron/agents/context.py:156`,
`saffron/phases/review.py:51`). Give the turn file the `{extraction}` slot, so
the output-block rules stay in one copy. Build the system prompt through
`context.build_system_prompt` with the phase REVIEW, which is the vocabulary
set a lens gets (`saffron/agents/context.py:28-32`). That function raises over
a template with no `{spec}` slot (`:190-191`). The value you pass for `{spec}`
is the one claim. Pass no spec body: the body is prompt text naming witnesses
and files, and criterion 1 is that no witness reaches these sessions. Both new
files sit inside `.saffron/gates/prose.py`'s `INCLUDED_DIRS` (`:36-44`). So the
`prose` gate reads them as living prose, and the `terms` gate reads them for
avoided words.

**Your own injected glossary is stale here, as `SA-0109`'s was**. `CONTEXT.md`
§4 defines *Mutant* as declared by a criterion and never chosen by the agent
(`CONTEXT.md:335-343`). It defines *Vacuity probe* as named by a lens and
applied by the corpus harness (`:345-352`). A criterion probe is neither.
Backlog item b-0c1d69 owns the entry that will say so. Write the prompt so the
session it addresses is told what it is naming, in that prompt's own words. Do
not hedge the design against a glossary line you cannot edit.

**The prompt asks for an edit against the claim, never against a test**. Say in
it that the reader holds no test runner and sees no test name. Say that the
edit must break the claim rather than evade a suite, and must leave the program
able to start. Say that `find` has to appear in its file exactly once. That is
the rule `source_mutated` enforces, and the adequacy lens prompt states it
already (`saffron/agents/prompts/review-adequacy.md:116-120`). Say that naming
no edit is a real answer. An invented edit over an untouched subject costs the
child spec a whole suite run for nothing. Say that the prompt holds everything
the reader needs, and that the diff and the source under `/work` are what it
reads. Do not name the spec directory in the prompt. Telling a session where
the tests are named is the disclosure this step exists to avoid. Item 80 is the
standing record of why a written rule is not a boundary.

**Where the loop lives**. `saffron/phases/review.py` holds the fresh-session
machinery and the record-shaped helpers. `saffron/cell/session.py` holds the
call site, the write and the line. That split is the one `SA-0109` left:
`review.adequacy_probes`, `review.probe_key` and `review.describe_probes`
(`saffron/phases/review.py:359-413`) are pure, and `_probe_adequacy`
(`saffron/cell/session.py:1255`) holds the cell. `session.py` is 2618 lines and
`review.py` is 436. Put everything that does not need the call site in
`review.py`.

**`review.py` cannot import `session.py`**. `session.py` imports `review`
(`saffron/cell/session.py:48`). So the ceiling reaches the loop as a value the
call site passes, the way `run_review` takes `budget_usd` today
(`saffron/phases/review.py:289`). Write no copy of `critic_budget`'s
subtraction (`saffron/cell/session.py:138-140`) in `review.py`.

**Every field you record needs a reader in scanned code**. The `dead` gate
reports a field no scanned root loads by name, which cost `SA-0109` a review
round over `probe_verdict`. Build the record entry where the fields are read,
and keep the entry a plain structure the JSON write consumes.

**The existing session witnesses that declare criteria will change**. Ten call
sites in `tests/test_session.py` pass `acceptance=`, and the ones reaching
REVIEW now buy one session per criterion. `_drive`'s scripted turns run out
after the turns a test names. Every later turn takes the fallback
`{"findings": []}` (`tests/test_session.py:1051`), which this schema refuses.
So those tests record an error entry per criterion, which is the expected state
rather than a defect. Leave `_drive`'s fallback alone: criterion 3 needs an
answer the schema refuses to stay easy to produce. Script the lens turns and
the naming turns for any test asserting on turn counts or prompts.
`test_the_review_lens_prompt_carries_the_claim_for_a_witnessed_spec`
(`tests/test_session.py:5654`) asserts every prompt past the first carries the
claim. A naming prompt carries it too, so that one stands.

**Two files of tests, and which witness goes where**. Criterion 3 is a unit
witness in `tests/test_review.py`, driving the loop directly with the `_agent`
double (`tests/test_review.py:50-65`). That double scripts a per-session answer
and records the prompt it was given. Criteria 1 and 2 drive a whole task
through `_drive` (`tests/test_session.py:966`). They assert on task-level
output: the system prompts, the turn options, the task directory, the emitted
lines and `outcome.spent_usd`. Criterion 2 drives it twice, so put the scripted
turns and the two criteria behind one helper both witnesses call. Each witness
is a plain `def`, never parametrised, because `criteria` matches a bare node id
by exact string.

**Import inside the test body, not at module scope**, for any name this change
adds. `revert` re-runs your new tests with the source reverted. A module-scope
import of a new name makes that run a collection error, which `revert` reads as
`skip`.

**This step spends before REBUT's budget check** at
`saffron/cell/session.py:2404`. A task holding a blocker and a thin remainder
can now end `EXHAUSTED` where it would rebut today. That is the existing rule
rather than a new one, and this spec's ceilings account for it. Do not add a
second budget rule to protect REBUT.

**The tier is elevated and `size` blocks**. `saffron/cell/**` is in
`.saffron/policy.yaml:36`'s `elevate_on`, so this diff auto-elevates. The
`feature` ceiling of 600 changed lines is then blocking
(`saffron/gates/core/size.py:25`). The estimate for this change is about 480
lines. It is 58 of prompt text, 150 in `review.py`, 35 in `session.py`, 65 in
`tests/test_review.py`, and 175 in `tests/test_session.py`. The last figure
includes the repair of the existing tests named above. `SA-0109` is the
comparable cell, at 584 lines over seven criteria and six new witnesses. This
one has three criteria and three new witnesses. Keep the drive helper shared,
and do not go looking for more to do.

**The `prose` gate counts comment runs and docstrings per file**. It blocks,
with the base subtracted. Keep every comment to one or two lines and every
docstring under ten, the two new prompt files included.

**Rename no existing test**. `census` compares collected names between base and
head, and reads a rename as a removal.

Commit after each coherent step. Uncommitted work dies with the cell.
