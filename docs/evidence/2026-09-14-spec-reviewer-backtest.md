# Spec reviewer backtest

Pre-registered 2026-09-14, before any scored review, in the commit that adds this
file. Design: `docs/superpowers/specs/2026-09-14-spec-reviewer-design.md`.
Script: `docs/evidence/scripts/2026-09-14-spec-reviewer-backtest.py`.

## The bar

The reviewer passes if it catches **at least 17 of the 34 known defects** and
raises **at most 2 false blockers across the 10 controls**.

## Scoring

- A known defect is **caught** when a `blocker` or `concern` names the same file
  or criterion and the same kind of defect. Blocker-only recall is reported
  as well.
- A blocker on a control is **false** when its claim does not hold on reading
  the code at the control's version. A blocker whose claim holds is a new find,
  not a false alarm. The operator settles any disputed call.
- Each version is reviewed once, blind: a fresh single-commit snapshot of the
  version (`git archive`), so no later commit is reachable, with Read, Grep
  and Glob scoped to it, `history --before` the version, and no outcome in
  the prompt.

## Known defects

| spec | version | defects |
| --- | --- | --- |
| SA-0005 | 351bdd3 | `touches` lacked `cli.py` and `package.py`, which its criteria needed |
| SA-0009 | ad94fd2 | 990 lines against a 600 ceiling; `EXHAUSTED` at $31.60 |
| SA-0011 | 1e069af | `tests/test_package.py` fakes outside `touches` |
| SA-0014 | e1090dc | false claim about SA-0005's criteria |
| SA-0016 | e1090dc | false claim that its refusal fires on SA-0005 |
| SA-0018 | 366e377 | forbade `DESIGN.md`/`CONTEXT.md`, which the change made false |
| SA-0019 | 6f8e0d7 | orphan criterion broke an invariant; `EXHAUSTED` at $12.12 |
| SA-0020 | 86f0c6e | forbade `saffron/phases/**`, which the fix needed; too wide |
| SA-0025 | 2e4f2e6 | too wide; `NOT_IMPLEMENTED` at 141 turns |
| SA-0026 | 0301518 | test file with a guard outside `touches`; the agent dodged the guard |
| SA-0029 | 3ed6f83 | plan estimated 1100 lines against 600; `PLAN_REJECTED` |
| SA-0029 | 98ce586 | 548 lines grew to 863 in review because 14 criteria demanded tests |
| SA-0031 | 0bcf5ac | `EXHAUSTED` at 141 of 140 turns, $19.17 of $18 |
| SA-0043 | a205a90 | three files outside `touches`; `EXHAUSTED` with a sound diff |
| SA-0044 | 6ceb5ba | criterion 2's witness proved only the half already true; criterion 4's real witness needed a file outside `touches` |
| SA-0051 | 5177edb | three mechanisms; plan at 650 lines against 600 |
| SA-0059 | ab42114 | nine files at `elevated`; `EXHAUSTED` at $26.75 of $16 |
| SA-0063 | 6527f73 | forbade `saffron/phases/**`, home of the only call site; the spec body dictated the literals its mutants pin |
| SA-0065 | d84cab3 | forbidden excluded a caller the change breaks |
| SA-0079 | 1e2209a | the memo witness only ever answered "present" |
| SA-0080 | 1e2209a | missing mutant; the headline witness passed a full re-parse |
| SA-0081 | 1e2209a | missing mutant; a misplaced boundary passed every test |
| SA-0082 | c0e84c3 | the spec's table called an alternative equivalent that is not |
| SA-0083 | c0e84c3 | missing mutant; deleting the override left every test green |
| SA-0084 | c0e84c3 | missing mutant; a partial strip passed "every control character" |
| SA-0085 | c0e84c3 | missing mutant; two witnesses each covered half a claim |
| SA-0086 | 8811f3a | forbade `pr_body.py`, which the change made false; no mutants on an edit, so a witness that could not fail shipped; "verdict" in the spec text, which `CONTEXT.md` forbids in that sense |
| SA-0087 | 24edb32 | 60 turns / $8 against a 47-turn plan checkpoint; criterion 3 charges an unappliable binary stub to the task |
| SA-0087 | 14f6357 | criterion 2's witness passes with `read_head` on the wrong container |

## Controls

| spec | version | started_at |
| --- | --- | --- |
| SA-0062 | 210b0d4 | 2026-09-07 03:04:36 |
| SA-0061 | 210b0d4 | 2026-09-06 17:59:43 |
| SA-0060 | 210b0d4 | 2026-09-06 05:36:50 |
| SA-0056 | ee98185 | 2026-09-05 23:14:16 |
| SA-0055 | 49cc2ef | 2026-09-05 19:46:28 |
| SA-0054 | fdcbbad | 2026-09-05 03:36:10 |
| SA-0030 | 59cde3d | 2026-09-02 03:12:08 |
| SA-0040 | 98ce586 | 2026-09-02 00:52:14 |
| SA-0027 | 094cc4e | 2026-09-01 07:41:50 |
| SA-0024 | 7455593 | 2026-08-31 22:08:37 |

## Results

Not yet run.
