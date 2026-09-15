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
- Each version is reviewed once, blind: a detached worktree at the version,
  `history --before` the version, and no outcome in the prompt.

## Known defects

| spec | version | defects |
| --- | --- | --- |
| SA-0005 | 351bdd3 | touches lacked cli.py and package.py, which its criteria needed |
| SA-0009 | ad94fd2 | too wide: 990 lines against a 600 ceiling |
| SA-0011 | 1e069af | tests/test_package.py Spec fakes outside touches |
| SA-0014 | e1090dc | false claim about SA-0005's criteria |
| SA-0016 | e1090dc | false claim that its refusal fires on SA-0005 |
| SA-0018 | 366e377 | forbade DESIGN.md/CONTEXT.md, which the change made false |
| SA-0019 | 6f8e0d7 | orphan criterion broke an invariant |
| SA-0020 | 86f0c6e | forbade saffron/phases/**, which the fix needed |
| SA-0025 | 2e4f2e6 | too wide for its ceilings |
| SA-0026 | 0301518 | test file holding a guard outside touches |
| SA-0029 | 3ed6f83 | too wide: plan at 1100 lines against 600 |
| SA-0029 | 98ce586 | 14 criteria demand tests past the 600 ceiling |
| SA-0031 | 0bcf5ac | turn and budget ceilings too low for its width |
| SA-0043 | a205a90 | golden fixture, test_events.py, test_session.py outside touches |
| SA-0044 | 6ceb5ba | criterion 2's witness proves only the half already true; criterion 4's real witness needs tests/test_worktree.py, outside touches |
| SA-0051 | 5177edb | three mechanisms; 650 lines against 600 |
| SA-0059 | ab42114 | nine files at elevated: too wide for its ceilings |
| SA-0063 | 6527f73 | forbade saffron/phases/**, home of the only call site; the body dictates the literals its mutants pin |
| SA-0065 | d84cab3 | forbidden excludes a caller the change breaks |
| SA-0079 | 1e2209a | missing mutant: the memo witness only answers 'present' |
| SA-0080 | 1e2209a | missing mutant: headline witness passes a full re-parse |
| SA-0081 | 1e2209a | missing mutant: a misplaced boundary passes |
| SA-0082 | c0e84c3 | its table calls a non-equivalent alternative equivalent |
| SA-0083 | c0e84c3 | missing mutant: deleting the override stays green |
| SA-0084 | c0e84c3 | missing mutant: a partial strip passes 'every control character' |
| SA-0085 | c0e84c3 | missing mutant: two witnesses each cover half a claim |
| SA-0086 | 8811f3a | forbade pr_body.py, which the change made false; no mutants on an edit, so a witness that cannot fail ships; 'verdict' used in the sense CONTEXT.md forbids |
| SA-0087 | 24edb32 | 60 turns / $8 against a 47-turn plan checkpoint; criterion 3 charges an unappliable binary stub to the task |
| SA-0087 | 14f6357 | criterion 2's witness passes with read_head on the wrong container |

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
