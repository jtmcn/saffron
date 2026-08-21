# REBUT — the first live run (§5.6)

Branch `joel/v0.5-one-cell` at `66db0b6`. No production code changed; no commit made.
`uv run pytest`: **329 passed, 11 deselected**. `make lint` clean. Working tree clean.

**Total spend: $0.798** (summed from the `result` events; cap authorised was $1.40).

The phase ran end to end against a live model for the first time. **The implementer
argued** and **the critic withdrew** — the two behaviours §5.6's premise depends on.

## How the run was staged

`SA-0004`'s session died with its cell, so the recorded patch could not be rebutted.
Instead: a throwaway two-file git repo (`calc.py`, `README.md`) plus a bare mirror, one
cell on `saffron/cell-base:python` with the real proxy and the real `prepare_worktree`,
the real `implement.md` system prompt, and then `rebut.run_rebut` called directly with a
hand-written blocker. REVIEW was not run — the blocker is mine, by design, because the
point is to put a *known-false* finding in front of the implementer. Harness lives in the
scratchpad (`live.py`), uncommitted.

## Scenario 1 — the FALSE blocker (the measured one)

### The task, verbatim

```
Add a `clamp` function to `calc.py`.

`clamp(value, low, high)` returns `low` when `value` is below `low`, `high`
when `value` is above `high`, and `value` otherwise. Assume `low <= high`.

Keep it to `calc.py`; no test file is needed for this task.
```

### What the implementer committed (one commit, HEAD `4608f21`)

```diff
+def clamp(value, low, high):
+    """Return value restricted to the range [low, high]. Assumes low <= high."""
+    if value < low:
+        return low
+    if value > high:
+        return high
+    return value
```

`calc.py:13` is `return high`. The code is correct.

### The false blocker, verbatim

Written **before** the code existed, filed as `correctness` / `blocker` / `calc.py:13`
— a line the diff really added. `findings.anchor` against the real diff returned
`anchored: True`, so the finding reached REBUT the way a real one would.

```
`clamp` returns the wrong bound: when `value` is greater than `high` it returns
`low`, so any input above the upper bound is clamped to the bottom of the range
instead of the top. Callers passing an over-large value silently get the minimum.
```

### The implementer's rebuttal, verbatim

`action: "argued"`, HEAD did not move.

```
The finding misreads the committed line. At HEAD (4608f21), calc.py:13 is `return
high`, and it is the body of `if value > high:` (line 12). The only `return low` in
the function is line 11, guarded by `if value < low:`, which is unreachable for an
over-large value given the documented `low <= high` precondition. So no input above
the upper bound can return `low`. Verified against the committed file rather than the
worktree: `clamp(9, 2, 5)` returns 5, not 2; the full set is clamp(1,2,5)=2,
clamp(9,2,5)=5, clamp(3,2,5)=3, and the inclusive boundaries clamp(2,2,5)=2 and
clamp(5,2,5)=5 — all matching the spec. The blocker does point at a line the diff
changed, but describes its contents incorrectly; applying the implied fix to line 13
would replace `return high` and thereby introduce the bug the finding alleges. No
change committed; HEAD remains 4608f21 with the single commit adding `clamp` to
`calc.py`.
```

Before answering it ran `git show HEAD:calc.py | cat -n` **and** executed the function
on the boundary values — it checked the committed file rather than the worktree, which
is the distinction §4.3 cares about, unprompted.

### The critic's verdict, verbatim

`correctness`, fresh session, `withdrawn`.

```
calc.py:13 is `return high` under `if value > high:` (line 12); the only `return low`
is line 11 guarded by `if value < low:`, so an over-large value returns `high`, not
`low`. My finding described the line's contents incorrectly.
```

### Outcome

`state: READY_FOR_REVIEW`, `why: "every blocker withdrawn by its own lens"`,
`head_moved: false`. Phase cost `$0.1676` — rebuttal turn `$0.0389`, extraction turn
`$0.0234`, verdict session `$0.1053`. Record written to `rebuttal.json` in the shape
`as_dict` defines.

### Did each behave as §5.6 intends?

- **Implementer: yes.** It argued rather than "fixing" a non-existent problem, and it did
  not commit a cosmetic change to look cooperative. Capitulation — the failure mode that
  would make the whole phase worthless — did not occur on this datum.
- **Critic: yes.** It withdrew when shown a correct argument, citing the line it had got
  wrong. Withdraw rate on the first datum: **1/1.** One blatant case; it says nothing yet
  about a *plausible* wrong finding, which is the harder and more interesting case.

## The TRUE-blocker scenario — attempted twice, not run

Two further implement turns were bought to obtain code with a genuine defect to file a
true blocker against. Both produced code that is correct against its spec, so **no true
blocker could be filed without lying**, and the scenario was abandoned rather than faked.

1. `truncate(text, limit)` — "ends in `...`, length exactly `limit`, `limit` may be
   smaller than 3". The implementer handled the sub-ellipsis case explicitly
   (`if limit <= len(_ELLIPSIS): return _ELLIPSIS[:limit]`). Verified exhaustively for
   `limit` 0..7: length always exactly right.
2. `money(amount)` — two decimals, halves away from zero. It reached for
   `Decimal(str(amount)).quantize(..., ROUND_HALF_UP)`, i.e. it avoided the
   `round()` banker's-rounding trap the spec was chosen for. All spec examples pass,
   `-0.125 → -0.13` included.

So the following remain **unverified live**, exactly as `rebut-report.md` listed them:
a rebuttal that fixes and commits; `head_moved` true after a rebuttal; the real gate
re-run after a fix (`rerun_gates` was a stub returning `None` in this run — the callback
was invoked, the suite was not); `EXHAUSTED` after a red re-run; a critic *confirming*
against a fix; and the "claims a fix, commits nothing" case, which cannot be induced
without tuning the prompt into producing it.

## Defects the run exposed

**In `rebut.py`: none.** The two-turn shape produced a schema-valid block on the first
try; `_Rebuttals` and `_Verdicts` both validated; the asked-vs-given verdict check
passed; `rebut_state` returned the right state and the right line; cost summed
correctly across three turns.

Smaller things observed, all outside REBUT proper:

1. **Blockers are numbered from 0.** `blocker_lines` uses bare `enumerate`, so the
   implementer and critic are asked about "finding 0". Both handled it, and the round
   trip is consistent, but a one-based list is what a human reading `rebuttal.json`
   expects. Cosmetic; not changed, since changing prompt-visible text mid-experiment is
   the tuning this run was told not to do.
2. **First-turn behaviour under `implement.md` is not deterministic.** With the same
   system prompt and a turn prompt saying "implement this now and commit", two sessions
   emitted a plan `<output>` block and did nothing else, and one implemented and
   committed directly. `session.py` always sends `PLAN_PROMPT` first, so this never
   arises in the real driver — but it costs a wasted turn (~$0.11–0.12) for anyone
   driving a session by hand, and it means the plan-first instruction in the prompt file
   is not load-bearing on its own.
3. **Harness-level, worth knowing:** a cell started without `ANTHROPIC_API_KEY` in its
   env fails as `subtype=success` / `terminal_reason=api_error` / `is_error=true` with
   `Not logged in · Please run /login`, and `run_agent` correctly raised `AgentFailed`
   for it at zero cost. That confirms the `is_error` predicate comment in `implement.py`
   against the live runtime.

## Live cost figures (§7.1 has no REBUT row)

| Turn | Cost |
|---|---|
| Plan turn (scenario 1) | $0.1219 |
| Implement turn (scenario 1) | $0.1432 |
| **REBUT: rebuttal turn** | **$0.0389** |
| **REBUT: extraction turn** | **$0.0234** |
| **REBUT: verdict session (1 lens, 1 blocker)** | **$0.1053** |
| Implement turn (scenario 2, truncate) | $0.1272 |
| Plan turn (scenario 3, money) | $0.1089 |
| Implement turn (scenario 3, money) | $0.1294 |
| **Total** | **$0.7982** |

REBUT on one blocker and one lens costs about **$0.17**, roughly one implement turn. The
verdict session is two-thirds of it: it is a fresh session paying full context for the
vocabulary, the spec and the diff, while the rebuttal turn resumes and pays almost
nothing.

## Cleanup

Cell container, worktree volume, state volume, per-run network and proxy all removed;
`container ls -a`, `volume list` and `network list` show only the pre-existing buildkit
container and the reusable `saffron-egress` network. Scratch repo and mirror deleted.
