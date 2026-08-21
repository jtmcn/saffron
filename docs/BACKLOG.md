# Backlog — what v0.5 left, and why each thing matters

Written at the close of v0.5 (`DESIGN.md` rev 14). Every item here is a gap a
live run exposed or a decision deliberately deferred — none is speculation about
what might be nice. Each says what "done" looks like, so it can be picked up
cold.

Ordered by what would hurt most on the first unattended night.

**Where the evidence lives.** `DESIGN.md` Appendices I–L narrate what building
and running v0.5 found. The per-task briefs and implementation reports were
written under `.superpowers/`, which is gitignored and does **not** survive a
merge — anything from them worth keeping was moved into the appendices or into
`docs/superpowers/plans/2026-08-19-v0.5-findings.md` before this was written.

---

## 1. `integrity` must be rewritten, not merely wired

**Status:** written by the factory, reviewed, **rejected**. The patch is in the
batch tree, not in the repo.

`SA-0004` produced a 371-line `integrity` gate that passed every gate and its own
31 tests, and adversarial review rejected it on three Criticals (Appendix K):

- `\ No newline at end of file` handled only *inside* a hunk, while git emits it
  after one — so any diff touching a file without a trailing newline returns
  `error`, and §5.4 turns that into an aborted attempt the agent is never told
  about.
- "an existing test was removed" inferred from **net line count**: delete the
  failing test, write a longer comment, and the gate is green. That is precisely
  the evasion the gate exists to stop.
- the same comparison fails a legitimate `parametrize` consolidation, so the only
  repair is padding the file — the gate teaching the gaming.

**Done looks like:** a gate that identifies removed *tests* rather than removed
*lines*, handles the marker git actually emits, honours §5.4's "unless `touches`
explicitly includes it" exemption, and is wired into `run_one_cell`'s suite
beside `scope`. The rejected patch and the review are worth reading first — most
of its structure is sound and the §2.1 split in it is clean.

**Why it is first:** principle 49 — a verification an agent can run itself is one
it will have already passed. The core gates are the only gates that can ever
fire, and this is the one that catches gaming.

## 2. The agent can disable a core gate from inside the cell

`worktree.export_patch` runs bare `git diff`, inheriting worktree config the
agent can write. One `git config diff.srcPrefix x/` and a diff deleting the
entire test suite reads as `pass`, because path matching no longer recognises
anything.

**Done looks like:** `export_patch` pins `--src-prefix=a/ --dst-prefix=b/
--no-ext-diff`, and any core gate reading a diff refuses a prefix it does not
recognise rather than silently passing. A test that sets the hostile config and
asserts the gate does not report `pass`.

**Done, 2026-08-20.** `worktree.DIFF_FLAGS` pins prefixes, `--no-ext-diff`,
`--no-textconv` and `--no-renames` on every diff the host reads, and `_git` adds
`-c core.quotePath=false`; a command-line flag beats repo-local `.git/config`,
measured on git 2.50 (including config reached through `include.path`).
`scope_gate` is handed that diff and reports `error` — infrastructure, charged to
nobody — when the headers are not `a/ b/`. Two things the review's account got
slightly wrong, both measured: `--name-only`, which is what `scope` actually
consumed, was never bent by `diff.srcPrefix` (the `pass` was the rejected
`integrity` gate's, which parses hunks); and `diff.external` and a textconv
driver are the sharper knobs — either can empty a diff entirely. Still open: a
`-diff` attribute renders a text file as `Binary files ... differ`, which hides
*content* but never a path, so `scope` is unaffected and the future `integrity`
gate must treat such a section as unreadable rather than as no change.

## 3. `findings` and `attempts` have no tables

`DESIGN.md` §4.1 declares both. Neither exists, so:

- REVIEW's findings and REBUT's verdicts and rebuttals live in `rebuttal.json`
  in the batch tree. §4.1 is explicit that `verdict`, `adjudication` and
  `rebuttal` are three distinct columns that must not collapse — they are three
  distinct JSON keys instead, which is the right shape in the wrong place.
- every attempt's gate results share one `attempt_id`, so "which attempt produced
  this failure?" has no join to stand on — the question §5.4's no-progress rule
  and §8's flywheel both assume is answerable.
- `tasks.spent_usd_est` does not exist, so a run ends with no persisted record of
  what it cost. Fine while an operator is watching; not fine for §4.2's budget
  gate.

`SA-0003` produced an `attempts` implementation, unreviewed, in the batch tree —
its patch no longer applies (see item 9).

**Done looks like:** both tables, the drop-rate-per-lens query answerable in SQL,
and cost on the task row.

## 4. Three of five supervisor bounds are missing

§4.3 wants turns, spend, idle, completion and wall clock. v0.5 has turns, spend
(host-side, per task) and a wall clock on `exec_stream`. **Idle and completion do
not exist**, and the wall clock defaults to 3600s that `run_one_cell` never
overrides — so an "attended" operator can watch nothing happen for an hour.

§4.3 is emphatic that splitting idle from completion matters: silence *before* an
agent claims to be done is a stall, silence *after* is a lingering child process,
and collapsing them makes a finished agent burn the full idle timeout and then
read as a failure.

**Done looks like:** all five, and a default wall clock an operator would
actually sit through.

## 5. PACKAGE, and the fact that patches perish

There is no PR, no push, no index. A green run leaves `patch.diff` and
`patch.json` in the batch tree and nothing tells you they are there — finding one
requires knowing the layout by heart.

Worse, they decay: `SA-0003`'s patch no longer applies, because three hours of
commits moved `session.py` underneath it. A verified-green change has a shelf
life measured against the branch it was cut from.

**Done looks like:** §5.7's PACKAGE — rebase onto current `main`, re-run the full
suite on the merged result, push with `--force-with-lease` pinned to the checked
SHA, open the PR with the body §5.7 describes — and §6's index. Until then a
patch older than its base is a patch nobody can use.

## 6. The critic's lenses overlap, and the third does not exist

Measured on the critic's first live run (Appendix L): **both lenses filed the
same `touches` finding.** §5.5's no-voting rule rests on lenses being disjoint by
construction — *"the schema critic will never independently corroborate the
correctness critic's timezone finding"* — so an overlap is a prompt defect, not a
duplicate to deduplicate. Principle 51: two lenses reaching one finding is a fact
about the prompts, and it reads as corroboration, which is what makes it
dangerous.

Lens 3 (blast radius) is not built because no risk tier is wired into
`run_one_cell`. It is the lens that would have caught item 2 — the review found
the `srcPrefix` escape and the critic did not, because it lives in `session.py`
rather than in the diff.

**Done looks like:** remits that do not overlap, a risk tier on the task, and the
third lens at `elevated`.

## 7. `CLAUDE.md` no longer reaches the agent, so the flywheel's middle bucket is inert

`setting_sources: []` was set because a target repo's `.claude/` was configuring
the agent working on it — measured, a planted subagent and skill both loaded out
of `/work` (Appendix J). The fix is right and it has a cost: the repo's
`CLAUDE.md` stops loading too, and that is §2.1's named learning surface and
**bucket 2 of §8's entire flywheel.**

**Done looks like:** `CLAUDE.md` injected host-side from the mirror, the way
`CONTEXT.md` already is — which is the better shape anyway, since a file under
`/work` is rewritable mid-attempt.

## 8. N1 rests on seven guessed ports

`preflight.PROBED_PORTS` is `5432, 5433, 3306, 6379, 8000, 8080, 27017`. The
probe raises rather than passing when it cannot run, which is right — but "no
host service answered on seven ports I thought of" and "no host service is
reachable" are different claims, and the code and `DESIGN.md` both currently make
the second.

This was not hypothetical: the host service that *was* exposed sat on 8000 and
was caught, while four more on 8001+ would have been invisible.

**Done looks like:** enumerate the host's actual wildcard-bound listeners and
probe those.

## 9. Unverified against a live model

Everything here is built and unit-tested and has never met a real session. On
this project's evidence that is exactly where the next defect is.

- **GATE ⇄ REPAIR has never fired.** Three live tasks, three greens on attempt
  one, because a capable agent with `Bash` runs every gate it can reach before
  committing (principle 49). Repair's real domain is only the core gates.
- **A critic confirming** rather than withdrawing. The one live REBUT saw a
  blatantly false blocker withdrawn; a plausible-but-wrong finding is untested,
  and that is the kind that costs mornings.
- **A rebuttal that fixes and commits**, with `head_moved` true.
- **The gate re-run after a rebuttal**, and `EXHAUSTED` when it is red.
- **A rebuttal that claims a fix and does neither** — §4.3's doneness rule at the
  point an agent has the strongest incentive to claim it is done.

## 10. Small, measured, cheap

- `rebut.py` numbers blockers from 0 in the prompt.
- `implement.md` is non-deterministic on the first turn — 2 of 3 live sessions
  emitted a plan block when told to implement. Harmless today because
  `session.py` always sends `PLAN_PROMPT` first, but the template is doing double
  duty.
- `uv run` inside a cell rebuilds and reinstalls the project on every invocation,
  and would fail outright if it ever needed the network — the proxy allows one
  host. Agents work around it with `python -m`, at the cost of a turn.
- `image_exists` was deleted as dead; if PACKAGE wants a stale-image check it
  comes back.

---

## What is *not* here, deliberately

DIAGNOSE and `SCOPE_REVIEW`, the scheduler's conflict sets and stacking, `saffron
gc`, multi-repo, the merge train, and the `size`/`secrets`/`revert` gates. All are
v1+ by `DESIGN.md` §9's own build order, and none of them is blocked by anything
above. §4.2's own argument applies: at a two-deep queue they arbitrate contention
that never arrives.
