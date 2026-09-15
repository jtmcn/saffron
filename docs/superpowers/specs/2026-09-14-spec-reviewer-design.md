# A spec review, before any cell spends money

2026-09-14. Designed with the operator after the spec loop was used a second
time (`docs/evidence/2026-09-14-spec-loop-skill-feedback-run-2.md`).

**Status:** built; backtest FAIL (K = 5 false blockers against a bar of 2, recall 18/34, operator's ruling). The reviewer stays advisory. See docs/evidence/2026-09-14-spec-reviewer-backtest.md and BACKLOG items 123–125.

## Why

Of the cells whose failure a written record blames on something, the most
common cause is the spec. Appendix A lists 38 such defects across 32 spec
versions. Every control a
spec meets before a cell is about its form. Intake validates the schema and
refuses a disclosed mutant. The scheduler refuses a protected path in
`touches`, a criterion path outside it, a `retired-by` marker it cannot reach,
and an unmet `depends_on`. `tests/test_queued_specs.py` now runs the stateless
half of those refusals in CI. Nothing checks what a spec means until a cell
has paid for the answer. SA-0087 cost $22.42 over two cells to show its
ceilings were too low and one criterion broke `error` ≠ `fail`.

Specs are already reviewed by hand, and it pays when it happens: Appendix B
lists 29 specs whose defects a review caught before any cell ran. It does not
happen every time, and #253's review of SA-0086–0089 missed the ceilings and
the binary-patch criterion. This design makes the review a standing step and
measures it before anything is promoted.

## Decisions

| Question | Decision |
|---|---|
| When it runs | Both when a spec is written, before its PR merges, and in the spec loop before the spec's first cell. One definition serves both. |
| Authority | Advisory. In the loop, a blocker is put to the operator as a question before that spec's cell; the rest are kept for step 5. Nothing enforces it in code. |
| Shape | One agent, plus a deterministic `history` command for the numeric checks (approach A). Two seats is the fallback if the backtest shows one kind of check crowding out another. |
| Checks | Six. See the contract below. |
| Promotion | Decided by a backtest against a bar fixed before it runs. |

## Components

1. **`.claude/agents/spec-reviewer.md`: the agent definition.** A delegate
   runs it with read-only tools: Read, Grep, Glob, and Bash for `git show`,
   `git log`, `git ls-tree`, `git grep` and `driver.py history` only. Its
   input is a spec path and a base commit, which defaults to `origin/main`. It never edits a file and never runs
   tests, because a spec has no implementation to probe.
2. **`driver.py history SA-NNNN [--before <commit>]`: the numbers.**
   Deterministic, and it reads the ledger only. For the spec's `type`, it
   prints past cells' plan-checkpoint turns and cost (the first `IMPLEMENTING`
   attempt), IMPLEMENT turns and cost, REVIEW and REBUT spend, each
   attempt's `subtype` and `terminal_reason`, and the last `size` gate
   summary. Specs of similar shape come first, by `touches` count and criteria
   count. `--before` drops every task that started after the commit's date,
   along with the spec's own tasks. That closes the one leak a blind review
   would otherwise have. It lives in the loop's driver, which already owns
   ledger reads, and is callable on its own.
3. **Where it runs.**
   - In the loop: a step 1b in the loop skill, between snapshot and the first
     cell. One spec review per spec in the order, in parallel.
   - When writing a spec: one line in `docs/agents/issue-tracker.md`.
4. **The backtest.** The script goes under `docs/evidence/scripts/` and the
   record under `docs/evidence/`. Following the `harness/` convention, the
   part that spends money stays out of `saffron/`.

No `saffron/` code changes. A spec-review cell in DIAGNOSE's slot (§3.3, §5.2)
is a later spec, and only if the backtest passes.

## The review contract

**Inputs.** Everything is read at the base commit through
`git show <base>:<path>`, never from the working tree unless the checkout is a
snapshot of the base, as the backtest's are:

- the spec's frontmatter and body;
- `CLAUDE.md` and `CONTEXT.md`;
- the `DESIGN.md` sections the spec cites;
- `docs/agents/issue-tracker.md`'s spec conventions;
- the code the spec names;
- `history` for the spec's `type`, limited to tasks before the base.

The delegate is never shown a cell's outcome.

**The six checks.** A `blocker` is a defect that, built to the letter, gets a
cell wrong. With no task yet to route to REBUT, it becomes a question to the
operator. A `concern` needs the operator's judgement, and a `note` is true but
trivial (`CONTEXT.md`'s severities).

| Check | Blocker when |
|---|---|
| Criteria vs invariants | A criterion built to the letter breaks a `CLAUDE.md` invariant or a `DESIGN.md` principle. The finding quotes both. |
| Scope reaches the change | A file the change must edit is outside `touches` or inside `forbidden`: a caller of a changed signature, a consumer whose output the change makes false, a test file holding a guard, a fixture. The finding names the line that makes the file necessary. |
| Witness/mutant discipline | Any of three: an edit spec has a criterion with no mutant whose witness a named plausible wrong implementation would pass; a `preserves` witness names a test absent at base; a non-`preserves` witness is already green at base. |
| Ceilings vs history | `max_turns` or `budget_usd` is below what similar past cells spent on the plan checkpoint plus IMPLEMENT, citing `history` rows. It is a `concern` when the remainder cannot cover REVIEW and REBUT at their usual cost (item 120). |
| Size vs ceiling | The criteria, `touches`, and the tests they demand imply more changed lines than the type's `size` ceiling, going by `history`'s past sizes (item 56's check, done by judgement rather than formula). |
| Claims about current code | A factual sentence about the code at base is false and a criterion depends on it. It is a `concern` when nothing depends on it. |

**Output.** The findings come first, in the review seats' format: severity,
file:line, the rule broken quoted with its own file:line, the evidence, and the
fix. Then one line per check, `checked: …` or `found: …`, so a check that did
not run never reads like one that ran and found nothing (§5.4). Then an
assessment: runnable, runnable after the listed fixes, or not runnable.

## The backtest

**Known defects.** Appendix A, minus the four rows rated low or medium-low
confidence because their records blame the system: SA-0021, SA-0058, SA-0064,
and SA-0087's second-cell REBUT budget. That leaves 34 known defects across 29
spec versions. Each version is reviewed once, at its recorded pre-cell commit,
and scored against every defect recorded for it.
Appendix B is reported alongside but not scored, because no cell outcome
confirms it.

**Clean controls.** The ten most recent specs in `.saffron/specs/done/` that
appear in neither appendix and reached `READY_FOR_REVIEW` on their first cell.
Each is reviewed at the commit before its cell ran.

**Scoring, fixed before the first review.**

- A known defect is *caught* when a `blocker` or `concern` names the same file
  or criterion and the same kind of defect. Blocker-only recall is reported
  too.
- A blocker on a control is *false* when its claim does not hold on reading the
  code at base. The operator settles any disputed call. A blocker whose claim
  does hold is a new find, not a false alarm, and is recorded as one.
- **The bar:** at least 17 of the 34 known defects caught, and at most 2 false
  blockers across the 10 controls.

**Order.** The known-defect list, the control list and the scoring rule are
committed to `docs/evidence/<date>-spec-reviewer-backtest.md` before the first
review, so its history shows the bar came first. Each review is a fresh
headless session running the agent. That makes 39 reviews (29 versions and 10
controls) at roughly lens cost
($1–2 each). The results go into the same file: a per-case table, both
rates, pass or fail against the bar, and any new finds.

## Out of scope

- Blocking in code (`next` refusing a spec with an unanswered blocker).
- A spec-review cell, and CI running the model review. Both wait on the
  backtest, and CI also waits on podman in CI being measured and the operator's
  decision on the token secret.
- Two seats.
- Enforcing the mutant rule at intake.

## Appendix A — cells whose failure the record blames on the spec

Collected 2026-09-14 from `.claude/skills/run-saffron-spec-loop/GOTCHAS.md`,
`.saffron/rejections.md`, `docs/BACKLOG.md`, `docs/agents/issue-tracker.md`, `docs/evidence/`,
`DESIGN.md` and the git history of `.saffron/specs/`. Each version is the last
commit touching the spec before its cell or its fixing commit. The ledger's
`spec_sha` is not a git blob id, so it cannot be used to recover the text.

| Spec | Defect | Recorded at | Version | Confidence |
|---|---|---|---|---|
| SA-0005 | `touches` lacked `cli.py` and `package.py`, which its criteria needed | BACKLOG.md item 18; DESIGN.md §4.2.1; `3de35ab` | `351bdd3` | high |
| SA-0009 | 990 lines against a 600 ceiling; `EXHAUSTED` at $31.60 | BACKLOG items 25, 56 | `ad94fd2` | high |
| SA-0011 | `tests/test_package.py` fakes outside `touches` | BACKLOG item 21; `ff997e2` | `1e069af` | high |
| SA-0014 | false claim about SA-0005's criteria | `bf5a93e`; `done/README.md` | `e1090dc` | medium |
| SA-0016 | false claim that its refusal fires on SA-0005 | `366e377` | `e1090dc` | medium |
| SA-0018 | forbade `DESIGN.md`/`CONTEXT.md`, which the change made false | BACKLOG items 27, 30 | `366e377` | high |
| SA-0019 | orphan criterion broke an invariant; `EXHAUSTED` at $12.12 | BACKLOG item 29; `dc71072` | `6f8e0d7` | medium-high |
| SA-0020 | forbade `saffron/phases/**`, which the fix needed; too wide | BACKLOG item 33; `77b5ba6` | `86f0c6e` | high |
| SA-0021 | `touches` named a protected path; `PLAN_REJECTED` | BACKLOG item 28 | `6bcf365` | low (excluded) |
| SA-0025 | too wide; `NOT_IMPLEMENTED` at 141 turns | `fcc5c87`; BACKLOG item 34 | `2e4f2e6` | medium |
| SA-0026 | test file with a guard outside `touches`; the agent dodged the guard | BACKLOG items 33, 35 | `0301518` | high |
| SA-0029 | plan estimated 1100 lines against 600; `PLAN_REJECTED` | `98ce586` | `3ed6f83` | high |
| SA-0029 | 548 lines grew to 863 in review because 14 criteria demanded tests | BACKLOG item 40 | `98ce586` | medium |
| SA-0031 | `EXHAUSTED` at 141 of 140 turns, $19.17 of $18 | `268449c` | `0bcf5ac` | medium-high |
| SA-0043 | three files outside `touches`; `EXHAUSTED` with a sound diff | `990ad71` | `a205a90` | high |
| SA-0044 | criterion 2's witness proved only the half already true | `4bf170d` | `6ceb5ba` | high |
| SA-0044 | criterion 4's real witness needed a file outside `touches` | `done/README.md` | `6ceb5ba` | medium |
| SA-0051 | three mechanisms; plan at 650 lines against 600 | `fdcbbad` | `5177edb` | high |
| SA-0058 | the seam needing change was outside every `forbidden` list | BACKLOG item 71 | `bf55842` | medium-low (excluded) |
| SA-0059 | nine files at `elevated`; `EXHAUSTED` at $26.75 of $16 | `docs/evidence/2026-09-06-an-attempt-is-the-overshoot-bound.md` | `ab42114` | high |
| SA-0063 | forbade `saffron/phases/**`, home of the only call site | `a4618f4` | `6527f73` | high |
| SA-0063 | the spec body dictated the literals its mutants pin | BACKLOG item 82 | `6527f73` | high |
| SA-0064 | a mutant that matched at base; a witness subject in a forbidden file | BACKLOG items 83, 84 | `a4618f4` | low-medium (excluded) |
| SA-0065 | forbidden excluded a caller the change breaks | BACKLOG item 26; `93f3cb4` | `d84cab3` | high |
| SA-0079 | the memo witness only ever answered "present" | `rejections.md` | `1e2209a` | medium |
| SA-0080 | missing mutant; the headline witness passed a full re-parse | `rejections.md`; BACKLOG item 40 | `1e2209a` | medium |
| SA-0081 | missing mutant; a misplaced boundary passed every test | `rejections.md` | `1e2209a` | medium |
| SA-0082 | the spec's table called an alternative equivalent that is not | `rejections.md`; run-1 feedback | `c0e84c3` | medium-high |
| SA-0083 | missing mutant; deleting the override left every test green | `rejections.md` | `c0e84c3` | medium |
| SA-0084 | missing mutant; a partial strip passed "every control character" | `rejections.md` | `c0e84c3` | medium |
| SA-0085 | missing mutant; two witnesses each covered half a claim | `rejections.md` | `c0e84c3` | medium |
| SA-0086 | forbade `pr_body.py`, which the change made false | `rejections.md`; BACKLOG items 40, 118 | `8811f3a` | high |
| SA-0086 | no mutants on an edit, so a witness that could not fail shipped | `rejections.md`; BACKLOG item 121 | `8811f3a` | high |
| SA-0086 | "verdict" in the spec text, which `CONTEXT.md` forbids in that sense | `rejections.md`; BACKLOG item 118 | `8811f3a` | medium |
| SA-0087 | 60 turns / $8 against a 47-turn plan checkpoint | `14f6357`; BACKLOG item 119 | `24edb32` | high |
| SA-0087 | criterion 3 charges an unappliable binary stub to the task | BACKLOG item 118 | `24edb32` | high |
| SA-0087 | criterion 2's witness passes with `read_head` on the wrong container | BACKLOG item 118 | `14f6357` | medium |
| SA-0087 | $14 left REBUT $3.09 | BACKLOG item 120 | `14f6357` | low (excluded) |

## Appendix B — defects caught by a review before any cell ran

SA-0001 (`2b4a90e`), SA-0011 (`5d68699`), SA-0013 (`7c43868`),
SA-0017 (`0cbe950`), SA-0022 (`151568d`), SA-0025 (`2e4f2e6`, `9516a6b`),
SA-0029 (`3ed6f83`), SA-0031 (`1fcc359`, `0bcf5ac`), SA-0041/0042 (`8bf8882`),
SA-0044 (`6ceb5ba`), SA-0045 (`2e563cf`), SA-0046 (`be3ed91`),
SA-0048 (`c5b8838`), SA-0049/0050 (`535bf23`, `5177edb`),
SA-0052 (`865c11a`, `9299734`), SA-0066–0070 (`15f4d77`),
SA-0071–0073 (`25cbf81`), SA-0077 (`a74a21a`), SA-0087 (`24edb32`),
SA-0088/0089 (`14f6357`). Each commit is the fix. The version a spec review
would see is its parent.
