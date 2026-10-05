# Delegate loop onto the stack batch: plan

> **For agentic workers:** this plan runs as five gated stages in order. Code
> changes come from specs that cells implement, or from hand pull requests for
> skill text. Steps use checkbox (`- [ ]`) syntax for tracking.

**Decided 2026-10-03:** stage 1 runs `SA-0200` and four items. Stage 2 runs
three, at a budget of the total divided by 0.75. Seats retire after two
clean batches in a row. Stages 4 and 5 ship as one PR.

**Goal:** the delegate stops driving cells by hand and runs `saffron batch
--stack`, the machine ADR 7 decided and b-792ab2 built.

**Architecture:** harden two failure paths first. Then run the first live
stack batch with the delegate watching. Keep the hand review seats beside the
end review until they stop finding what it misses. Only then cut the skill and
the delegate agent down to what the batch leaves undone.

**Spec:** `docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md`
and section 4 of `docs/superpowers/specs/2026-09-23-stack-batch-design.md`,
"What the delegate still does".

## Global Constraints

- The running loop (run 27, `SA-0197` to `SA-0199`) owns `.claude/skills/run-saffron-spec-loop/`,
  `.claude/agents/delegate.md` and `hooks/delegate_status.py` until its step 6
  handoff. No stage edits them before then.
- Nothing merges without the operator. The batch marks no layer ready (`SA-0170`).
- `CLAUDE_CODE_OAUTH_TOKEN` is scoped to each `saffron cell` or `saffron batch`
  invocation, never exported.
- `SAFFRON_ALLOW_HOST_PROCESS` takes this host's tolerated listener (memory:
  host posture).
- Branches are `joel/<kebab>` under 50 characters. Commit subjects follow `git log`.
- New Markdown passes `python3 hooks/prose_limit.py --file <path>` at zero.

## Facts this plan rests on

Measured 2026-10-03 against `~/.saffron/ledger.db`:

- `stack_layers`, `end_reviews` and `spec_reviews` hold zero rows. No stack
  batch has run live.
- `saffron batch` takes `--repo`, `--budget`, `--until` and `--stack`. There is
  no `--ready` flag. The design's §4 still names one.
- The finish writes `findings.json` (`saffron/finish.py:30`) to the batch tree.
- `driver.py` commands the spec chain still calls: `history`, `check`, `cite`,
  `enumerators`, `bookkeeping`. Commands the reviews still call: `probe`,
  `size`, `jev`, `labels`, `noise`.

## Review Focus

1. A refused API connection during the first batch. Expected: exit 2 and an
   infrastructure state, never a missed layer that refuses its descendants.
2. A malformed wrong-version answer in a batch cell. Expected: one re-prompt,
   then an `error` the REVIEW line names.
3. A review commit pushed to a lower layer while the batch runs. Expected: the
   finish escalates on the head mismatch. The delegate never pushes mid-batch.
4. A `scope` escalation at 03:00. Expected: the batch skips that spec and its
   descendants and keeps going. The delegate answers it in the morning.
5. The delegate hook calling a command that reconciles against GitHub.
   Expected: the session still opens inside the hook's 60 second timeout.

---

### Stage 0: let run 27 finish

- [ ] **Step 1:** wait for run 27's step 6 handoff and its step 5 PR.
- [ ] **Step 2:** the operator merges run 27's stack. `SA-0197`'s multi-task
  `saffron watch` is then on `main`, and stage 2 depends on it.
- [ ] **Step 3:** `git pull` on `main`, then `make check` exits 0.

Stage 1's spec writing can start before this stage ends. Its cells cannot.

### Stage 1: harden the paths a night cannot survive

- **`SA-0200`** for **b-b0cd68**, written in another worktree. Until it
  lands, every finish with a layer turns this repo's suite red and pushes
  nothing. Stage 2 cannot finish without it.
- **b-031ac2**: a refused API connection reads as a failed task.
- **b-7251b5**: a malformed wrong-version answer passes REVIEW.
- **b-038aef**: an `EXHAUSTED` task with green gates opens no PR.
- **b-4c5dc7**: a budget stop after green refuses REBUT, so a one-line fix
  ends `EXHAUSTED`.

In a stack batch the last three each turn a sound task into a missed layer
that refuses its descendants.

- [ ] **Step 1:** merge `SA-0200`'s spec PR from its worktree.
- [ ] **Step 2:** run `create-saffron-spec` on the four items. Each spec goes
  through `spec-writer` and `spec-reviewer` rounds to a clean review, and its
  spec PR merges.
- [ ] **Step 3:** run the attended loop over the five specs with
  `run-saffron-spec-loop`, as run 28. This is the last attended run.
  `snapshot --new` takes all five.
- [ ] **Step 4:** review, stack and file as the skill says. The operator
  merges the stack.

**Done when** all five items are `done` with their PRs, and `main` carries
every fix.

### Stage 2: run the first live stack batch, attended

Payload: **b-23a149** (wall bound cut during a suite GATE repeats),
**b-209696** (a session a bound cuts records $0.00) and **b-60ff2e** (a
layer's peak turns counts spec review attempts). Each is tier 2. The last two
decide whether ADR 7's spend and turn numbers read true.

- [ ] **Step 1:** write the three specs through `create-saffron-spec`, and
  merge their spec PRs. Spec review runs again inside the batch, so this
  review is the comparison for in-batch spec review.
- [ ] **Step 2:** print the plan the batch will run:

  ```bash
  uv run saffron queue --repo . --stack
  ```

  Show the operator the order, each budget and the total. Set `--budget` to
  the specs' total divided by 0.75, rounded up. That holds the end review's
  quarter (`SA-0154`).
- [ ] **Step 3:** start the batch in the background:

  ```bash
  PYTHONUNBUFFERED=1 SAFFRON_ALLOW_HOST_PROCESS=<listener> \
    env CLAUDE_CODE_OAUTH_TOKEN="$(bash -c 'source ~/.secrets; printf %s "$CLAUDE_CODE_OAUTH_TOKEN"')" \
    uv run saffron batch --repo . --stack --budget <N> --until <HH:MM> \
    > /tmp/stack-batch-1.log 2>&1
  ```

- [ ] **Step 4:** follow it with `uv run saffron watch` on every task, and
  send a push notification per escalation line. Push nothing to any layer
  while it runs.
- [ ] **Step 5:** once the process exits, read its exit code and the facts:

  ```bash
  for t in spec_reviews spec_texts stack_layers end_reviews qualifications stack_finishes; do
    sqlite3 ~/.saffron/ledger.db "select '$t', count(*) from $t"; done
  ```

- [ ] **Step 6:** record ADR 7's two measures. First, the share of follow-ups
  that reach `READY_FOR_REVIEW` with a clean critic. Second, the spend per
  follow-up across writing, spec review and cell.
- [ ] **Step 7:** write `docs/evidence/<date>-first-stack-batch.md`. It names
  every step that needed a hand, every escalation and every defect the first
  run found. Each defect becomes a backlog record.

**Done when** the batch exited, its stack is linked, and the evidence file
holds both measures, or names why one is missing.

### Stage 3: hand seats as a comparison

- [ ] **Step 1:** spell the findings block's JSON shape in `REVIEW-PROMPT.md`.
  Run 26 lost two seat reports to YAML and rule names.
- [ ] **Step 2:** run the Spec and Standards seats on every layer PR of the
  stack, as step 2c of the skill does today.
- [ ] **Step 3:** for each seat finding, verify it with `driver.py probe`. Then
  record whether the end review raised it, whether the host qualified it, and
  which follow-up it reached. That table goes in the stage 2 evidence file.
- [ ] **Step 4:** push review commits only after the batch exits. Restack the
  layers above with `driver.py rebase`.
- [ ] **Step 5:** file the backlog from `findings.json` and the seats, in a PR
  on top of the stack. Add a `.saffron/rejections.md` line for each blocker the
  end review missed.

Repeat stages 2 and 3 for each later batch until the retirement test passes.

**Retirement test:** two batches in a row in which the
seats find no blocker the end review missed.

### Stage 4: shrink the skill

Starts after the first batch, on branch `joel/spec-loop-batch-mode`. Stages 4
and 5 ship as one PR. Load
`superpowers:writing-skills` and `mattpocock-skills:writing-for-agents` first.

- [ ] **Step 1:** rewrite `SKILL.md` around the design's five delegate steps:
  print the plan, start the batch, watch and answer escalations, file the
  backlog from `findings.json`, then the summary, feedback and handoff. Stage
  3's seats stay as one step until retirement.
- [ ] **Step 2:** move the attended path into one short section for a single
  spec: `saffron cell`, then `driver.py record`.
- [ ] **Step 3:** delete `snapshot`, `next`, `hold`, `drop`, `status`,
  `stack` and `pattern` from `driver.py`, with their tests in
  `tests/test_spec_loop_driver.py` and `tests/test_loop_reconciles_first.py`.
  Keep `record`, `rebase` and every command the facts section lists.
- [ ] **Step 4:** cut `GOTCHAS.md` to the sections the new steps still meet.
- [ ] **Step 5:** amend the design's §4 to drop `--ready` from step 1.
- [ ] **Step 6:** `make check` exits 0, then open the PR from
  `.github/pull_request_template.md`.

**Done when** the skill reads as about a page plus the seat step, and every
deleted command has no caller (`grep -rn "driver.py <cmd>"` prints nothing).

### Stage 5: retarget the delegate agent

Same branch and PR as stage 4.

- [ ] **Step 1:** change `hooks/delegate_status.py` to run
  `uv run saffron queue --repo . --stack`. Time it against the hook's 60
  second limit, and fall back to `saffron watch --no-follow` if it runs over.
- [ ] **Step 2:** rewrite `.claude/agents/delegate.md`'s summary section to
  read the queue page's stack view. Hand-collect only what it lacks.
- [ ] **Step 3:** rewrite its goal paragraph. Feedback ranks by end-review
  misses from stage 3's table, then by steps that still needed a hand.
- [ ] **Step 4:** open a fresh `claude --agent delegate` session and confirm
  the hook prints the stack queue.

**Done when** a new delegate session opens on the batch's status and its
instructions name no retired command.
