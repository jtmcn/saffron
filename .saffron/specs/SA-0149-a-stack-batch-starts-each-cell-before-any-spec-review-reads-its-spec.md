---
id: SA-0149
title: A stack batch starts each cell before any spec review reads its spec, so a blocker a delegate would catch reaches the cell
type: feature
priority: 1
depends_on: [SA-0148]
touches:
  - saffron/spec_review.py
  - saffron/batch.py
  - tests/test_spec_review.py
  - tests/test_batch.py
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
  - saffron/task.py
  - saffron/cli.py
  - saffron/scheduler.py
  - saffron/intake.py
  - saffron/ledger.py
  - saffron/events.py
  - saffron/record/**
  - saffron/repos/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/agents/**
  - tests/test_task.py
  - tests/test_cli.py
  - tests/test_scheduler.py
  - tests/test_ledger.py
  - tests/test_review.py
budget_usd: 26
max_attempts: 3
max_turns: 160
pending_symbols:
  - saffron/spec_review.py::fixes
acceptance:
  - claim: >-
      `read_spec_review` reads the last fenced `json` block of a
      `SpecReviewSession`'s text and carries its cost and `resets_at`. It
      keeps each finding's `fixes`.
      `spec_review_route` routes a read with `resets_at` set `wait`, before
      any other check. It routes the read `error` when the session carries
      an error, when the
      text holds no `json` block, or when that block is not an object whose
      `findings` is a list of objects. It routes `error` too when a finding
      has no string `claim`, a `severity` other than `blocker`, `concern`
      or `note`, or a `fixes` other than an entry of `SPEC_REVIEW_TAGS`,
      null or absent. `SPEC_REVIEW_TAGS` is the tuple `scope`, `build`,
      `witness`, and the read looks it up when called. Otherwise one `blocker` or more routes `escalate`, whatever
      its `fixes`, and none routes `run`. A `concern` whose `fixes` is
      `witness` routes `run` and keeps that `fixes`. Other keys are
      ignored. The witness drives each member, and a tag added to
      `SPEC_REVIEW_TAGS`.
    witness: tests/test_spec_review.py::test_a_spec_review_routes_on_the_severities_in_its_last_json_block
  - claim: >-
      Given `review`, `run_stack_batch` calls it for a spec after the checks
      before that spec's task and before its runner call. It passes the spec
      and the last layer, which is the predecessor the runner would get, or
      `None`. A spec routed `escalate` or `error` never reaches the runner
      and adds no layer. It emits one line, its id padded to ten, then
      ` escalated  ` and its count of blockers, or ` unreviewed  ` and the
      read's error. An `escalate` counts as no abort. Each spec that reaches
      either through a `depends_on` entry at any position, directly or
      through a refused spec, is refused with a line naming it and is never
      reviewed. An entry outside the order holds nothing back. A spec routed
      `run` runs on the last layer.
    witness: tests/test_batch.py::test_a_stack_batch_runs_a_spec_only_when_its_own_review_routes_it_to_run
  - claim: >-
      A spec that `run_stack_batch` runs a second time, after it returns
      `RATE_LIMITED`, is reviewed once. Both runner calls get the same
      predecessor. A spec that depends on it is reviewed on it and runs.
    witness: tests/test_batch.py::test_a_spec_run_again_after_a_rate_limit_keeps_its_first_review
  - claim: >-
      A review that raises counts as an abort, as a runner that raises does,
      and so does a review routed `error`. Two in a row end the batch
      `INFRASTRUCTURE` before the third spec's runner call. The witness
      drives two raises, and a session error then text with no `json` block.
      Each reviews only the first two specs. When readiness fails, or the
      budget stops the first spec, no review is called.
    witness: tests/test_batch.py::test_a_spec_review_that_raises_or_errors_counts_toward_the_breaker
  - claim: >-
      A review routed `wait` leaves the runner wrapper as a
      `batch.SpecReviewWait` raised with the review's `resets_at`. `_drive`
      catches it before its general handler and gives that reset time to
      `SA-0148`'s rate-limit wait. It counts no abort and attaches no run.
      The batch sleeps once and offers the spec again, next, on the same
      predecessor, after `--until`, the budget and the breaker. It reviews
      the spec again, and runs it once its review routes `run`. A wait that
      ends at or past `until` stops `UNTIL` at once, with no sleep. The
      witness drives a wait that ends before `until` and one that does
      not.
    witness: tests/test_batch.py::test_a_rate_limited_spec_review_waits_and_reviews_again
---

## Context

Backlog item **b-792ab2**, step 6 of its Done. It cites `DESIGN.md` §4.2,
§4.2.1 and §5.5. ADR 7
(`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md:54-61`)
decides that spec review runs inside a stack batch, before each spec's
first cell. Section 3 of
`docs/superpowers/specs/2026-09-23-stack-batch-design.md` is the design. It
seeds each review at the tree the spec would be cut from (`docs/superpowers/specs/2026-09-23-stack-batch-design.md:160-162`).
It reviews queued specs one at a time, each right before its own cell
(`docs/superpowers/specs/2026-09-23-stack-batch-design.md:170-177`).

**This spec is the first of six for step 6.** It builds the read of a
findings block and the tags blockers route by. It also builds the routing
inside `run_stack_batch`, through an injected `review` callable. `SA-0155`
records each review as facts. `SA-0168` and `SA-0169` prepare the task
and the cell. `SA-0175` builds the session and core's prompt for it.
`SA-0156` builds the production `review`, one host-invoked session in a
critic cell seeded at the tree this spec hands it, and passes it from
`saffron batch --stack`.

**Each review runs right before its own spec's cell.** Reviews run one at
a time, as the design says. Reviews at batch start, K at once, cannot
run on the cell runtime at the tree base. Every cell shares the network
`saffron-cells` and one proxy. `start_proxy` removes the proxy before it starts one
(`saffron/cell/proxy.py:53`), and `cell_up` removes the network before it
creates it (`saffron/cell/session.py:909`). `cell_down` stops the proxy
and removes the network (`:1012-1013`). So a review cell beside a task cell
loses its network. Run at the spec's turn, the review reads the tree the
spec's cell is cut from, the current last layer.

**What the tree base holds.** This spec's tree base is `SA-0148`'s head.
The chain runs through `SA-0142` to `SA-0145`, and `SA-0135` and
`SA-0136` below them. This spec consumes three things `SA-0143` builds.

- `run_stack_batch` in `saffron/batch.py`. It runs a stack order once and
  hands each task the last task before it that returned
  `READY_FOR_REVIEW`. That task is a **layer**, and the last one is the
  next task's **predecessor**.
- Its refusal. A spec that reaches, through a `depends_on` entry at any
  position, a spec that missed `READY_FOR_REVIEW` is refused. It never
  reaches the runner. Its line is its id padded to ten, then ` refused  `,
  then a reason naming each spec it reaches that missed. A `Refused` and a
  raise count as a miss. An entry outside the order never counts.
- `_candidate`'s `depends_on` keyword in `tests/test_batch.py`.

Criteria 3 and 5 consume what `SA-0148` builds: `run_stack_batch`'s
`sleep` keyword, `CellOutcome.resets_at` and its wait. After a
`RATE_LIMITED` task, `SA-0148` sleeps once and offers the same spec again,
on the same predecessor, and leaves the breaker's count as it was. This spec consumes nothing else of `SA-0146`, `SA-0147` or
`SA-0148`. Every line number below was read at `2bb34a8d`. The chain edits
`batch.py` and `tests/test_batch.py`, so read their lines there by symbol.

**How a spec review runs today.** A delegate dispatches this repo's
spec reviewer by hand. `CONTEXT.md` calls it advisory, with nothing in
code to enforce it (`CONTEXT.md:462-466`). That agent file is the hand
path's own, and core never reads it (`docs/superpowers/specs/2026-09-23-stack-batch-design.md:164-168`).

**Whose block and tags these are.** ADR 7 makes the tags blockers route
by core's (`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md:63-64`). So this spec defines them as
`SPEC_REVIEW_TAGS` in `saffron/spec_review.py`, and nothing here derives
them from a repo file. A spec review returns its tags through a separate
extraction turn, which keeps principle 18 (`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md:91-94`). That turn is
`SA-0175`'s. It is meant to fill `SpecReviewSession.text` with one
fenced `json` block, `{"findings": [...]}`, whose body parses as JSON, or
leave `text` empty. This spec takes no such promise on trust. Any other
`text` routes `error`, as criterion 1 says. Each
finding holds `severity`, `claim`, `criterion`, `file`, `line` and
`fixes`. So the read here parses only that block, never the review
turn's prose. Its witnesses build `text` as fixtures.

**How a batch runs a spec today.** `_drive` checks readiness before any
task (`saffron/batch.py:165-166`). Before each task it checks `--until`,
the budget and the breaker (`:192-202`). It then emits the spec's
`starting` line (`:207`) and calls the runner (`:212`). A raise counts as
an abort (`:213-230`), and so does a `GATE_ERROR` (`:53`, `:244-245`). Two
in a row fire the breaker (`:57`).

**An unrun review never reads as clean.** REVIEW keeps the same rule. A
lens that fails returns an `error` and no findings (`saffron/phases/review.py:237-241`).
`review_state` stops at `REVIEWING` when any lens errored (`:611-616`).

## Problem

Build four things.

1. **The read.** A new module, `saffron/spec_review.py`, holds these.
   - `SpecReviewSession`, a frozen dataclass of `text: str`,
     `cost_usd: float`, `error: str | None` and
     `resets_at: int | None = None`. It is what a `review` callable
     returns. A session that met the account's rate limit carries its
     reset time there.
   - `SpecReview`, a frozen dataclass of `findings`, `cost_usd`, `error:
     str | None` and `resets_at`. Each finding carries `severity`, `claim`,
     `fixes`, `criterion`, `file` and `line`.
   - `SPEC_REVIEW_TAGS`, the tuple `("scope", "build", "witness")`. The
     read checks each `fixes` against it at call time. `SA-0175` fills
     core's prompt from it, and `SA-0164` routes on it.
   - `read_spec_review(session) -> SpecReview`, as criterion 1 says. It
     checks each finding's `fixes` by name on the finding it builds, so
     `saffron/` reads the field. `SA-0164` routes on it.
   - `spec_review_route(review)`, which returns `"wait"`, `"run"`,
     `"escalate"` or `"error"`, as criterion 1 says.
2. **One keyword on `run_stack_batch`.** `review`, a callable taking a
   `Candidate` and the last layer's `Candidate` or `None`, and returning
   a `SpecReviewSession`. It defaults to `None`, and with `None` nothing
   changes.
3. **The routing**, as criteria 2 to 4 say. The review runs where the
   runner would, after `_drive`'s checks and its `starting` line. So a spec
   its review withholds still meets `--until`, the budget and the breaker
   first, and still logs `starting`. A spec whose review routes `escalate`
   or `error` does not run, and neither does any spec that reaches it. A
   review that raises or routes `error` is an abort. A review routed
   `wait` goes through `SA-0148`'s wait with the review's `resets_at`, as
   a `RATE_LIMITED` task's does, and its spec is reviewed again.
4. **The wait signal.** Add `SpecReviewWait`, an exception in
   `saffron/batch.py` that carries `resets_at: int | None`. The wrapper
   raises it for a `wait` route. `_drive` catches it in its own `except`
   clause, before the general one, and hands `resets_at` to the wait
   `SA-0148` built for a `RATE_LIMITED` outcome. That wait then takes the
   spec id back out of the started set, as it does for a task. Build no
   `CellOutcome` for it. A review wait has no run, and
   `attach_run_to_batch` raises on a run that does not exist
   (`saffron/ledger.py:855-859`). That raise ends the night
   `INFRASTRUCTURE`.

## Out of scope

- **Concurrent reviews.** Reviews beside a task's cell need network and
  proxy names per cell, in `saffron/cell/**`, and a later spec. The
  operator files that backlog item.
- **Revision rounds.** A `build` or `witness` blocker gets up to three
  rounds by an agent that revises the spec. That is `SA-0164`'s, because
  it needs the spec writer. Here every blocker routes `escalate`. The read
  already keeps and checks each `fixes`. So `SA-0164` adds a `"revise"`
  route in `spec_review_route` and leaves `SpecReview` and the read as
  they are.
- **A concern that a witness cannot be measured.** The design routes
  it as `witness` (`docs/superpowers/specs/2026-09-23-stack-batch-design.md:198-199`). The review marks one itself: a
  `concern` whose `fixes` is `witness`, as core's prompt asks
  (`SA-0175`). No word in its claim decides it. The read keeps that
  `fixes`. With no revision here, it routes `run`, as any concern does.
  `SA-0164` at the tree base routes it `run` and keys its revision on a
  word in the claim. `SA-0164` must be revised to route on this tag.
- **The session, its facts and its caller.** The session and its
  extraction turn are `SA-0175`'s, the facts `SA-0155`'s, and the caller
  `SA-0156`'s. Nothing
  in `saffron/` passes `review` until then, so a production stack batch
  reviews nothing yet.
- **Filling `resets_at`.** `SA-0175`'s session sets it from a
  session that met the account's rate limit, and returns at once. It
  never waits inside the callable. The loop's wait here is the only one,
  and the wrapper never sleeps or reviews again inside itself.
- **Money.** A review's cost reaches no ledger row, so the batch's budget
  check does not count it. The start-of-batch reserve for spec work is a
  later step.
- **Follow-ups, the end review and the queue view.** They are other steps
  of b-792ab2.
- **The vocabulary.** `CONTEXT.md` calls a spec review advisory, and has
  no entry for an escalation. Backlog item b-466005 files both by hand.

## Notes for the agent

**Every criterion is new code.** No text at the tree base reads a findings
block or calls a review. So each criterion declares a witness and no
mutant, and `witness` reports `skip` for each.

**Import every new name inside the test body.** `saffron/spec_review.py`
does not exist at the tree base. A module-scope import of it fails
collection with the source reverted, and `revert` reads that as `skip`.

**One way to route.** Review inside the runner wrapper `SA-0143` builds,
on the predecessor it is about to hand the runner. Keep each spec's route
by spec id, and read it again on a second call for that spec. For
`escalate`, emit the line and return a `Refused` (`saffron/task.py`, from
`SA-0135`). `SA-0143` counts a `Refused` as a miss, and `_drive` counts it
as no abort. For `error`, emit the line and then raise, so `_drive` counts
the abort and `SA-0143` counts the miss. `_drive` then adds its own
`raised` line. Let a raise from `review` itself leave the wrapper.

**Name the severities once.** Import `Severity` from
`saffron.agents.findings` (`saffron/agents/findings.py:23`) and type each
finding's `severity` with it. A second spelling of that `Literal` fails
`tests/test_closed_sets_are_spelled_once.py`.

**Keep the error route's line single.** `_drive` emits
`raised <type>: <message>` for any raise (`saffron/batch.py:230`). So the
exception the error route raises carries a message that does not repeat
the ` unreviewed  ` line.

**`tests/` is not scanned by `dead`** (`.saffron/gates/dead.py:4-5`). So
every new name in `saffron/spec_review.py` needs a reader in `saffron/`.
`batch.py` reading each one is enough. `fixes` is read only by the check
in the read until `SA-0164` routes on it, so it is a `pending_symbols`
entry too.

**Criterion 1's witness** builds each session with `json.dumps` inside a
fenced `json` block, cost 0.5, and asserts the route and the cost. Each
finding holds `criterion`, `file`, `line` and `claim` unless its row says
otherwise.

| session | route |
|---|---|
| `{"findings": []}` | `run` |
| one `note` | `run` |
| one `concern` with `fixes: "witness"`, whose read keeps `witness` | `run` |
| one `blocker` for each of `scope`, `build`, `witness` | `escalate` |
| one `blocker` with `fixes: null`, and one with no `fixes` | `escalate` |
| one `note` with an extra `evidence` key | `run` |
| `error` set, text a clean block | `error` |
| text with no fence | `error` |
| a clean block fenced as `text` | `error` |
| a `json` fence around text that is not JSON | `error` |
| a top-level list holding a `blocker` | `error` |
| an object with no `findings` key | `error` |
| `findings` a string | `error` |
| severity `Blocker`, and severity `critical` | `error` |
| a `blocker` with `fixes: "rewrite"` | `error` |
| a `concern` with `fixes: "rewrite"` | `error` |
| `findings` a list holding a string | `error` |
| a `note` with no `claim` | `error` |
| a block with a `blocker`, then a clean block | `run` |
| a clean block, then a block with a `blocker` | `escalate` |
| `resets_at` set, text a block with a `blocker` | `wait` |
| `SPEC_REVIEW_TAGS` patched to add `rewrite`, a `blocker` with `fixes: "rewrite"` | `escalate` |

The witness also asserts `SPEC_REVIEW_TAGS == ("scope", "build",
"witness")` and that it is a tuple. It patches the tags with
`monkeypatch.setattr` on the module.

These fail it, each measured:

- an error on the session ignored
- no block read as clean
- any fence read as `json`
- the first block read in place of the last
- a top-level list accepted
- severity compared without case
- an unknown severity passed over
- an extra key refused
- a finding with no `claim` accepted
- a `fixes` outside the three accepted
- a `fixes` checked on a blocker alone
- a finding that is not an object passed over
- `escalate` only for a `scope` blocker
- `escalate` for any finding with a `fixes`, whatever its severity
- a `resets_at` passed over, reasoned and not measured
- the tags spelled inside the read in place of `SPEC_REVIEW_TAGS`, which
  refuses `rewrite` once it is patched in, reasoned and not measured
- `fixes` dropped from a concern's finding, reasoned and not measured

**Criteria 2 to 4 drive `run_stack_batch`** with a budget of 100,
`until=None`, `_ready` and the `ledger` and `repo_id` fixtures. Build
each candidate with `_candidate`. The runner records
`(candidate.spec.id, predecessor.spec.id or None)`. Each call mints its
own run and a task for its spec id, with one closed attempt at $1. That is
`_spend`'s shape with the spec id in place of `TE-0001`. It returns
`_outcome(state=..., run_id=..., task_id=...)` with that call's run and
task. `_outcome` defaults `task_id` to 1 (`tests/test_batch.py:43`), and
`SA-0145` keys each layer's row on its task, so two layers on task 1
collide. The review double appends the same pair to a list and returns a
canned `SpecReviewSession`.

**Criterion 2's witness** passes this order. Every runner call returns
`READY_FOR_REVIEW`, except `TE-17`'s.

| order | spec | `depends_on` | review, and its layer | outcome |
|---|---|---|---|---|
| 1 | `TE-1` | none | `{"findings": []}`, `None` | runs on `None` |
| 2 | `TE-2` | none | a `scope` and a `build` blocker and a `note`, `TE-1` | escalated, 2 |
| 3 | `TE-3` | none | a `build` blocker, `TE-1` | escalated, 1 |
| 4 | `TE-4` | none | a `witness` blocker, `TE-1` | escalated, 1 |
| 5 | `TE-5` | none | a blocker with no `fixes`, `TE-1` | escalated, 1 |
| 6 | `TE-6` | none | a `concern` with `fixes: "scope"` and a `note`, `TE-1` | runs on `TE-1` |
| 7 | `TE-7` | none | `error` set, text a clean block, `TE-6` | unreviewed |
| 8 | `TE-12` | `TE-1` | clean, `TE-6` | runs on `TE-6` |
| 9 | `TE-8` | none | text with no fence, `TE-12` | unreviewed |
| 10 | `TE-16` | `TE-99` | clean, `TE-12` | runs on `TE-12` |
| 11 | `TE-9` | `TE-6`, `TE-2` | never called | refused, names `TE-2` |
| 12 | `TE-10` | `TE-9` | never called | refused, names `TE-2` |
| 13 | `TE-11` | `TE-7` | never called | refused, names `TE-7` |
| 14 | `TE-13` | `TE-3` | never called | refused, names `TE-3` |
| 15 | `TE-14` | `TE-12`, `TE-1` | clean, `TE-16` | runs on `TE-16` |
| 16 | `TE-17` | none | clean, `TE-14` | runs on `TE-14`, `EXHAUSTED` |
| 17 | `TE-18` | none | clean, `TE-14` | runs on `TE-14` |
| 18 | `TE-15` | none | clean, `TE-18` | runs on `TE-18` |

No spec in the order is `TE-99`. `TE-14` lists its later-built entry
first, and neither entry is the layer it is cut from. A layer between each
errored review and the next resets the breaker. It asserts the runner's
calls in order, and the review's pairs in order, each spec once. It
asserts one ` escalated  ` line each for `TE-2` to `TE-5`, whose text after
that holds the count. It asserts one ` unreviewed  ` line each for `TE-7`
and `TE-8`, and `TE-7`'s holds its session's error text. It asserts one
` refused  ` line each for `TE-9`, `TE-10`, `TE-11` and `TE-13`, naming
what the table says. It asserts one `starting` line for `TE-2`. The stop
reason is `DRAINED`. These fail it, each measured on the loop's rule:

- a withheld spec left out of the misses, which runs `TE-9`
- a descendant check on `depends_on[0]` alone, which runs `TE-9`
- an `error` read as `run`, which runs `TE-7`
- a review's layer from `depends_on[0]`, which reviews `TE-12` on `TE-1`
- a review's layer from `depends_on[-1]`, which reviews `TE-14` on `TE-1`
- `None` for a spec with no `depends_on`, which reviews `TE-15` on `None`
- a review layer kept apart from the runner's predecessor, as the last
  spec handed to the runner, which reviews `TE-18` on `TE-17`
- an `escalate` counted as an abort, which fires the breaker at `TE-4`
- a count of every finding, which prints 3 for `TE-2`
- a spec held until every entry is a layer, which refuses `TE-16`
- a fixed line in place of the read's error

**Criterion 3's witness** passes `TE-41`, with no `depends_on`, then
`TE-42`, with `depends_on: [TE-41]`. `TE-41`'s first call returns
`RATE_LIMITED` with `resets_at` 60 seconds ahead of the clock, and its
second returns `READY_FOR_REVIEW`. It passes a fake `sleep` that records
each call, and a clock as `SA-0148`'s witnesses build one. Every review
returns clean. It asserts the review's pairs are `(TE-41, None)` then
`(TE-42, TE-41)`. It asserts the runner's calls are `TE-41` on `None`
twice, then `TE-42` on `TE-41`. It asserts one sleep, and the stop reason
`DRAINED`. These fail it, each measured on the loop's rule:

- a review on every runner call, which reviews `TE-41` twice
- a route taken out of the store on first use, whose second call raises
  and refuses `TE-42`

**Criterion 4's witness** has four parts. Each passes `TE-31`, `TE-32`
and `TE-33`, with no `depends_on`, and every review clean unless a part
says otherwise.

- The first two reviews raise `RuntimeError`.
- The first review returns a session with `error` set, the second text
  with no fence.
- A readiness check that fails.
- A batch budget of 5, below `TE-31`'s budget of 10.

The first two parts expect `INFRASTRUCTURE`, no runner call, and review
calls for exactly `TE-31` then `TE-32`. The third expects
`INFRASTRUCTURE`, and the fourth `BUDGET`. Both expect no review call and
no runner call. These fail it, each measured on the loop's rule:

- a raise turned into a withheld spec
- an `error` counted as no abort
- a review called before `_drive`'s `--until`, budget and breaker checks,
  which reviews `TE-33`

**Criterion 5's witness** has two parts. The first passes `TE-50` then
`TE-51`, with no `depends_on`, `until=None`, a fake `sleep` and
`SA-0148`'s clock. `TE-50`'s review
returns a session with `error` set. `TE-51`'s first review returns a
session whose text holds no fence and whose `resets_at` is 60 seconds
ahead of the clock. Its second returns clean. It asserts the review's pairs are `(TE-50, None)`,
`(TE-51, None)` and `(TE-51, None)`. It asserts one runner call, `TE-51`
on `None`, the sleeps `[60.0]`, and the stop reason `DRAINED`. It asserts
two `starting` lines for `TE-51`, since the wait offers it again through
`_drive`.

The second part passes `TE-51` alone, with `until` 30 seconds after the
clock's start. Its review returns a session whose `resets_at` is 60
seconds ahead of the clock. It expects the stop reason `UNTIL`, no
sleep, one review, no runner call and one `starting` line for `TE-51`.
`SA-0148` stops `UNTIL` at once there and runs nothing more, so the spec
is never offered again.

These fail it, the first three measured on the loop's rule:

- a `resets_at` passed over, which reads no block and fires the breaker
- a `wait` kept as the spec's route, which waits again and never runs it
- a `wait` counted as an abort, which fires the breaker after `TE-50`
- a wrapper that sleeps and reviews again inside itself, which logs one
  `starting` line and sleeps in the second part
- a synthetic `RATE_LIMITED` outcome, whose attach raises and ends the
  night `INFRASTRUCTURE`
- a `SpecReviewWait` caught by the general handler, which counts an abort

**How the lists were measured.** A throwaway model of the loop's rule and
of the read ran every table above on 2026-09-23. It modelled `SA-0143`'s
miss rule, `_drive`'s checks, `SA-0148`'s wait and the routing here, with each wrong version
as a flag. The right build passed each table. Every wrong version listed
failed at least one, and each failure named above is the one it gave.
The wait signal, criterion 5's second part and the last three wrong
versions under it are not in that model. Nothing below `SA-0175`'s head is
built, so they stay unmeasured.
`run_stack_batch` does not exist at `0b1b4b96`, so nothing ran the real
loop.

**What the witnesses leave undriven.** Only `READY_FOR_REVIEW`,
`EXHAUSTED` and one `RATE_LIMITED` return from the runner in criteria 2
to 5. A `wait` that meets `--until` is `SA-0148`'s rule, driven there for
a task only. `SA-0143`'s own
witnesses drive the other outcomes. A malformed block reaches the loop in
no witness, and routes `error` as a missing one does.

**The `prose` gate** counts every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words. Keep each docstring within ten lines.

**Commit as each witness passes**, before the full suite runs.

**Size.** About 72 changed lines in `saffron/spec_review.py` at 5.3 tokens
a line, the rate `saffron/agents/findings.py` measures. About 50 in
`saffron/batch.py` at 6.6. About 117 lines of test in
`tests/test_spec_review.py` at 4.7, the rate of `tests/test_review.py`.
About 327 in `tests/test_batch.py` at 3.3. That is about 2340 tokens of
the `feature` ceiling of 3000 (`saffron/gates/core/size.py:26`). Three
things move it. The tags constant, its two table rows and its asserts add
about 55. The wait signal adds about 12 lines to `batch.py`, about 80.
Priced at 4 tokens a line, the repo's aggregate, `tests/test_batch.py`
runs about 347 lines with criterion 5's second part, about 1390. That is
about 2780, 93% of the ceiling. No path here is in `elevate_on`, so
`size` stays advisory. Keep the new rows inside the existing loops.
