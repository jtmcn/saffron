## SA-0054 pre-run review, base `HEAD` (snapshot of `fdcbbad`)

This spec isn't runnable at this base. The loop, the batch ledger writers, the readiness check and the extracted scan it builds on are all missing from this commit, and the files that would hold them are `forbidden`.

### Findings

- **Blocker. Everything the spec calls is missing at base (checks 6 and 2).** The spec says at SA-0054:121–122: *"`SA-0050` built the loop and left it with no caller. `SA-0051` extracted the scan"*. At SA-0054:179–181 it says *"`preflight.check_readiness` takes the repo, the mirror path, a scratch directory, the home directory and the token"*. What base actually has:
  - `git ls-tree -r HEAD` lists no `saffron/batch.py` and no `tests/test_batch.py`.
  - Searching `saffron/`, `tests/` and `images/` for `run_batch|check_readiness|open_batch|close_batch|batch_id` finds nothing.
  - `saffron/ledger.py:3` says *"Seven of the ten tables. `batches` and `decisions` wait for a scheduler"*, so SA-0045 and SA-0049 have not landed either.
  - `saffron/preflight.py` defines only the host-probe functions (lines 37–253). There is no readiness entry point.
  - The scan still runs inline in `_queue`: `cli.py:543` calls `reconcile(ledger, repo_id, gh=_guarded_gh(gh_failures))`, with no stamping argument and no separate resolve function.
  - The spec forbids every file that would have to supply these: `saffron/batch.py` (spec:15), `saffron/ledger.py` (:22) and `saffron/preflight.py` (:24).
  - `history` lists SA-0050, SA-0049 and SA-0045 as `MERGED`, but their code is not in this tree. SA-0051 has no row at all.
  - `depends_on: SA-0051` won't save the cell. The attended path doesn't enforce dependencies (`cli.py:303–307`: *"not this attended path's check to make"*). With no waiting row for SA-0051, `_resolve_stacked_on` returns `(None, None)` (`cli.py:336–338`), so the cell would be cut unstacked from this base.

  **Fix:** cut the base from a commit where SA-0045, SA-0048, SA-0049, SA-0050 and SA-0051 are all merged, then re-review. The spec also makes claims I couldn't check here, including the readiness signature and *"The loop's default is to proceed"* (spec:77).

- **Blocker. Criterion 4's witness is already true at base (check 3).** Criterion 4 (spec:52–58) claims *"Neither a concurrency flag nor a multi-repo flag exists."* At base there is no `batch` subcommand at all: the subparsers at `cli.py:74–127` are `replay`, `cell`, `queue`, `reconcile` and `watch`. So `saffron batch --concurrency 3` already exits `2` from argparse, and neither flag exists anywhere. A witness that only checks the flags are rejected passes at base. DESIGN.md:837 requires a witness that *"did **not** pass at `base_sha`"*, so `criteria` fails the attempt. **Fix:** reword the claim so its witness asserts the `batch` subcommand's exact option set (`--repo`, `--budget`, `--until`, `-h`). That fails at base.

- **Concern. The batch's `--budget` would leak into every task's ceiling, and no criterion catches it (check 3).** `_ceilings` reads `"budget_usd": args.budget` (`cli.py:188`) and lets a given flag win (`cli.py:193`, labelled `"flag"` at :202–203). Criterion 1 gives the batch's `--budget` a default of 50. If the adapter reuses `_ceilings` with the batch's namespace, as spec:166 ("reuse rather than reimplement") invites, every task runs with a $50 ceiling marked "(flag)". The loop's budget gate meanwhile compares against the spec's $12. Only prose (spec:169–170) says ceilings come from the spec, and every witness would still pass. **Fix:** add a criterion that each task's `CellSpec` carries the spec's own `budget_usd`, `max_attempts` and `max_turns`, driven with `--budget 50`.

- **Concern. PACKAGE isn't pinned for the adapter.** `_run_cell` calls `package_phase.package(..., parent_branch=target_branch)` only after `run_one_cell` (`cli.py:496–511`). An adapter that just returns `run_one_cell`'s outcome passes all eleven witnesses. The night would then end with `READY_FOR_REVIEW` rows and no pull requests. A later child would also resolve unstacked, with *"records no pushed branch"* (`cli.py:344–353`). Spec:160–162 mentions *"the sha and the branch together or neither"* but no witness checks it. **Fix:** add a criterion that a reviewable outcome is packaged with the parent's branch.

- **Concern. The real readiness check may reach the network in tests.** Criterion 8 (spec:75–81) requires the real check to be bound. But `tests/conftest.py:13` blocks only `{runtime.RUNTIME, "gh"}`, and `tests/test_cli.py:23–26` is an autouse fixture that sets a fake token (`sk-test`) for every test. SA-0048's own notes (SA-0048:189–193) warn that its probe uses `urllib`, which conftest doesn't block. Spec:189–195 covers containers only. **Fix:** tell the agent to assert which arguments the readiness callable is bound to, using a patched `saffron.cli` namespace, rather than invoking it. **Unverified:** how the probe connects, since it doesn't exist at base.

- **Concern. Size is near the ceiling (check 5).** My estimate for `saffron/cli.py`:

  | Piece | Lines |
  |---|---|
  | Subparser | ~15 |
  | `HH:MM` resolver | ~20 |
  | `_batch` body, readiness binding and exit map | ~70–90 |
  | Adapter, factored out of `_run_cell` (moved lines count twice) | ~70–130 |
  | **Code subtotal** | **~180–260** |

  The eleven witnesses add ~300–380 more, since the stacking ones need real-origin fixtures (`test_cli.py:379–420`). That is **~480–640 changed lines against the 600-line feature ceiling.** For comparison:
  - SA-0026 (stacking in `cli.py`, 11 criteria): 487 lines.
  - SA-0050 (10 criteria): 576 lines.
  - The combined first SA-0051, which included this half, was planned at 650 and refused (SA-0051:79–84).

  **Fix:** add up the planned lines at the checkpoint, or drop criterion 11, which mostly repeats `test_only_the_first_depends_on_entry_is_a_stacking_candidate` (`test_cli.py:760`).

- **Concern (unverified). Criterion 9 needs a result shape I can't see.** It says *"the result carries the step"* (spec:82–86). SA-0050's notes (SA-0050:201–204) say the loop returns the stop reason itself. The failing step would therefore have to be captured inside the readiness closure in `cli.py`. Nothing at base confirms either shape.

- **Note. CLAUDE.md goes stale.** It says *"Exit codes are load-bearing: `0` reviewable, `1` the task did not make it, `2` infrastructure failed (`saffron/cli.py`)"*, and its "Running the CLI" block lists no `batch`. After this change `batch` exits `0` on a night with failures. CLAUDE.md isn't in `touches`, so it needs a hand edit after merge.

- **Note. The deadline's timezone isn't specified.** `--until 06:30` is a local time, and the spec doesn't say whether it is naive or timezone-aware. Across a DST change the resolved deadline can be off by an hour.

- **Note. This repo has no `mutant` convention.** The `Criterion` model is `extra="forbid"` with only `claim`, `witness` and `preserves` (`saffron/intake.py:44–60`). `docs/agents/issue-tracker.md` has no witness, mutant or preserves conventions. A mutant can't be declared, so I tested each witness against plausible wrong implementations instead (the two concerns above).

### Checks

- `checked: criteria vs invariants` — I compared the CLAUDE.md invariants with DESIGN §4.2.1:396–410. The exit codes match DESIGN:410 and the `RATE_LIMITED` breaker matches DESIGN:398. Nothing crosses `error` ≠ `fail`.
- `found: scope reaches the change` — findings 1, 8.
- `found: witness/mutant discipline` — findings 2, 3, 4, 10. No SA-0054 witness name exists at base, and none claims `preserves`.
- `checked: ceilings vs history` — `max_turns` 90 is above every completed peak: SA-0050 36t, SA-0053 36t, SA-0026 53t, SA-0025 62t, SA-0028 67t. SA-0025's 141t `error_max_turns` row was PACKAGE work, and its later run finished at 62t. Plan plus implement was $2.40 for SA-0050 and $7.45 for SA-0026. That leaves at least $4.55 of the $12, against $2.66–$3.57 for review plus rebut.
- `found: size vs ceiling` — finding 6.
- `found: claims about current code` — findings 1, 7. The claims about `_run_cell`, `addopts`, the `--collect-only` argv and conftest's blocks are true at base (`cli.py:371–492`, `pyproject.toml:43`, `.saffron/gates/tests.py:37`, `conftest.py:13`).

### Assessment

Not runnable at this base. It could become runnable after re-cutting from a commit where SA-0045 through SA-0051 have merged, fixing criterion 4's witness, and re-reviewing the claims that depend on those parents.

One Bash call (a loop over the witness names) was denied because it needed an approval this session can't give. I got the same answer with Grep, so nothing is missing. Separately, several claude.ai connectors (Booking.com, Expedia, Google Drive, Hugging Face, Slack, Tripadvisor) need authorizing in claude.ai's connector settings before they can be used. This review didn't need them.