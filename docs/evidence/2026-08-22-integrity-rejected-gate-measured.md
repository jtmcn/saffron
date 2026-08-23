# The rejected `integrity` gate, measured

Taken 2026-08-22, before writing
`docs/superpowers/specs/2026-08-22-integrity-split-design.md`. `docs/BACKLOG.md`
item 1 says to read the rejected patch and its review before writing anything;
this is what running it found on top of reading it.

**The subject is not the patch Appendix K reviewed.** `~/.saffron/batches/v0/SA-0004/patch.diff`
is the cell's export, and `rebuttal.json` records `head_moved: true` — the
implementer changed the removal check during REBUT and the lens withdrew its
blocker. Appendix K describes the code as the operator applied and reviewed it;
the exported patch is one fix later. Both accounts are honest about different
artifacts, which is exactly the shelf-life problem Appendix K's own "patches
perish" note describes, arriving in a second form.

## Method

The module was loaded from the applied patch by path (`importlib`, not installed
into `saffron/`), and handed diffs produced by real `git` in throwaway
repositories with `worktree.DIFF_FLAGS` — the same flags the host pins for the
diff a gate actually sees. Patterns came from this repo's `.saffron/policy.yaml`
for the real-commit runs, and from an equivalent literal for the scenarios.

Scripts, runnable from the repo root with `uv run python`:

| Script | What it produces |
|---|---|
| `scripts/2026-08-22-integrity-scenarios.py` | the eight-scenario table below |
| `scripts/2026-08-22-integrity-newline-positions.py` | all four `\ No newline` positions, with the diffs printed |
| `scripts/2026-08-22-integrity-real-commits.py` | the gate against five merged commits of this repo |

They import the module from `~/.saffron/batches/v0/SA-0004/` applied to a scratch
directory. Once the split lands they will not run against anything current; they
are kept as the record of what the measurement was, not as a suite.

## What the scenarios returned

| Scenario | Status | Codes |
|---|---|---|
| delete one test, nothing in its place | `fail` | `removed-test` |
| delete one test, leave a comment in its place | `pass` | — |
| gut a test body in place (`assert 2 == 2` → `pass`) | `pass` | — |
| consolidate two tests into one `parametrize` | `pass` | — |
| delete the whole test file | `fail` | `removed-test` |
| move a test file out of `tests/` | `fail` | `removed-test` |
| rename `test_b` → `check_b`, body intact | `pass` | — |
| add a test to a file with no trailing newline | `pass` | — |

## Three corrections to Appendix K

**1. The no-newline defect is fixed in the exported patch.** Appendix K: *"there
is a branch for it — and put it in the one position git does not use."* All four
positions git emits the marker parse without error: after a `-` line (old file
lacked the newline), after a `+` line (new file lacks it), after both (neither
has it, content changed), and in a single-line file. Verified with the diffs
printed, so the marker is demonstrably present in each. Nothing to repair.

**2. The removal check is run adjacency, not net line count.** `_unreplaced_removals`
counts a maximal run of `-` lines only when no `+` run is immediately adjacent on
either side. So the `parametrize` false positive Appendix K reports is gone — and
the evasion is *cheaper* than the appendix says, not harder. It does not take a
comment longer than the test; one adjacent added line of any content is enough,
because the gate never asks what the added line says. Appendix K's "wrong in both
directions on one comparison" no longer describes this code.

**3. A defect nothing records: the gate fails this repo's own merges.**
Suppression tokens are substring-matched against every added line in every file,
so prose containing a token fails. Run against five merged commits, four pass and
`d1141d0` — the merge of PR #5 — returns `fail`:

```
saffron/report/pr_body.py:100   added-suppression   '@pytest.mark.skip'
tests/test_report.py:266        added-suppression   '@pytest.mark.skip'
```

Both are docstrings, and both are explaining that a critic's claim routinely
quotes `@pytest.mark.skip` — text about the token, not a use of it. This is also
what the "sixteen violations on its own pull request" were: `integrity.py` and
its fixtures quote every token in the repo's `suppressions` list. Appendix K
attributes those to the omitted `touches` exemption, which is true, and leaves
unsaid that the exemption is the *only* defence a substring scan has. That is an
argument about which checks the exemption binds, and the spec's part 3 makes it.

## What did not need correcting

Everything the review praised held up under execution: the §2.1 split, `error`
kept distinct from `fail`, count-driven hunk consumption, line numbers from the
`@@` header, the pinned-prefix refusal, and suppression detection restricted to
added lines. The two scenarios that return `pass` and should not are both
questions about *which tests exist*, and neither is answerable from a diff.
