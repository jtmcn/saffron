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

## 1. `integrity` needs splitting, not rewriting — and half of it may not be a core gate

**Status:** **done**, by hand, in PR #6 (merge `596f96f`) — not by the factory
patch this item was written about. That patch was reviewed and **rejected**, and
stayed in the batch tree; what shipped keeps its §2.1 split and its suppression
detection and replaces the rest. Nothing below needs picking up. Read it for
what the shipped gate is answering and why, not as work outstanding.

`SA-0004` produced a 371-line `integrity` gate that passed every gate and its own
31 tests, and adversarial review rejected it (Appendix K). The three Criticals
collapse into **two defects**, and they want different treatment.

### Defect A — a positioning bug. Fix it.

`\ No newline at end of file` is handled only *inside* a hunk, while git emits it
after one. So any diff touching a file without a trailing newline returns
`error`, which §5.4 turns into an aborted attempt the agent is never told about.
The branch exists; it is in the wrong place and untested.

### Defect B — the central heuristic is the wrong shape. Replace it.

"An existing test was removed" is inferred from **net line count**. Delete the
failing test, write a comment longer than the test, and the gate is green — the
exact evasion it exists to stop. The same comparison fails a legitimate
`parametrize` consolidation, so the only repair is padding the file, which
teaches the gaming. Wrong in both directions on one comparison is not a check.

**And the obvious replacement may not be possible in a core gate.** "What is a
test" beyond a path glob is language knowledge, and §2.1 keeps that out of core.
A better-shaped answer already exists in the contract: §5.4 requires the `tests`
gate to accept a **test-subset argument**, so the repo can already enumerate its
tests. If it reported the *collected test names*, comparing the set at `base_sha`
against the set at head answers the question **exactly** — no false positive on a
consolidation, no evasion by padding, and it catches a test silenced by renaming
out of collection, which the rejected gate blesses (verified in review).

The cost is that this half stops being diff-only, so it needs the `revert`-shaped
exception §2.1 already sanctions: *core invokes declared gates, never tools*.

**This is a design decision and belongs in `DESIGN.md` before any code.** §5.4's
`integrity` paragraph currently describes a single diff-reading gate; if test
removal moves to set comparison, that paragraph and the gate-role table change,
and the contract gains a requirement on what `tests` reports.

### What to keep

The review was explicit about what is good, and it is most of the file: the §2.1
split (not one language token in a code path), `error` vs `fail` not blurred,
count-driven hunk consumption with a fixture containing diff-shaped content,
line numbers derived from the `@@` header, and **suppression detection that is
correct** — added lines only, with the context-line and removed-line cases both
tested and right. The `gate_config` check is right too.

### Done looks like

- Suppression and gate-config checks surviving as a diff-reading core gate,
  with defect A fixed and §5.4's "unless `touches` explicitly includes it"
  exemption honoured — the rejected gate omitted it and so failed its own PR
  with sixteen violations.
- Test removal answered by comparing collected test sets, with `DESIGN.md`
  updated first to say so.
- Both wired into `run_one_cell`'s suite beside `scope`.
- A `-diff` gitattribute renders a text file as `Binary files ... differ`; that
  hides content but not paths, so `scope` is safe and this gate must treat such
  a section as unreadable rather than as no change (see item 2).

### Why it is first

Principle 49: a verification an agent can run itself is one it will have already
passed, so the core gates are the only gates that can ever fire.

Note the justification in §5.4 — that a hard-gate *repair loop* trains toward
test destruction — is not the reason this matters here, because the repair loop
has never fired (item 9). The reason is simpler and stronger: **`integrity` reads
the diff and does not care why the diff looks that way.** An agent that runs its
own tests, finds one hard to fix, and deletes it before ever committing produces
exactly the same diff as one that deleted it under repair. The gaming pressure
moved earlier in the process, not away — which makes this the only place that
deletion is visible at all.

**Done, 2026-08-22.** Split, and three of this item's own claims were wrong —
measured, not re-reasoned (`docs/evidence/2026-08-22-integrity-rejected-gate-measured.md`,
Appendix M). The batch tree holds a **post-rebuttal** patch, one fix past the one
Appendix K reviewed. Defect A was already fixed in it: all four positions git
emits `\ No newline at end of file` parse cleanly, so there was nothing to move
and nothing to test. The removal check was run adjacency, not net line count, so
the `parametrize` false positive was already gone — while the evasion was
*cheaper* than this item says, taking one adjacent added line of any content
rather than a comment longer than the test. And a defect nothing had recorded:
the suppression scan substring-matches every added line in every file, so
`d1141d0` — this repository's own merge of PR #5 — fails `integrity` on two
docstrings that quote `@pytest.mark.skip` while explaining that a critic's claim
quotes it.

What shipped: `integrity` keeps the two checks a diff can answer — added
suppressions, and gate-config edits — and treats a `Binary files ... differ`
section as unreadable rather than unchanged. Test removal became `census`, a set
comparison of collected test names, which also catches a test renamed out of
collection: the case every diff-shaped version blessed. **It needed no §2.1
exception.** This item assumed core would have to invoke the `tests` gate the way
`revert` does; it does not, because the baseline and head suites already run
`tests`, so the names needed reporting rather than fetching. The contract gained
one optional field, `collected`, and core subtracts two lists it already holds.

**The `touches` exemption binds `gate_config` alone.** The first design exempted
suppressions too, and review killed it: `scope` already requires every changed
file to be inside `touches`, so a per-file exemption fires on every file of any
diff that can reach green. Measured — a failing test silenced with
`@pytest.mark.skip`, its file named in `touches`, went green on `scope`,
`integrity`, `census` and `tests`. A file-level key cannot exempt a line-level
check without nullifying it. The cost of not exempting suppressions is that prose
quoting a token fails; that is accepted, because a `fail` reaches the repair loop
naming file, line and token, while a gate that never fires reports nothing.

**The cost is measured, not estimated — and re-measured whenever this paragraph
changes.** Against this branch's own diff (`d1141d0..HEAD`) with the real
`.saffron/policy.yaml`, `integrity` reports **71** failures across **11** files —
69 `added-suppression` plus 2 `gate-config-changed` — where
`d1141d0` itself produced 2. Almost all of it is this work's own prose about the
tokens the policy declares: 23 in the plan, 17 in `tests/test_integrity.py`, 7 in
`DESIGN.md`, 6 in the spec, 5 in the policy file, the rest in this file and the
evidence files. **The count is self-referential** — prose quoting a token is
counted, so the first two recordings of it went stale in the commit that made
them, by quoting the tokens they were counting. Describe them, never reproduce
them. A task whose `touches` names those paths is exempt, so this bites only a
task editing a prose file it did not declare. If it starts biting, the relief is a `prose_paths`
key in `integrity` — paths whose *added lines* are not scanned, distinct from
`touches`, which exempts the whole file — not a weaker token list.

**Three defects found by executing the work rather than reading it**, each closed:

- **One byte hid a suppression.** Git splits diff lines only on `\n`; Python's
  `str.splitlines()` splits on nine more characters. Git emits them raw inside a
  `+` line, so one added line shattered into fragments and a fragment beginning
  with a space was filed as a *context* line, which the suppression scan skips.
  Measured end to end: `import os\x0c  # noqa: F401` parses as valid Python,
  `ruff` honours the `noqa`, and `integrity` returned `pass`. The repo's lint gate
  obeyed a suppression the anti-gaming gate could not see.
- **The same line lived in `scope`.** `scope_gate` read the diff with
  `splitlines()` too, so the same injection reached it. Fixed with `integrity`
  rather than left one file away.
- **The evasion also lived one layer up, at the capture boundary.** `runtime._call`
  captured with `subprocess.run(text=True)`, whose universal-newline translation
  rewrites a bare `\r` to `\n` *before any gate executes* — so the line arrived
  already shattered and no parser fix could undo it. It now captures bytes and
  decodes explicitly. That also removed a latent crash: the old text mode decoded
  with the **host locale** under `errors="strict"`, so a non-UTF-8 byte from a
  cell could raise `UnicodeDecodeError` out of `_call`.

Still open, deliberately: a task that *legitimately* removes a test cannot pass,
since no exemption binds `census`. The upgrade path is a spec field, left unbuilt
until a task needs it. A genuine binary fixture inside `touches` trips
`integrity`'s unreadable-section rule — and the same rule is a **deterministic
route out of a red run**: committing a `.gitattributes` carrying `*.py -diff`
renders every Python file as `Binary files ... differ`, so a file inside `touches`
turns `integrity` into `error`, which `aborted_gates` reports as `GATE_ERROR` —
infrastructure, charged to nobody. An agent facing a failing run can reach that
on purpose. The vector is new to this split; the pre-split gate had no binary
handling at all. Closing it is a `--numstat` cross-check (a file git reports
non-zero added lines for cannot legitimately be unreadable), which is a design
change and not this branch's. And `exec_stream`, `LocalExecutor` and
`package.py` still capture with `text=True` — harmless today, since none of them
reads a diff that a gate judges, but they are the remaining siblings of the
boundary this work fixed. All carry `ponytail:` comments or a line here.

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

**And `size` inherits it, 2026-08-25.** Measured on `SA-0002`'s gate: a block
with no `@@` contributes 0, so `*.py -diff` in `.gitattributes` makes a
2000-line rewrite count as 1 and pass — at `elevated`, the one tier where
`size` blocks. It carries a `ponytail:` comment naming the ceiling rather than
a fix, because the honest response is `error` only when the unreadable file is
inside `touches`, as `integrity` already does, and `size_gate` is handed
neither `touches` nor a `--numstat` cross-check. **The wiring spec has both and
should close it**, which makes that spec's second reason to exist.

**Closed at the tier that blocks; corrected 2026-08-25 (#27).** `size_gate` is
handed `touches` and returns `error` when an unreadable block names a declared
path (`_unreadable_declared_path`, `saffron/gates/core/size.py:101`) — reusing
`scope.matches`, so "declared" means one thing in every gate. The paragraph
above stood as outstanding work after the work had shipped, which is the shape
#26 found on item 17: a stamp read as a plan.

**Two residuals, and the first was nearly lost to the correction above.** The
guard is `if unreadable is not None and blocking` (`size.py:162`), so at
`standard` an unreadable declared path still counts as zero lines silently.
That is the right scope — the original complaint was about `elevated`, the one
tier where `size` blocks — but it is a narrower closure than "closed", and an
advisory gate that under-reports is still a gate reporting something false.
The `--numstat` cross-check remains an upgrade path in the docstring rather
than shipped code.

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

**Done, 2026-08-23.** All three, by hand; `SA-0003`'s stale patch was not
reopened, and two review rounds followed. What is worth carrying forward, in the
order it was learned:

**The column had no `REFERENCES`, and that is what made the convention
possible.** `gate_results.attempt_id` was a bare `INTEGER`, so holding a
`task_id` in it was not a shortcut the schema tolerated — it was one the schema
could not see. It points at `attempts(attempt_id)` now, and the old convention
is unrepresentable rather than merely discouraged — though that took two more
commits than the schema line, and this paragraph claimed it a round early
(below). Two existing ledger tests asserted it directly and had to change;
`SA-0003`'s "every existing test still passes unchanged" was written before it
was clear that two of them encoded the defect.

**Attempts are opened by wrapping the agent callable, not at the call sites.**
`record_attempts` sits inside `stop_on_rejected`, so a turn the provider walled
records its cost before the rate limit is raised. The consequence is the reason
for the shape: the lens sessions inside `review.run_review` and the rebuttal and
verdict turns inside `rebut.run_rebut` all get rows without either phase
learning what a ledger is — they still take an `agent` and nothing else. A
turn that fails is still recorded; one that raises something neither layer
expects leaves its row open, which is an honest reading of what happened.

**`phase` is the state the task is in, and `spent_usd_est` is derived.**
`open_attempt` reads `tasks.state` rather than taking a phase, because the
caller already sets it at every phase boundary and tracking it twice is how the
two drift. `set_task_state` rolls the spend up from `attempts` in the same
statement, so the figure cannot disagree with the rows it is made of and no
terminal path can forget it — there are seven of them. The equality between
`tasks.spent_usd_est` and `CellOutcome.spent_usd` is asserted, because it is
what proves no spending turn is missing a row.

**`SA-0003` deferred `spent_usd_est` on a question that was already answered.**
It said the sum depends on "whether a resumed session reports per-turn or
whole-session cost, which is not yet known". `session.py` had since measured it
— $0.00396 fresh, $0.00199 on resume of the same `session_id`, so summing is
correct and cumulative would never fall. The deferral outlived its reason.

**Review found the migration, and the obvious repair is illegal.** A ledger
written before `attempts` existed holds a *task_id* in `gate_results.attempt_id`
— and a new attempt's id starts at 1 in that same integer namespace, so task 1's
v0.5 results reattach to whichever attempt draws id 1. Reproduced on a copy of
this machine's own `~/.saffron/ledger.db`, which is exactly such a ledger.
Nulling the legacy values out is not available: the `CHECK` that keeps exactly
one of `attempt_id` and `run_id` set rejects a row with neither, on `UPDATE` as
much as on insert. What shipped was the backfill the old schema comment promised
— one attempt row per legacy value, carrying that value as its own id, so the
ids stay taken and nothing is lost or moved. Measured on that copy: five
backfilled, zero dangling, every task still holding its own results.

**And the backfill protected the data without delivering the constraint.** A
second review round found the paragraph above true only of a ledger created from
scratch: `CREATE TABLE IF NOT EXISTS` is a no-op on an existing `gate_results`,
and SQLite has no `ADD CONSTRAINT`, so on an upgraded ledger the column still
read `attempt_id INTEGER` and a dangling `attempt_id` inserted silently. The
test that was supposed to prove otherwise passed because its fixture builds a
fresh file — the same shape of gap as the one this item exists to end, one level
up: a check that reads as enforcement and is a convention. What ships now is
SQLite's documented 12-step rebuild, after the backfill so every copied row
already has an attempt to point at, `foreign_keys` off across it because
`failures` references `gate_results`, which does not exist between the DROP and
the RENAME.

Dangling rows are copied in rather than refused. SQLite checks a reference when
a row is written, not when it is rebuilt, so a `PRAGMA foreign_key_check` gate
here is theatre: the rebuild has already committed by the time it runs, and the
next open takes the early-return path and lets the row through anyway. The
constraint governs what can be recorded from here on, which is what made the
collision possible. Measured on the copy again: 49 gate results, 12 failures,
5 tasks and 5 runs identical across the migration, a dangling write rejected.
The rewrite happens on first open, so the ledger is worth copying aside before
the next run.

**Two more from that round, both in what the ledger is told.** `task_spend`
selected `tasks.spent_usd_est`, which only `set_task_state` refreshes — correct
only when a state change happened to precede it, which today's one caller
arranges and a read from inside the repair loop would not. It sums `attempts`
now; the column stays, because it is what `queue_lines` reports without a join.
And the rebuttal write was lossy twice: `run_verdict` rejects a verdict set that
is not exactly its own blockers, but nothing validates the *rebuttal* turn's
numbering, so two entries for blocker 1 and none for blocker 2 left blocker 2
reading as unanswered against an artifact that says otherwise. Validated at the
write now. `Rebuttal.action` was dropped outright, which made a claimed fix and
an argument indistinguishable in `findings.rebuttal` — the distinction §4.6's
critic-ROI query is the whole reason for the column.

Two smaller ones from the same review. `open_attempt` against a task that does
not exist selected nothing and still returned `lastrowid` — an id that exists,
belongs to another attempt, and satisfies the foreign key; silent
misattribution, which is the failure this item exists to end. And `RATE_LIMITED`
was the one exit where the ledger and `CellOutcome` disagreed: the raise comes
from outside the turn, so it lands past the `spent +=`. The outcome reads the
attempts back now, which also closes the older gap where a window closing inside
`plan_checkpoint` lost the whole tally with its frame.

Still open, by choice: `findings.adjudication` has no producer — it is the
operator's, and the morning queue (§6) is where it comes from. `attempts.model`
is declared and never written: the runner's `result` event does not carry it and
only assistant messages do, so recording it means changing the event schema.
`batches` and `decisions` remain the two tables of the ten with nothing to put
in them.

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

**Done, 2026-08-20.** All five. `exec_stream` reads through a queue fed by a
reader thread, so every wait carries a deadline: `idle_s` (300s) before the
payload signals done, `completion_s` (10s) after it, and `timeout_s` for a turn
that keeps producing and never stops. `session.TURN_TIMEOUT_S` is 900s and is
bound onto the agent callable once, so plan, implement, repair, review and
rebuttal all carry it rather than inheriting the library's hour.

The split is load-bearing and is what the returned value now records.
`Completed.bound` names which bound fired; an idle or wall-clock expiry kills
and reports 124, a **completion window close reports 0 and is a success** — the
runner emitted its result and only a child was holding stdout open. `run_agent`
propagates it as `AttemptResult.bound` and its failure message names the bound
instead of saying "timed out" for all three. The done signal comes from
`run_agent` returning true out of `on_line`, not from the runtime parsing
events: the container seam does not know Saffron's schema.

Threads over `selectors`, measured against the alternative rather than
preferred: readiness on the fd is not a line, so a half-written one still
blocks `readline` and the fix is reimplementing line splitting over `os.read`.

**Amended 2026-08-21: one of the five was not bounding, and a bound firing
kills less than it looks like.** Two defects in the above, both measured.

The completion window was recomputed as `now + completion_s` at the top of
every loop iteration, and the `signalled` branch short-circuits the wall clock
— so every line a child wrote pushed the deadline out again and nothing else
applied. A child writing steadily after the result event held `exec_stream`
open forever: an unbounded wait, inside the function whose five bounds exist so
that no wait is unbounded. The window is now fixed once, when the result event
lands, and a chatty child cannot move it.

And the kill does not reach the cell. Measured against a real `container` — a
detached container, a long `container exec`, `proc.kill()` on the host side,
then a look at `/proc` from inside — the process is still there. Killing the
exec client kills the client. So an idle or wall kill left the agent running in
the cell while the driver went on to measure `commits_ahead`, run the whole
gate suite and resume the session, all in that same container, with an
abandoned agent still able to edit `/work` and commit underneath every one of
them. `runtime.reap_cell` now kills everything but PID 1 on those two bounds —
never on the completion window, which is a turn that finished. Measured again
after: the abandoned process is gone, `sleep infinity` survives, and the cell
still takes the next exec.

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

**Done, 2026-08-22** (PR #5). All of it, and the re-run is conditional: if the
fetched default-branch head still equals `base_sha` the packaged tree is
byte-identical to the one the suite already ran on, so re-verification is
*provably* redundant and the body says it was skipped and why. Otherwise the
suite re-runs in a gate-only cell — never host-side, because the applied tree
carries `.saffron/gates/*` exactly as the patch left them (§2). The base having
moved also invalidates the old baseline, so that cell runs the suite twice and
subtracts, which is §4.4 steps 2-3 applied to one commit.

Three things the build measured rather than reasoned, all now in §5.7. A
conflicting `git apply --3way` exits 1 **and still writes the file**, markers
staged — "apply failed" and "nothing happened" are different states. A degraded
apply exits **0**: preimage blob absent, context matching, and git falls back to
direct application, so conflict detection silently becomes a context match. And
`git commit` in a `--mirror` clone with no identity does not abort — it
auto-detects from the OS and attributes machine-written commits to the operator,
so `commit_squash` passes `-c user.email=saffron@localhost` on the command line.

`repos.origin` now holds the real remote; since v0 it held the mirror's *source*,
a local path, so nothing downstream knew where a pull request would go (§4.1).

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

**Amended 2026-08-25 by `SA-0002`, and the amendment changes what lens 3 should
be.** The overlap did not recur: correctness filed the counting blocker,
contract filed a `tool` concern, disjoint by construction on a second live diff.
One run is not proof the prompts are fixed, but it is evidence the remits hold.

The sharper finding is what *both* lenses missed. A later review of the same
97-line diff found two mediums neither lens raised. One was a `-diff`
gitattribute zeroing the count — the escape route item 2 leaves open, arriving
in a new gate. The other was that the multi-file header reset had **no test**:
deleting the line left all sixteen tests passing while a two-file diff
overcounted by two lines per file. That second one is the same class as the
blocker correctness *did* catch — a header-collision bug in `_changed_lines` —
found one level up, in whether the suite would notice a regression.

So the gap the third lens should close is not blast radius. **No lens asks
whether the tests would catch the code being wrong**, and a critic that reads
the diff without mutating it cannot: the implementer's own tests passed, the
gates were green, and the line was invisible to every one of them.

**Corrected 2026-08-25 by #33: the line is not uncovered, and the word mattered.**
Measured twice independently — `saffron/gates/core/size.py` reports **100%
statement and 100% branch coverage** from its own tests, and the reset line is
executed by every one of them. The defect is an *executed line whose effect
nothing observes*, which is the one class coverage cannot report by
construction. The wrong word had a cost: it made diff-scoped coverage look like
a cheap answer to this remit, and #33 was written to price an option that was
never available. See `docs/evidence/2026-08-25-mutation-testing-vs-a-lens.md`.

**And `DESIGN.md` §5.5 says the opposite of this item, which is #34's to
settle.** `DESIGN.md:782`: *"lens #3 in a naive design would be 'test quality' —
but the `revert` gate now answers that mechanically and for free."* Neither
document cites the other. The displacement is also incomplete (reasoned, not
measured): `revert` stashes the source hunks and requires the new tests to fail,
but `SA-0002` landed source and tests together, so stashing the source fails all
sixteen and `revert` reports green without ever asking whether the reset line
specifically is tested. `revert` asks whether the new tests test *anything*;
this remit asks whether they test *each thing*.
§5.5's disjointness argument still holds — this is a third remit, not a second
opinion on the first two.

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

**Done, 2026-08-20.** `preflight.host_listening_ports()` parses `lsof -nP -iTCP
-sTCP:LISTEN` and probes every listener not bound to loopback — a superset of
wildcard, because a service bound to the LAN address is reachable from a cell
too. Enumeration that cannot run raises; only lsof's own listing counts as
having run, so a listing with nothing but loopback rows is the real empty and a
silent lsof is not. Measured consequence on the machine v0.5 ran on: four macOS
services answer from inside a cell (ARD 3283, Control Centre 5000/7000, rapportd
49152), none of them in the old seven, so `preflight` now fails there until they
are turned off. That is the probe working.

**Amended 2026-08-21: one of the four is now tolerated, by name.** Three of
those services were turned off; `rapportd` remains, holding `*:49152` whatever
Continuity's settings say, and AirDrop going back on will reopen the two ports
it closed. So the probe was refusing to start a cell, permanently, for a daemon
the operator has accepted. `SAFFRON_ALLOW_HOST_PROCESS=rapportd` tolerates it
for that invocation: empty by default, matched by the COMMAND `lsof` reports
rather than by port (rapportd's ports are dynamic — 49152, 60215, 60216 all
seen), and a port drops out only when every listener on it is tolerated. The
preflight line names what was tolerated on every run, because an exception that
goes quiet is the hazard the probe exists for. Enumeration that cannot run
still raises. **This is an accepted risk, not a fix** — an agent in a cell can
reach that socket, and `DESIGN.md` Appendix G says so and says what it costs.
Renamed with it: `host_listening_ports()` → `host_probe_ports()`, which now
returns the ports probed *and* the listeners tolerated.

**Also 2026-08-21.** The probe enumerated a second time inside
`probe_host_bindings`, so the port list the operator was shown at the top of
preflight was not necessarily the one checked; it now takes that list as an
argument. It also connected serially at 1.5s per address-port pair, which puts
roughly a hundred listeners over the 300s cap — preflight failing for having
too much to check, and reporting it as a probe that did not run. The connects
go through a thread pool now; the timeout stays generous.

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

**Half met, 2026-08-25**, by `SA-0002` — the first task to run the whole
pipeline, spec to pull request (#15), $2.38 against an $8 budget, green on
attempt one.

**Two of the five fired, and the pair that fired is the pair that matters
most.** The correctness lens filed a true blocker: `_changed_lines` dropped any
hunk line *starting with* `---`/`+++`, so a SQL `-- comment` or a YAML `---`
undercounted the diff. The implementer fixed it, committed, `head_moved` true;
the gates re-ran clean on the new head; the lens withdrew its own finding on
the evidence. That is REVIEW ⇄ REBUT closing the loop against a real defect
rather than a planted one, which is what Appendix L could not show.

**Three are still open** and they are the expensive three: `EXHAUSTED` when the
post-rebuttal re-run is red, a rebuttal that claims a fix and does neither, and
a critic *confirming* a plausible-but-wrong finding. All three are failure
paths, and a green run cannot exercise them — which is the argument for a task
chosen to fail rather than for waiting.

**GATE ⇄ REPAIR did not fire, for the fourth time.** Four live tasks, four
greens on attempt one. This is no longer an accident to be waited out: an agent
with `Bash` runs every gate it can reach before committing, so the bullet above
is the standing behaviour and not a sampling artifact. Repair's domain is the
core gates the agent cannot run — `scope`, `committed`, `census` — and testing
it means a task that trips one of those, not a fifth hope.

**And the run measured two things nothing had.** The agent's `uv run pytest`
took four `403`s from the proxy and cost three turns (item 10, closed). And
five tests in this repo's own suite failed inside a cell while passing on the
host, so the baseline every gate result is subtracted from was carrying five
failures for reasons unrelated to any task (closed by PR #16). Both were
invisible to every unit test and to three prior live runs; both cost money on
the first task that reached PACKAGE.

## 10. Small, measured, cheap

- `rebut.py` numbers blockers from 0 in the prompt. **Done, 2026-08-21:**
  numbered from 1 in both places they are produced. Not cosmetic —
  `run_verdict` requires the verdict set to match the blockers exactly, so a
  critic answering "1." for the first of one blocker failed the check, and
  the phase discarded both lens sessions, both rebuttal turns and every
  verdict session over the numbering.
- `implement.md` is non-deterministic on the first turn — 2 of 3 live sessions
  emitted a plan block when told to implement. Harmless today because
  `session.py` always sends `PLAN_PROMPT` first, but the template is doing double
  duty.
- `uv run` inside a cell rebuilds and reinstalls the project on every invocation,
  and would fail outright if it ever needed the network — the proxy allows one
  host. Agents work around it with `python -m`, at the cost of a turn.
  **Done, 2026-08-24.** It does need the network, and the cost is three turns,
  not one: `SA-0002`'s implementer took four `403`s from the proxy on
  `pypi.org` before reaching `python3 -m pytest`. `UV_NO_SYNC=1` in
  `.saffron/Dockerfile` runs it out of the venv the image already baked. The
  general form is an onboarding requirement rather than a Saffron fix, and
  §5.1 now carries it: a repo's image pins its runner to the baked
  environment, because the workaround leaves the run green and bills the
  difference to the task.
- `image_exists` was deleted as dead; if PACKAGE wants a stale-image check it
  comes back.

---

## 11. What PACKAGE left, and the one design question it raised

Written at the close of sub-project A (PR #5). Every item was found by review or
by measurement during that build; none is speculation. The first is a design
decision, the rest are small.

### The base a task is cut from is the working copy's `HEAD`, not the default branch

`cli.py` sets `base_sha` from `git rev-parse HEAD` in the repo you invoked it in.
Run from a feature branch, `base_sha` is that branch's tip, so the fetched
default-branch head never equals it: re-verification fires on **every** package,
starting two containers and running two full suites, and the "provably redundant
skip" is only reachable from a checkout sitting exactly on an up-to-date default
branch. Worse, the patch is cut against a tree the default branch has never seen,
so `--3way` merges onto a base missing every commit the feature branch carries,
and a task touching a file the branch also touched conflicts — a `MERGE_FAILED`
that is an artifact of where the operator was standing.

**This is a design question, not a defect.** §5.7 is silent on where `base_sha`
comes from, and the scheduler (§4.2) will need an answer before it can start
tasks unattended. **Done looks like:** §5.7 saying whether a task's base is the
invoking checkout's `HEAD` or the remote's default branch, and the code agreeing.

### `github_slug` fails quiet on anything that is not a two-segment GitHub URL

Measured: `/Users/joel/Code/saffron` returns `Code/saffron`, and a GitLab-style
`group/owner/repo` returns `owner/repo` — the leading segment is dropped rather
than refused. Harmless for `github.com`, which is always two segments, but a
local-path origin is exactly what `session.py` falls back to, and a wrong slug
reaches `gh` as a repo that does not exist. **Done looks like:** a URL that is not
a recognisable forge remote raises rather than guessing.

### A pushed branch whose `gh pr create` failed is recorded nowhere but stdout

`_finish` runs after `open_draft_pr`, so a `gh` that is missing, unauthenticated,
or refused leaves the branch pushed and the ledger still reading
`READY_FOR_REVIEW` with no `branch` and no `pushed_sha`. A re-run self-heals — the
lease matches the branch it pushed — but the operator has to know that. **Done
looks like:** branch and pushed sha recorded before the pull request is opened,
and only the URL after.

### `reverify`'s cell does not get the repo's `thread_env`

The in-cell suite runs under `cell_env(proxy_ip, policy.thread_env)`; the
re-verification cell gets `env={}`. Empty for Saffron, so it changes nothing
today — but the two suites being subtracted are run under different environments
by construction, which is a suite-drift vector for the second repo onboarded
(§9's v2 is where that bites).

### Three test gaps, each one assertion

The pipe-escaping test covers only `_new_failures`, not the two tables added for
findings and disagreements — and a `|` is likelier in a model-authored `claim`
than in a gate message. `test_an_unanchored_finding_still_appears` checks the
claim renders but never that the row is marked `no`, which is the half that makes
drop rate visible (§5.5). And no test exercises `attempts`, `new_failures`,
`reviews` or `rebut_result` on `CellOutcome`'s success path.

### §5.7 says "rebase" and means `git apply --3way`

Step 1 says *rebase onto current `main`*; the v1 subsection describes applying one
squashed patch. Both are true — step 1 is the intent, the subsection is the
mechanism — but the document never says so, and a reader meeting them in order
will think one contradicts the other. One sentence, no renumbering.

### And one accepted risk, restated so it does not go quiet

The credential refusal keeps a secret off the *remote*, not off the *host*:
`patch.diff` and `pr_body.md` still sit in the batch tree with it in them.
`_CREDENTIAL_SHAPES` is a partial list under a `ponytail:` comment naming that
ceiling, and the real answer is §5.4's `secrets` gate, which is still v1's to
build.

**Done, 2026-08-23.** All six, and the design decision the first one asked for
is written down: `DESIGN.md` rev 16 — §5.1 for the fetch, §5.4 for the gate
source, §5.7 for the base, Appendix N for what building it found. A task's base
is now the head of the remote's default branch as of task start, so both ends of
the comparison read one source and the redundant-suite skip is reachable by
construction rather than from a checkout that happened to be standing in the
right place. Two things this item got wrong, both measured rather than
re-reasoned:

**`github_slug` was wrong on three of five real inputs, not on GitLab alone.** A
one-segment URL — `https://example.com/repo` — takes the **host** as the owner,
which this item does not name and which is the case where a wrong slug looks most
plausible. And the first fix was itself wrong, caught in review: a pattern
matching `github.com` after any of `^ @ / .` let `/Users/joel/go/src/github.com/owner/repo`
through, and twelve fixtures had by then been moved to a path shape that
satisfied it. Appendix N carries the 14-case table the shipped pattern is
measured against.

**The ledger defect is one column, not two.** `branch` was already written at
insert time by `create_task`, from `spec.branch`; only `pushed_sha` was missing,
written solely by `set_task_package` after `open_draft_pr`. What ships records
the pushed sha before the pull request is opened and the URL after.

`reverify` takes `dict(policy.thread_env)` rather than `cell_env(...)`: the
obvious route would have put `CLAUDE_CODE_OAUTH_TOKEN` into a gate-only cell with
no proxy and no egress. The three test gaps are closed, and §5.7 now says in one
sentence that step 1's "rebase" is the intent and `git apply --3way` the
mechanism. The accepted credential risk above is unchanged and still §5.4's
`secrets` gate to close.

---

## 12. `census` trusts the gate runner, and the gate runner is in the cell

Promised by the split's spec (part 2.3) and not written until the fix wave.
`census`'s subtraction is exact about the two lists it is handed, and both lists
are produced inside the untrusted cell — by `/work/.saffron/gates/tests.py` and a
second pytest process. CLAUDE.md's founding line is that every control that
matters lives outside the cell; this one does not. Two routes, both measured:

- **A `conftest.py` that lies to `--collect-only`.** A
  `pytest_collection_modifyitems` that drops a test only when
  `config.option.collectonly` is false makes enumeration report a name the run
  never executes. `census` passes because the name is still collected; `tests`
  passes because the test never ran. The removal is invisible to both.
- **Uncommitted edits are invisible to every diff-reading gate and fully
  effective on every gate result.** `worktree.export_patch` and
  `worktree.changed_files` both diff `base_sha..HEAD`, while `CellExecutor` execs
  gates against `/work` — the worktree. So **any** uncommitted change is absent
  from `scope`, from `integrity` and from the packaged patch, while being live
  for the suite. The spec names `/work/.saffron/gates/tests.py`, and the
  `.saffron/**` `gate_config` pattern closes only the committed case — but the
  hole is wider than one file: an uncommitted edit to any source file changes
  what the suite is measuring, and the reviewer reads a patch that does not
  contain it.

Neither route argues for the diff-shaped removal check this branch rejected: that
one was evadable by a single adjacent added line and needed no `conftest.py` at
all. The honest statement of what shipped is that **`census` buys exactness
against an honest suite, not integrity against a hostile one.**

**Done looks like:** a decision on the gate-runner trust boundary, which §5.4's
`no-network` gate and the gate contract both currently assume is cooperative. The
two candidate halves are independent: (a) gates run from a host-supplied copy of
`.saffron/gates/` rather than the one in `/work`, so an in-cell edit — committed
or not — cannot reach the runner; (b) the host refuses a dirty worktree at gate
time, or diffs `base_sha..worktree` so that an uncommitted edit is at least
*visible* to `scope` and `integrity`. Neither is v0.5's to build, and this item
exists so the choice is made deliberately rather than inherited.

**Done, 2026-08-23.** Both halves, which this item leaves as alternatives.
`.saffron/gates/` is exported from the mirror at `base_sha` and mounted read-only
at `/gates`, and the runner execs from there; a new core gate, `committed`, fails
the attempt when `git status` is not clean at gate time, one failure per path.
`DESIGN.md` rev 16 states the invariant both serve — anything that changes what
the suite measures must appear in the patch a human reads — and restates the
residual unchanged: a committed `conftest.py` still defeats `census`, and
`**/conftest.py` in this repo's `gate_config` routes that edit to a person rather
than failing it.

Two things this item does not contain, both worth more than the routes it names:

**Pinning the gates closes a baseline drift nothing had recorded, and that is the
stronger reason for doing it.** The baseline suite runs in the same cell and the
same worktree as head, before the agent starts, so the baseline ran the base
tree's gates and head ran whatever gates were in `/work` by then — a task editing
its own `tests` gate changed what the two subtracted sides mean. Suite drift by
construction, the same shape item 11 flags for `reverify`'s missing `thread_env`.

**`reverify` was a second copy of the same seam.** Its own cell, its own
`prepare_worktree`, its own `gate_executables(WORKTREE_MOUNT)`. Changing only
`session.py` would have left the two suites `reverify` subtracts coming from
different executables, and a required `gates_dir` would have broken PACKAGE at
runtime — invisible to `make check`, because the tests covering that path are
cell-marked and excluded by default. Found by review, not by running.

The dirty-tree half needed no new control flow: `committed` is a gate, so a dirty
tree gets the repair turn the loop already gives every `fail`, and a second
identical look ends the attempt on the no-progress rule.

---

## 13. Gate executables come from `base_sha`; the policy declaring them still comes from the working copy

The same asymmetry item 11 raised for a task's base, in a second place, left
half-closed by the fix that closed the first. `session.py` calls
`load_policy(repo)` — reading and validating `.saffron/policy.yaml` and the
gate executables in the operator's working copy — then resolves
`gate_executables(Path("/gates"))` against `export_gates`'s archive of
`base_sha`, the remote's default-branch head. Before this branch those were
the same tree; now they can diverge on any branch that touches `.saffron/`.

Two concrete consequences. An operator on a branch that adds a gate role gets
a `PREFLIGHT_FAILED` whose watch line reads *"the toolchain is broken, not the
code"* — a wrong diagnosis for a policy/export mismatch, not an infrastructure
failure. And `policy_sha` in the ledger names the working-copy policy rather
than the one that actually governed the exported gates, so the ledger's record
of what ran is not the record of what was declared.

A repo adding its *first* gate lands somewhere else again, and worse. There is
no `.saffron/gates` at `base_sha` at all, so `export_gates` raises on the
unmatched pathspec at `session.py:572` — after the image build, the host probe
and the proxy — and the run exits 2 as infrastructure rather than reaching
`PREFLIGHT_FAILED`. `export_gates_for`'s guard covers the opposite case,
`gates: {}`, where the policy declares nothing to export.

This is the ordinary workflow, not an edge case: writing or renaming a gate
means being on a branch that adds it, and running `saffron cell` from that
branch is how you would test it. The run reaches `PREFLIGHT_FAILED` before the
agent starts, so it costs nothing but the wrong diagnosis. Until it is closed,
the workaround is to land the gate on the default branch first — `base_sha` is
the remote's head, so the export sees a gate only once it is pushed there.

**Done looks like:** `load_policy` reading from the same export
`gate_executables` already resolves against, rather than from `repo`.
`export_gates` already archives a subtree with `git archive <sha> .saffron`;
loading policy from that archive — `git archive <sha> .saffron` plus
`load_policy` pointed at the export instead of the working copy — is the shape
of the fix, not a new mechanism.

**Done, 2026-08-24.** The shape held: the pathspec widened from
`.saffron/gates` to `.saffron`, and `_drive_cell` reads its policy back out of
that export. Three things the item did not say.

**The fix deleted a function rather than adding one.** `export_gates_for`'s
`gates: {}` guard existed *only* because the narrow pathspec made `git archive`
fail on a repo with no `gates/` — widening it removes the guard's reason, and
`export_gates` already cleared its own dest, which is the half of that guard
worth keeping (its staleness test moved onto `export_gates` with it). Renamed
with it: `export_gates` → `export_saffron_dir`, because a function that now
carries the policy the run is judged under cannot be named for the subdirectory
it used to copy.

**The export moved out of the try block, not just above `load_policy`.** It ran
after the image build, the host probe and the proxy; it now runs before all
three and before the ledger has a task row — so a `base_sha` carrying no
`.saffron` at all costs nothing and leaves no run behind. That case is still an
exit 2: a repo whose default branch is not onboarded cannot start a cell, which
is what pinning the policy to `base_sha` means and is stated in §5.4.

**`/gates` now also holds `specs/` and the `Dockerfile`** — everything under
`.saffron/`, because one archive is one pathspec. They are read-only and the
cell already has all of it at `/work`, so this leaks nothing; it is noted
because a mount named `/gates` holding specs is otherwise a surprise.

---

## 14. `committed` fails on build artifacts a repo does not gitignore

`dirty_paths` is read after the declared suite on both calls so that an artifact
a gate writes lands on baseline and head alike and `subtract_baseline` cancels it
(§5.4). The cancellation is by identity — `(gate, file, code, message)` — so it
only reaches artifacts whose **paths** match on both sides.

A head-only path has nothing to cancel against. The task adds `src/newmod.py`; the
head `tests` gate compiles it and leaves `src/__pycache__/newmod.cpython-312.pyc`,
which the baseline never had. `committed` fails, the repair turn says *changed but
not committed — fix these and commit*, the agent commits the artifact, and `scope`
then fails it as a path outside `touches`. The attempts burn out and the run ends
`EXHAUSTED` on a diff that was green. `.coverage.<host>.<pid>.<rand>` and
`.mypy_cache/<module>.meta.json` are the same shape.

Saffron's own `.gitignore` covers all three, which is why nothing here caught it;
an onboarded repo whose ignores are looser is not covered.

**That sentence is false, measured 2026-08-25 (#30). It covers one of three.**
`git check-ignore` against the shapes this item names: `__pycache__/*.pyc` is
ignored; `.coverage`, `.coverage.<host>.<pid>.<rand>` and
`.mypy_cache/<module>.meta.json` are **not**. The whole file is nine lines and
has no coverage entry and no mypy entry. Found by accident — a `coverage` run
during #33 left a `.coverage` that `git status` reported as untracked, which is
the opening move of the sequence above.

So the reason this has never fired here is not that the declaration is complete.
It is that no declared gate has yet written one of the two unignored artifacts —
**untested, and worth testing before this item is closed**, since if none of
`format`/`lint`/`types`/`tests` writes either file then this item is right by
accident and should say so for the right reason.

The consequence for the decision: this item argues the repo-declaration route is
free for Saffron and costly only at repo two. It is not free here, and under an
unattended night the failure is silent, arrives at the worst hour, and presents
as a task that could not pass its gates rather than as a misconfigured repo.
`session.py:674` carries a `ponytail:` comment resting on the same assumption.

Adding two lines to `.gitignore` closes this repo's instance and leaves the
question — whose declaration is this? — exactly where it was. Worth doing; not a
resolution.

**Done looks like:** the repo declaring its build output, since which paths are
artifacts is language knowledge §2.1 keeps out of core — `.gitignore` is already
that declaration and `git status --porcelain` already honours it, so onboarding
documentation stating the requirement may be the whole fix. If it is not, the
narrower mechanism is `committed` ignoring untracked paths that the baseline call
also produced *by directory* rather than by path — which is a second identity rule
sitting next to the subtraction's, and CLAUDE.md warns against making those match.

---

## 15. Two more reads of the working copy, one of them the same defect as item 13

Found while closing item 13, measured, not reasoned — and left open because
both sit in PACKAGE rather than in the cell.

**`cli.py` loads the policy for PACKAGE from `repo`.** `package()` then hands
it to `reverify`, which resolves `gate_executables` against gates exported from
`fetch_head` — item 13's asymmetry exactly, one phase later and against a
different sha. A working copy declaring a role `fetch_head` does not carry
makes the re-verification gate error, which raises as infrastructure at the
point the task is otherwise `READY_FOR_REVIEW`. It also feeds
`policy.integrity.test_paths` into the pull request body, so the body describes
the checkout's declaration rather than the one the packaged commit was verified
under. **Done looks like:** `package()` loading its policy from the export it
already makes at `fetch_head`, which means dropping the `policy` parameter
rather than threading a second one.

**Done, 2026-08-24.** `package()` exports `.saffron` at `fetch_head` and reads
its policy from it, unconditionally rather than inside the re-verification
branch — the body's `test_paths` is read on every path, so a policy loaded only
when the base moved would have been half a fix. The `policy` parameter is gone
and `cli` no longer reads `.saffron/policy.yaml` at all, which took the refusal
read with it: it existed to keep an invalid checkout policy from costing a run,
and the checkout's policy is now read nowhere on the cell path. One measured
consequence for onboarding: a repo whose default branch carries no
`.saffron/policy.yaml` cannot package, the same way it cannot start a cell.

**The cell image is built from the working copy's `.saffron/Dockerfile`**
(`image.build_cell_image(repo)`) while the gates, the policy and the base tree
all come from `base_sha`. This one may be correct as it stands — the image is
the toolchain, not the judgment, and an operator testing a new Dockerfile wants
the branch's — but it is now the only member of the family that reads the
checkout, and nothing says which way it is meant to go. **Done looks like:**
§5.1 saying so either way.

**Done, 2026-08-24: deliberate, and §5.1 says so.** The image stays the
checkout's. The drift is real and now named rather than implied — this repo's
own Dockerfile `COPY`s `pyproject.toml` and `uv.lock` out of the build context,
so a branch that touches the lock bakes those dependencies into an image
running `base_sha`'s code. It is accepted because the image is the toolchain
and not the judgment. **The scheduler reopens it**: unattended there is no
checkout for the phrase to mean anything, and the answer there is a build
context exported from `base_sha` like every other input. That is v1+ work and
is not filed as an item here, because §4.2 has to exist before it can be
written.

---

## 16. No record says which policy PACKAGE verified under

Found reviewing item 15's fix, which created the gap by closing a worse one.
`policy_sha` on the `repos` row is written once, at cell start, from the export
at `base_sha`. When the default branch has moved, PACKAGE re-verifies under
`fetch_head`'s policy instead — a *different* declaration, correctly so — and
nothing records that: not the ledger, not the pull request body, not a watch
line. The body says the gates were re-run on the packaged commit "because the
base moved" without naming what they were re-run under.

This is item 13's own complaint one phase later — *the ledger's record of what
ran is not the record of what was declared* — and the sha is already in hand at
the call site, discarded as `policy, _`.

**Done looks like:** a per-task record, which is the part that makes this an
item rather than a one-line fix. `repos.policy_sha` is per repo and written
before the task exists, so there is nowhere to put a second declaration without
deciding where a task's own policy lineage lives. §4.1's invalidation rule
(*change a repo's gate declarations mid-batch and its in-flight tasks are
invalidated*) is the same question from the other end and should be answered
with it.

---

---

## 17. `size` exists and nothing calls it

`SA-0002` built the gate (#15) and its spec put the consumer out of scope, on
the correct reasoning that the risk tier has none until v1. So the module is
present, unit-tested, adversarially reviewed — and unreachable: `session.py`'s
`_suite` builds its core-gate list from `scope`, `integrity`, `committed` and
`census`, and `size` is not in it.

**This is a spec-writing lesson before it is a task.** A spec whose output has
no consumer produces a module, not a capability, and the gate loop cannot be
handed one without a change it does not have: every `fail` today means repair,
while §5.6 makes `size` **advisory at `standard` and blocking only at
`elevated`**. There is no advisory result the repair loop honours.

**Corrected 2026-08-25, writing `SA-0005`:** the sentence here said
`policy.elevate_on` "does not exist either", and it does — `Policy.elevate_on`
(`saffron/repos/policy.py:51`), parsed, validated, tested, and already carrying
three patterns in this repo's own `.saffron/policy.yaml`. So does
`GateDeclaration.blocking` (`:29`), which is the advisory switch for *declared*
gates. Both have **no reader anywhere downstream**. That makes this task
smaller than the item claimed and its failure mode worse: a declaration a repo
can set, that validates, and that changes nothing is indistinguishable from one
that works until someone checks.

**Done looks like:** an advisory status the repair loop does not act on,
`policy.elevate_on` matched against the diff, `risk` reaching `run_one_cell`,
and `size` in `_suite`. Two things it must carry, both found reviewing #15:

- **Call it host-side, never declare it.** `size` leaves `tool` unset, which is
  right for a gate that executes nothing — and `runner.run_gate` turns a
  declared gate's `pass`/`fail` with no `tool` into `error`. Declaring it in a
  `policy.yaml` errors every task.
- **Close the binary hole with what this spec has.** A block git renders as
  `Binary files ... differ` has no `@@`, so it counts 0 and a `-diff`
  gitattribute zeroes the gate on a rewrite of any size — at `elevated`, the one
  tier where it blocks. It carries a `ponytail:` comment rather than a fix
  because the honest response is `error` only when the unreadable file is inside
  `touches`, and `size_gate` is handed neither `touches` nor a `--numstat`
  cross-check. This spec is handed both.

The same wiring is what item 6's third lens needs, and the two should be built
together or in that order.

**Done, 2026-08-25**, across three specs rather than one — which is the part
worth carrying forward. `SA-0005` (#21) wired the tier and the advisory set,
`SA-0007` (#23) closed the two call sites `SA-0005`'s `touches` could not reach,
and `SA-0006` (#24) closed the binary hole. All four clauses of *done looks
like* hold: `effective_risk(spec.risk, changed, policy.elevate_on)` matches the
diff per attempt (`session.py:663`), `cli.py:176` passes `risk=spec.risk` into
`CellSpec`, `advisory_gates` plus `_blocking` give the repair loop a status it
does not act on, and `size` is in `_suite` (`session.py:691`).

**The advisory switch is two rules, not one, and they are not the same rule.**
`size` is advisory unless the tier is elevated; a declared gate the repo marked
`blocking: false` is advisory at *every* tier, because that is what the
declaration means rather than a tier-dependent switch. They sit in adjacent
lines and reading them as one is the mistake available here.

**And `size` still needs `blocking` even though it is host-side.** Refusing an
unreadable diff ends the attempt through `aborted_gates`, which no advisory
filter downstream can soften — so a gate that stops nothing at this tier must
not spend that refusal. That is why the fix `SA-0006` shipped is a `blocking`
argument and not an `error` return.

**What this item taught, beyond the gate.** Item 18 files the general pattern —
a declaration that parses, validates, and changes nothing. This is the instance
that produced it, and the sequence is the evidence: `SA-0005` could not close
its own gap because its `touches` did not reach `cli.py` and `package.py`, so a
second spec existed only to finish the first. A spec whose acceptance criteria
reach outside its own `touches` is unsatisfiable by construction.

---

## 18. A spec's ceilings were declarations with no reader, and turn exhaustion is total loss

Found by running `SA-0005`, which is the only way it could have been found: it
is invisible to every unit test and to four green live runs.

**Two of three ceilings did nothing.** `cli.py` built `CellSpec` with
`budget_usd=args.budget` and `max_attempts=args.max_attempts`, whose argparse
defaults made *not given* and *given the default* the same value — so a spec's
own `budget_usd` and `max_attempts` were parsed, validated, and discarded.
`max_turns` was not on `Spec` at all: hardcoded 60, unsettable, unprintable.
This is the third declaration-with-no-reader in two days, after
`Policy.elevate_on` and `GateDeclaration.blocking` (item 17). **The pattern is
worth more than any of the three instances**: a field that parses and validates
and changes nothing is indistinguishable from one that works, and the repo has
now produced four of them.

**And the ceiling that fired was the one nobody could see.** `SA-0005` died at
turn 61 with $5.34 of a declared $12 spent — stopped by the bound its author
could not raise, holding more than half the budget it *could* declare.

**Turn exhaustion discards everything.** An idle or wall kill leaves commits
behind (item 4). `error_max_turns` fires with the worktree full, the cell is
torn down, and the run exports nothing: 61 turns of correct work, $7.50, zero
commits. `implement.md` said *"Commit your work"* — singular, at the end.

**Closed, 2026-08-25.** The flags default to `None` and stay overrides, the
spec governs otherwise, `max_turns` joins `Spec`, all three print with their
source on the way in, and a turn ceiling names itself in the failure instead of
reading as `exited 1`. `implement.md` asks for a commit per coherent step and
says why, with the measurement.

**And a fifth, found the same day by `SA-0005` (#21).** `cli.py` never passed
`risk=spec.risk` into `CellSpec`, and `package.py` never passed the effective
tier or the advisory set to the PR body or the queue line — a value computed,
carried out on `CellOutcome`, and read by nobody. `SA-0007` closes it.

**What made it worth more than a sixth instance: the tests.** Every test of the
new behaviour called the renderer directly with hand-supplied values, so the
suite was green about a function that works and silent about whether anything
calls it. That is the shape all five share — the declaration end is tested, the
reading end does not exist, and no test spans the two. **A test that constructs
the argument it then asserts on cannot detect a caller that never passes it.**

**And the spec is what made it unfixable in place.** `SA-0005`'s `touches` did
not include `cli.py` or `package.py`, so the implementer could not have closed
the gap without failing `scope`, and one of the three findings was dropped as
unanchorable for the same reason — it named a file the diff could not contain.
Both lenses confirmed the blocker after the rebuttal, the first recorded
disagreement this pipeline has produced (item 9), and the adjudication is on
#21: **the fault was the spec's, not the implementer's.** A spec whose
acceptance criteria reach outside its own `touches` is unsatisfiable by
construction, and nothing in intake checks for it.

**And `SA-0016`'s criterion-path refusal, built to catch exactly this at
intake, does not fire on `SA-0005` — measured, not reasoned about:**

```
uv run python -c "
from pathlib import Path
from saffron.intake import load_spec
from saffron.scheduler import _unmatched_criterion_path
spec, _ = load_spec(Path('.saffron/specs/SA-0005-size-wiring.md'))
print(_unmatched_criterion_path(spec), len(spec.acceptance_criteria))"
None 7
```

Seven criteria parse in full — `SA-0014` already fixed the truncation that
would explain a `None` here — and still none of them trips the refusal,
because none of the seven names a path at all, backticked or bare. They name
behaviour: "the PR body header and the queue line report" the effective tier,
"`size` runs in `_suite`". The paths that behaviour lives in are `cli.py` and
`package.py`, exactly the ones this item already names as outside `touches`.
A refusal keyed on path tokens cannot see a criterion that reaches outside
`touches` by naming behaviour instead of a file, and no widening of the token
rule changes that: resolving "the queue line" to a file is a symbol index,
which is language-aware, and core knows nothing about languages (§2.1) — the
check cannot live in the scan. `SA-0018` closes the gap from the other side
instead: a door at the plan checkpoint an IMPLEMENT attempt can propose scope
through, reaching `SCOPE_REVIEW` with the paths and the root cause, so a spec
shaped like `SA-0005` stops there instead of at a fourth exhausted attempt.

**Still open, deliberately:** `error_max_turns` is not resumable. A bound that
resumes is not a bound, and committing per step removes most of the loss — if a
run exhausts turns *with* its commits landing, that is the evidence for
reopening this, and the honest shape then is a repair-loop state rather than a
retry.

---

## 19. `GateDeclaration.when` is parsed and read by nothing

**Status:** open. Found while declaring Saffron's own `shacl` gate (PR #46).

`repos/policy.py` accepts `when: "**/*.ttl"` on a gate declaration and stores it;
`run_suite` runs every declared gate in declaration order and consults it nowhere.
The only reader in the tree is an assertion in `tests/test_policy.py` that the
field parses. `DESIGN.md` §5.4 illustrates the contract with a conditional gate
and §10 calls repo-defined gates "conditional on touched paths", so a reader
following the design writes a clause the loader accepts and nothing honours —
backlog item 17's shape (`size` built and nothing calling it), one layer out.

Saffron's own `shacl` gate is declared **without** `when` for exactly this reason:
a control that reads as present and is not is Appendix I's founding defect, and
validation is milliseconds so conditionality buys nothing here. That dodges the
trap and leaves it armed for the second repo, which is why this is written down.

**Done looks like** one of: `run_suite` filters on `when` against the diff's
changed paths and a test proves a non-matching gate does not run; or `load_policy`
rejects `when` outright until something reads it, and §5.4's illustration drops
it. §5.4 now says the field is unread — that note comes out with the fix.

## 20. No cell-marked test exercises the `shacl` gate

**Status:** open. Same PR.

`tests/test_saffron_gates.py` runs the gate through a bare `subprocess.run` that
inherits pytest's environment, so it finds `pyshacl` in Saffron's own venv.
Through the real `LocalExecutor` it reports `error: pyshacl not on PATH`, because
`_gate_env` strips that venv — which is correct and is what `tests` already does,
since gates target the cell. The in-cell evidence is one line in
`.saffron/Dockerfile` asserting `pyshacl --version` at build time.

That is the same class of gap Appendix I is about: every mechanism reported green
and the thing under test was somewhere else. It is thinner here — the build-time
assertion is real, and `python3` and the `pyshacl` console script both resolve to
`/opt/venv` — but nothing proves the gate produces a contract-shaped result from
inside a cell.

**Done looks like** a `@pytest.mark.cell` test that starts a cell the way
production does and runs `shacl` through `CellExecutor`, asserting `pass` and a
`tool` obtained in the cell rather than on the host.

---

## 21. Two `SimpleNamespace` fakes stand in for `Spec` and drift silently

**Status:** **done**, driven from `SA-0012`
(`.saffron/specs/SA-0012-spec-doubles.md`) in PR #49 (`f31550c`). Both call sites
now build a real `Spec` through `parse_spec`. Found by `SA-0011`. Review of that
diff found the defect had moved rather than died — value drift where this was
shape drift — which is item 24. Read what follows for why the fakes cost what
they did, not as work outstanding.

`tests/test_package.py:679` and `:783` build a `Spec` out of `SimpleNamespace`,
carrying whatever attributes `package()` happened to read when they were written.
They are not typed, so nothing checks them against the model, and they do not
fail when `Spec` gains a field — they fail later, when some renderer finally
*reads* that field, in tests that are nominally about something else entirely.

That is exactly how it went. `SA-0011` added `Spec.acceptance` and nothing
noticed for three tasks; the moment `pr_body._criteria` read it, fourteen
PACKAGE tests died on `AttributeError: 'types.SimpleNamespace' object has no
attribute 'acceptance'` — none of them about acceptance criteria, all of them
about pushes, conflicts and queue lines.

**The trap is the `touches` interaction, and it is what makes this worth an
item.** A spec's `touches` is written by reasoning about which files the change
*should* need, and nobody knows these fakes exist until the code runs. So the
cell hits a wall with no way over it: editing `tests/test_package.py` fails
`scope`, and leaving it fails `tests`. Both burn the attempt, on every attempt,
until the budget is gone — and the agent cannot widen its own `touches`, which
is the point of `touches`. `SA-0011` only got past it because a human was
watching and amended the spec. An unattended night would have spent the whole
budget on it.

The blast radius is small and was measured, not assumed: these two are the only
structural `Spec` doubles in the repo. `tests/test_session.py:86` builds a real
`CellSpec`, `tests/test_report.py` goes through `parse_spec`, and
`saffron/replay.py:51` uses a real `Spec` from `load_spec`. `CellSpec` is never
`asdict`-ed or serialised, so a pydantic model inside the dataclass costs
nothing.

Tempting and wrong: `getattr(spec, "acceptance", [])` in `pr_body`. It makes a
missing field indistinguishable from an empty one, which is §5.4's `tool` defect
in a third costume — and it puts a default in production code to accommodate a
test fake.

**Done looks like** both call sites building a real `Spec` (via `parse_spec` on
a string literal, as `tests/test_report.py` already does), so the next field
`Spec` gains is a type error at construction rather than an `AttributeError` in
an unrelated suite three tasks later. Roughly twenty lines.

**One thing it left.** `SA-0011`'s `touches` still names `tests/test_package.py`
(`.saffron/specs/SA-0011-criteria-have-witnesses.md:24`), declared only because
of these fakes. `SA-0012` and `SA-0013` both put it out of scope, and
`.saffron/**` is `forbidden` in every spec — no cell can do it. It wants a
human edit.

---

## 22. Core gate names are not reserved, and `pr_body` is now a second consumer of that hole

**Status:** open. Found by review of `SA-0011`.

`GateName` at `saffron/repos/policy.py:53` accepts any string matching
`^[A-Za-z0-9_-]+$`, so nothing stops a repo declaring `gates: {criteria: {...}}`.
Three consequences, all verified against the running code:

`saffron/phases/package.py:402`'s `reverify` runs only
`policy.gate_executables(...)` (`:468-469`) — no core gates. On a rebase
(`verified_on = "packaged"` at `:638`) the `gates` handed to `render_pr_body`
(`:673`) therefore contain no core `criteria` result, so a repo-declared gate
named `criteria` reporting `pass` is the one `pr_body._criteria` selects
(`saffron/report/pr_body.py:140`) and it ticks every box it never earned. This
is the defect `2c3b231` ("a repo-declared gate named criteria ticked every
box") fixed on the session path — `_suite` appends the host-constructed result
last, so it cannot be shadowed there — and it is still open on the reverify
path, which never runs `_suite` at all.

`_suite` also builds `advisory_gates` straight from `policy.gates`
(`saffron/cell/session.py:672-674`), so `gates: {criteria: {blocking: false}}`
makes the *core* `criteria` gate advisory — same hole for `census`. And
`suite_drift` keys both suites by bare gate name (`saffron/gates/baseline.py:84`),
so the same collision family reaches `scope`, `census` and `committed` there
too.

**Done looks like** a `frozenset` of core gate names and one `field_validator`
on `Policy.gates` in `saffron/repos/policy.py` rejecting them, which closes all
three call sites at once and gives the ontology's `CoreGateShape` an enforced
counterpart in code.

---

## 23. A witness already green at `base_sha` makes a spec unsatisfiable, and nothing says so

**Status:** open. Found by review of `SA-0011`.

`saffron/gates/core/criteria.py` reports `witness-green-at-base` (`:100`) for a
non-`preserves` witness that already passed at base. It is blocking, and no
repair turn can fix it: the agent's only routes are renaming or deleting the
pre-existing test, and `census` and `integrity` both block those. So an
operator authoring error — naming a witness that already passes — burns
`max_attempts × budget_usd` with nothing to show, the same corpse `DESIGN.md:379`
records for item 18 (`SA-0005`, $5.34, dead at turn 61).

It cannot be caught at intake, because it needs the suite. But the baseline
suite already holds the answer: after `baseline = _suite([])`
(`saffron/cell/session.py:724`), any non-`preserves` witness appearing in the
baseline's `collected` union is a spec that cannot pass, before a single repair
attempt is spent finding that out the expensive way.

**Done looks like** one `watch()` line there naming those witnesses, turning
four dead attempts into a legible operator message on the first unattended
night.

---

## 24. The fixture item 21 built drifts in value, not shape

**Status:** open, specced as `SA-0013`
(`.saffron/specs/SA-0013-fixture-values-are-witnessed.md`), drivable once `#49`
is on `main`. Found by review of `SA-0012` (PR #49).

Item 21's fix replaced the two `SimpleNamespace` fakes with `_spec()`, which
builds a real `Spec` by putting a string literal through `parse_spec`. Nothing
asserts that the values handed to `_spec()` survive the trip. Measured, not
reasoned: break the `## Acceptance criteria` header so `_CRITERIA_SECTION`
misses, or corrupt the `touches` line to yield `["ZZZf.txt"]`, and the whole
module still reports **97 passed**. `["f.txt"]` and `["it works"]` appear in
`tests/test_package.py` only as arguments to the helper, and no assertion
mentions either.

So the `packageable` fixture that feeds most of PACKAGE's tests can start
handing `package()` a spec with no criteria and a scope matching nothing, and
every test stays green while exercising less than its name claims. `parse_spec`
changing its criteria regex is enough to trigger it, and that regex has no test
tying it to this fixture. It is item 21's own thesis — a fixture whose contents
nothing checks — one level down.

**Done looks like** one new test beside the existing one, asserting
`spec.touches` and `spec.acceptance_criteria` against what `_spec()` was called
with: two assertions, red under either mutation above. New rather than an
extension of `test_the_package_fixtures_build_a_real_spec`, which is green at
base and would fail `criteria`'s `witness-green-at-base` — item 23, met in the
wild while authoring the spec.

---

## 25. A spec's own diff can be too large for its own repair loop

**Status:** open, resplit as `SA-0014`–`SA-0017`. Found by running `SA-0009`
(task 11).

`SA-0009` was §4.2.1's read-only half — discovery, the re-queue filter, the
six refusals, `saffron queue` — as one spec. It never converged: two `IMPLEMENTING`
attempts landed 990 changed lines across seven files, `size` failed every gate
run after at the 600-line feature ceiling (`gate_result_id` 113/124/135), and
two `REPAIRING` attempts each burned a full `max_turns=100` trying to cut the
diff down without ever getting `committed` clean again — $31.60 against an $18
budget, terminal state `EXHAUSTED`, zero lines merged.

**The size was foreseeable before a single turn ran.** The diffstat splits
cleanly along the spec's own acceptance criteria: `tests/test_scheduler.py`
alone was 433 of the 990 lines, because it was carrying tests for two
unrelated mechanisms — the `spec_sha` re-queue filter and the five refusals —
each demanding its own fixture per the spec text. A spec whose acceptance
criteria describe more than one mechanism is a spec whose diff is the sum of
both, and nothing checked the sum against the ceiling before the cell started.

**Done looks like** the same work recut so each piece fits inside one repair
loop: `SA-0014` (intake's parser fix and directory discovery), `SA-0015`
(the ledger reads and the re-queue filter), `SA-0016` (the four refusals that
need `touches`, criteria, or GitHub state), `SA-0017` (`saffron queue`'s CLI
wiring) — chained by `depends_on`, ~150–420 lines apiece by the same diffstat.
`SA-0009` itself is left as written: its `spec_sha` is pinned to the
`EXHAUSTED` task above, and editing it would only mint a fresh `spec_sha` for
a monolith nothing intends to run again.

**Still open:** nothing yet checks a spec's own shape — how many acceptance
criteria, how many files in `touches` — against its `type`'s size ceiling
before a cell starts. That would have caught this one for the price of a
`gh`-free scan, the same argument item 18 made for turn ceilings.

---

## 26. Discovery cannot tell an empty night from a missing directory

`discover_specs` (`saffron/intake.py`, landing with `SA-0014` in PR #56) returns
`(specs, failures)` and reaches the filesystem through `directory.glob("*.md")`.
`Path.glob` yields nothing for a directory that does not exist and nothing for a
path that is a file, so all three of these are the same value:

```
discover_specs(Path("/nope/nothing"))   -> ([], [])
discover_specs(Path("saffron/intake.py")) -> ([], [])
discover_specs(<an empty directory>)    -> ([], [])
```

Measured at `30bd85c`. The spec's second acceptance criterion asks only that a
*malformed spec* not raise past discovery, so this is not a violation of it —
the scan does what it was asked. It is the distinction this repo enforces
everywhere else that is missing: `error` ≠ `fail`, and a gate that never ran
must not read like one that ran and passed. A scan that never saw a directory
must not read like a night with no work in it.

It matters at the seam, not here. `SA-0017` resolves `base_sha` and exports
`.saffron/specs/` from a repo; `SA-0015` builds the queue from what discovery
returns. An export that silently produced nothing — wrong `base_sha`, a repo
that never had `.saffron/`, a path assembled with the wrong join — reaches the
scheduler as a quiet empty queue, and the first unattended night ends having
done nothing with no record saying why. That is the failure mode this backlog
is ordered by.

**Done looks like** `discover_specs` raising `SpecError` when `directory` is not
an existing directory, with a test for the missing path and the not-a-directory
path. The caller owns the export, so a directory that is not there is an
infrastructure fault (exit `2`), not an empty scan — the same call
`PREFLIGHT_FAILED` makes. An existing but empty directory stays `([], [])`,
which is a true statement about a repo with no specs.

---

## 27. `SA-0018` built a door it could not document, and the prompt then contradicted it

**Status:** **done** — `SA-0021`, by hand on the host, 2026-08-30.

`SA-0018` added a second producer of `SCOPE_REVIEW`: an IMPLEMENT attempt whose
declared `touches` cannot satisfy its criteria proposes a set instead of grinding
to a ceiling. The code shipped and works. The documents that define what the words
mean did not move, because **`DESIGN.md` and `CONTEXT.md` were both in `SA-0018`'s
own `forbidden` list** — so the spec that created the affordance was structurally
unable to describe it.

The result was a prompt that contradicted itself. `CONTEXT.md` §3 is injected into
the IMPLEMENT system prompt (`SECTIONS_BY_PHASE['IMPLEMENT']` is `(1, 2, 3, 4, 10)`),
and its **Touches** entry read "proposed by DIAGNOSE and ratified by the operator on
bug specs". So the same assembled prompt offered the implementer the door and told
it, more specifically, that the door was DIAGNOSE's on bug specs. The specific
sentence wins that argument.

**This is the situation `SA-0018` exists to give an exit from, one spec later and
one level up.** Its `touches` could not reach the files its own feature made wrong;
by the feature's own logic the correct move was a scope proposal naming `DESIGN.md`
and `CONTEXT.md`. It was found by review instead. Note that a *proposal* naming
those paths would have been recorded — `validate_scope_proposal` checks only that a
path escapes `touches`, not that it escapes the deny lists — so the door was open;
nothing pointed the implementer at it.

Closed by `SA-0021`, by hand on the host (see item 28), 2026-08-30: §3.3 draws
`SCOPE_REVIEW` from IMPLEMENTING, §5.3.1 states the door's three rules, §5.2 no
longer claims the contract as DIAGNOSE's alone, and `CONTEXT.md`'s **Touches**
entry names both proposers. The witness reads the *assembled* prompt rather than
`CONTEXT.md`'s text, because reasoning about which sentences reach the model is
what failed here.

---

## 28. A spec whose `touches` are protected paths dies at the plan checkpoint with no exit

**Status:** **done** — `SA-0023`, 2026-08-31.

`SA-0021` — the spec that closes item 27 — declared `DESIGN.md` and `CONTEXT.md`
in `touches`, which is the only honest declaration it could make. Run as a cell on
2026-08-30 (ledger task 18) it ended `PLAN_REJECTED` in 2m44s having spent $0.82:

```
PLAN: rejected, $0.82 spent — DESIGN.md is a protected path
```

`.saffron/policy.yaml` lists `DESIGN.md`, `CONTEXT.md`, `.saffron/**` and `uv.lock`
under `protected:`, and `validate_plan` (`saffron/agents/artifacts.py`) rejects any
plan naming a protected path — checked after `touches` and `forbidden`, with no
exemption for a path the spec itself declares. The protection is right: those two
documents are authoritative, and a cell rewriting the definition of its own
constraints is exactly what a global deny list is for. What is missing is an exit.

The scope-proposal door does not cover this. That door is for "the declared
`touches` cannot satisfy the criteria"; here they can — it is policy, not scope,
that bars them. So the implementer correctly wrote a plan, and the plan was
correctly rejected, and the task is terminal at a state that means "your spec needs
work" when the spec is as good as it can be. Every future attempt spends the same
$0.82 to reach the same wall. This is item 18's shape — a declaration with no
reader — inverted: a rejection with no route.

**Done looks like** a plan naming a protected path inside the spec's own declared
`touches` ending at `SCOPE_REVIEW` rather than `PLAN_REJECTED`, carrying the
protected paths as the proposal and the rejection reason as the root cause, so the
work reaches the operator as a one-click "do this by hand" rather than as a dead
task. A plan naming a protected path *outside* `touches` stays a rejection: that is
an agent reaching for something it was never given, which is the case the check was
written for. Until then, a docs spec over protected paths must be run by hand and
say so in its own notes.

**One tension to meet deliberately rather than at implementation time.** Such a
proposal names only paths *inside* the declared `touches`, which is precisely what
`validate_scope_proposal` refuses — "every proposed path is already inside touches".
Generated host-side it would bypass that validator, and `SCOPE_REVIEW` would then
carry two meanings: a scope to ratify, and "this one is yours to do by hand".
`CONTEXT.md` defines **Ratify** as what the operator does to a *proposed `touches`
set*, so the second meaning needs either a different state or a deliberate widening
of that definition — not a quiet reuse.

**Closed differently from this item's own "Done looks like."** Not a second
`SCOPE_REVIEW` producer — the tension two paragraphs up is why: that state already
means "ratify a proposed `touches` set", and this collision is not one. Instead,
`SA-0023` added a refusal beside `SA-0016`'s: `scheduler.protected_touch_refusal`
compares a spec's declared `touches` against `policy.yaml`'s `protected` list with
the same glob matcher every other `touches` comparison uses, deciding only literal
`protected` entries — an entry that is itself a glob (`.saffron/**`) is left to
`validate_plan`'s own rejection, unmoved, still the backstop. Read at both places
this repo's specs actually run: the scan (`build_queue`'s new `protected`
parameter) and the attended single-spec run (`cli._run_cell`, before a cell
exists), both from the same `base_sha` export `build_queue`'s specs already come
from — never the working copy (items 13 and 15). What it cost to learn: one task,
$0.82, and a spec that had to be run by hand with nothing on the way in saying so.

---

## 29. Nothing recorded that a task merged, measured against this repo's own ledger

`SA-0019`. `set_task_state` is the only writer of `tasks.state`, and PACKAGE's
last word is always `READY_FOR_REVIEW` — nothing asked GitHub what happened
after, though §3.3 draws arrows onward to `MERGED`/`REJECTED`/
`CHANGES_REQUESTED`/`APPROVED`, and a dead batch scan leaves `ORPHANED`.

**Measured, 2026-08-30:** `select task_id,spec_id,state,pr_url from tasks
where pr_url is not null` against this machine's ledger returned six rows,
every one `READY_FOR_REVIEW`. Cross-referenced against this repo's own
`git log --all --oneline --merges`:

| spec | pull request | ledger said | `gh` says |
|---|---|---|---|
| `SA-0013`..`SA-0017` | #51, #56, #59, #60, #64 | `READY_FOR_REVIEW` | `MERGED` |
| `SA-0018` | #65 | `READY_FOR_REVIEW` | still open |

Five of six were wrong, with no mechanism that could make them right.

**A corpse was never stamped either**, per §4.2.1's own premise: "in flight"
and "dead" are synonyms only inside a batch scan, which v0.5 has none of —
the only candidate caller is `saffron queue`, run at will, mid-phase
included. A first attempt (`EXHAUSTED` at $12.12) stamped every in-flight
row unconditionally and was correctly blocked: `ORPHANED` is in
`scheduler.REQUEUE_STATES`, so a live row stamped that way is handed back
out as resumable — a second cell on the same branch.

**Done, 2026-08-30.** `saffron/reconcile.py`'s `reconcile()` — a writer
inverting `scheduler._open_prs`'s best-effort shape (an untrustworthy `gh`
answer counts as "could not be asked", never "not merged"; `MERGED` is never
asked again) — wired into a new `saffron reconcile --repo .` and into
`saffron queue` before it scans. Neither asserts §4.2.1's batch-scan premise,
so neither stamps `ORPHANED`; the supervisor still does, on the path it
already owned (`cell/session.py`, §4.5). **What has no writer is the scan's
half** — the corpse a hard kill or a power cut leaves behind, which is the
case §4.2.1 is actually about, and it waits for a caller that can assert the
premise. Tested against this repo's own six rows above, plus the CLI witness
that `IMPLEMENTING` survives `queue`/`reconcile`.

**One live-task path is left open deliberately, and `SA-0020` must close it
before a scan gets teeth.** The in-flight guard protects a first run for a
structural reason — `pr_url` is NULL until PACKAGE's last write, so there is
nothing to ask about. A *resumed* task escapes it. `_drive_cell` writes
`READY_FOR_REVIEW` and calls `finish_run` before `cli._run_cell` invokes
PACKAGE, so while PACKAGE runs the row reads `READY_FOR_REVIEW` and still
carries the **previous** attempt's `pr_url`, whose `reviewDecision` is the
`CHANGES_REQUESTED` that requeued it. Reconciling inside that window writes a
`REQUEUE_STATES` value onto a task whose cell is alive — the same double
-execution shape the first attempt was blocked for, arriving by the other
column. Harmless in v0.5: no scan starts a cell, and PACKAGE's
`set_task_package` overwrites the row moments later. **Done looks like** the
state being stamped out of `PR_PENDING_STATES` before PACKAGE is called
(`cli.py` owns that ordering), not a wider guard inside `reconcile` — the row
is genuinely `READY_FOR_REVIEW` in that window, so no state test can tell it
from a finished one. Note `runs.status = 'RUNNING'` is a liveness signal the
ledger already carries and no forbidden file owns; it does not close *this*
window, because `finish_run` precedes PACKAGE.

---

## 30. A protected document's one-line definition of a gate drifts the moment the gate changes, and the fix is always by hand

`SA-0024` widened `scope_gate` (`saffron/gates/core/scope.py`) to also fail a
changed file matching a spec's `forbidden` list or the repo's `protected` list,
not only a file outside `touches`. `CONTEXT.md` §3 still defines the gate in
one line: *"The check that changed files are a subset of `touches`."* That
sentence is now false — it describes half the gate — and nothing in this
spec's `touches` can fix it: `CONTEXT.md` is `protected`, so no plan naming it
can be validated (item 28's `SA-0023` refusal), and it is in this spec's own
`forbidden` list besides. The correction is a by-hand follow-up, the same
shape item 27 (`SA-0018`/`SA-0021`) and item 28 (`SA-0023`) already
established for a protected document a spec cannot reach.

**This is the second instance of that drift, not the first.** Item 27 is the
first: `SA-0018` added a second producer of `SCOPE_REVIEW` and could not update
`CONTEXT.md`'s **Touches** entry to say so, because `DESIGN.md` and
`CONTEXT.md` were both in `SA-0018`'s own `forbidden` list — the same
structural reason this item exists. `SA-0021` closed that one, by hand, one
spec later. The pattern both instances share: a spec that changes what a core
mechanism does can never be the spec that updates the one document defining it
in prose, because that document is `protected` by the same policy the spec's
own change makes more precise. A third instance should not need a third
backlog item before it is treated as a rule of the process rather than a
one-off gap: **any spec that changes core gate or phase behaviour should name,
in its own notes, the `CONTEXT.md`/`DESIGN.md` sentence its change makes
stale**, so the by-hand follow-up has a known list rather than a fresh reading
of both documents each time.

**Status:** **done** — by hand on the host, 2026-08-31, in `SA-0024`'s own
pull request.

**And the enumeration is what the item was actually for.** `CONTEXT.md` §3 was
the sentence this item named, and it was the *least* load-bearing of the six.
`DESIGN.md` — authoritative for what the system does, and cited by section
number from specs — carried four more, one of which stated the shipped
behaviour's exact opposite:

- §3.1's frontmatter example: `forbidden: # denied at the plan checkpoint, not
  against the diff`
- §3.1's paragraph *"**`forbidden` and `protected` bind the plan, not the
  diff** … No gate reads either against a diff."*
- §3.1's next paragraph, describing the gap as *"Stated rather than fixed"*
  after `SA-0024` fixed it
- §5.4's gate table row: `| scope | core | yes | changed files ⊆ touches |`
- §5.2's writeback rule, which item 31 covers separately

The second of those already carried a scar — *"the wording here said otherwise
until `SA-0011` leaned on it"* — so a spec that read it would have leaned on
wording false in the opposite direction. The by-hand list this item asks specs
to carry was written into `SA-0024` and still named only one of six documents,
which is the argument for making it a check rather than a request: **the spec
that proposed the rule did not follow it.** A plan-checkpoint or gate-0 check
that a spec changing a core gate names the `DESIGN.md`/`CONTEXT.md` sentences
its change makes stale is the shape; it is not written.

## 31. `SA-0024` made `touches` unable to rescue the ratification writeback, in a repo whose spec directory is `protected`

§5.2 requires the task's own spec path to be added to the ratified `touches`
when a scope proposal is recorded, *"or that first commit fails the `scope`
gate on every ratified task"* — the writeback commits to `.saffron/specs/…`,
which DIAGNOSE would never propose. `saffron/cell/session.py` implements it,
and its comment names the measurement.

`SA-0024` made the deny lists independent of `touches`, which is the whole
point of the change: widening `touches` must not clear a denied path. But
this repo's `.saffron/policy.yaml` lists `.saffron/**` under `protected`, so
the host-authored writeback commit is now exactly such a path. A ratified task
would report `[scope] .saffron/specs/SA-XXXX-….md protected` — a blocking
failure the agent cannot repair, because reverting it destroys the
ratification the operator just granted.

**Latent, not live.** Nothing in `saffron/` performs the writeback yet:
`SCOPE_REVIEW` writes `scope_proposal.json` and stops for a human, and
`base_sha` is the remote default-branch head, so a writeback merged by hand is
already behind the base a cell diffs against. The mechanism is designed,
documented and half-built, which is why this is an item rather than a note.

**Done looks like** the recorded spec path exempted from the deny lists in the
same place it joins `touches` — one exemption, host-added, never the model's —
with a test that a ratified task's first commit passes `scope` in a repo whose
spec directory is `protected`. Found by the review of `SA-0024`, not by a run.

## 32. The dependency gate asked whether a parent shipped and answered from a record of cell runs

**Done, 2026-08-31**, by hand on the host — `_retired_ids` in
`saffron/scheduler.py`, admitting a `depends_on` whose parent sits in
`.saffron/specs/done/`.

`SA-0020` narrowed the dependency refusal to admit a parent recorded `MERGED`,
which is right for a parent a cell ran. **Only a cell writes a task.** So a
spec a human implemented looks exactly like a spec nobody has run, and its
dependents stayed refused however plainly the parent's code sat in `main`. The
gate asked "is the parent's work in the default branch" and answered from a
record of cell runs; in a repo where humans and cells both commit, those are
two questions.

Measured the same day it shipped: `SA-0020` was implemented by hand, so
`SA-0022` was refused with *"no task in the ledger says it merged"* — true,
and not what the operator needed to know. The queue was empty and its one
refusal was wrong about the only work left.

Retirement to `specs/done/` already meant exactly the missing fact — that
directory's README opens *"Specs whose work is in `main`"* — and stating it
there costs nothing and writes no false row into the audit trail, which is the
one thing the ledger may not contain. Ids are read from frontmatter rather
than filenames, and a retired spec that no longer parses is not credited: the
refusal stands, the only direction that cannot admit a child whose parent is
absent.

**What this does not do:** stacking (§4.2, `SA-0022`). A retired parent is
admitted for the same reason a merged one is — the child is cut from the
default branch and the parent's commits are already in it. A parent that is
merely `READY_FOR_REVIEW` is still refused, which is §4.2's own rule minus the
half v0.5 cannot honour.

## 33. Stacking's other half needs two bases, and the two now disagree on purpose

`SA-0020`'s first attempt (ledger task 20, `EXHAUSTED` at $14.43 against a $16
budget, 2026-08-30) found that a stacked task — one whose parent is still only
`READY_FOR_REVIEW`, item 32's remaining half — needs `worktree.prepare_worktree`
to check out the parent's own unmerged branch head, ahead of `base_sha`, while
the exported patch was still computed as `export_patch(container, base_sha)`
and so captured the parent's entire diff plus the child's own. It could not fix
that: `saffron/phases/**` was forbidden to it, and the `touches` insufficiency
only surfaced after the plan checkpoint, past §5.3.1's one door out.

This split the remaining work in two. This item is the half with no production
trigger: `CellSpec.stacked_on`, distinct from `base_sha`, and
`worktree.prepare_worktree`'s matching parameter, so a worktree can be built on
a base other than the run's pin and a patch can be exported against that same
base rather than against `base_sha` — proven with a real two-commit parent
branch and a real child commit on top, not a value a test constructs and then
reads back. `cli.py` sets `stacked_on=None` explicitly at the one place a
`CellSpec` is built, so `depends_on` is not consulted on that path at all and
no real task stacks yet. `SA-0025` resolves a real parent onto the field, wires
it into `_drive_cell`, teaches PACKAGE to target the parent's branch, and
widens the dependency gate to admit a `READY_FOR_REVIEW` parent.

**The disagreement this creates is real the moment `SA-0025` wires it up, and
it is worth deciding now rather than at the hour nobody is watching.** A
stacked worktree's tree is the parent's unmerged commits plus the child's own —
code the gate executables and the policy declaring them, both exported from
`base_sha` (item 13), have never seen. Two ways that can go wrong: a gate role
the parent's own commits added exists in the tree but not in the exported
`.saffron/gates/`, so `run_suite` never invokes it — a silent gap, not a
`skip` that names itself; and a gate that would judge the parent's own change
differently under the parent's own policy update instead judges it under the
policy that predates that update.

**Decision: `base_sha` wins — the gates and the policy declaring them stay
resolved from it, stacked task or not.** Two reasons, not one. First, this
spec's own out-of-scope line is explicit that it does not redefine what
`base_sha` means; moving the gate source to `stacked_on` for some tasks and not
others *is* that redefinition, one call site at a time, and item 13 already
spent a whole item settling gates-from-`base_sha` as the run's pin — a second,
task-local exception to it is a third thing to keep in step with the first two
rather than one settled fact. Second, `base_sha` is the one value every task in
a run shares; a gate source that moved with `stacked_on` would mean two
sibling tasks stacked on two different parents run under two different gate
suites inside the same run — a suite-drift vector already named once, for
`reverify`'s missing `thread_env` (item 11), and the common case here rather
than the exception.

**What this defers, by name, for `SA-0025` to inherit rather than rediscover.**
A parent that adds or changes a gate role stays invisible to a child stacked on
it until the parent lands on the default branch and `base_sha` itself moves
past it — the same shape item 13 already accepted for an operator's own
branch, now also true of a dependent task's parent. Closing that without
moving what `base_sha` pins means exporting a second, `stacked_on`-sourced gate
set for a stacked task alone and running both suites, which is unbuilt and is
not this item's to build: the requirement here was that the disagreement be
recorded, not resolved.

**`package.py`'s own read of the base, which looks correct and is not.**
`saffron/phases/package.py:526` is `json.loads(patch.json)["base_sha"]`, and it
feeds `assert_base_objects`, the `git apply --3way`, `needs_reverification`
and the pull request body's provenance. `SA-0022` records `tree_base` beside
`base_sha` precisely so that read *can* be made correct — for a stacked child
the patch is relative to `tree_base`, and applying it to `base_sha` puts
parent-relative hunks on a tree without the parent's commits: `MERGE_FAILED`
at best, an apply that looks right at worst. It is the likeliest place
`SA-0025` gets this wrong, because a one-word read that is correct today
raises no question. `SA-0025` also owes `CONTEXT.md` an entry for the second
base: `tree_base` is a new noun and it is already in a durable artifact.

**Re-verification is the second caller, and it is not covered above.**
`saffron/phases/package.py` calls `prepare_worktree` a second time, building
its baseline and head worktrees from the current default-branch head. For a
stacked child that is the wrong baseline outright — the parent's commits are
not in it — which is a different failure from the gate-source disagreement
this item decides. `saffron/phases/**` is forbidden to `SA-0022`, so recording
it here is the only action available; `SA-0025` owns the file and the fix.

**Decided and implemented, 2026-08-31 (`SA-0025`).** `package()` now takes an
optional `parent_branch`. Unset — every caller today — nothing above changes:
`target_branch`/`target_head` resolve to `default`/`fetch_head` exactly as
before, and reading `tree_base` instead of `base_sha` for the patch's preimage
check is a no-op, because `SA-0022` already writes the two equal for an
unstacked task. Set, and the parent's own commits are not yet an ancestor of
`fetch_head`, PACKAGE opens against the parent's current head instead —
fetched fresh, so a parent that merged, force-updated or was deleted between
the child's start and its push is caught (named as `ParentGone`, one message
for "gone", a different one for "moved to a commit the mirror cannot reach")
before a pull request opens against a branch that is not there. A parent
already merged into `fetch_head` falls back to the ordinary target rather than
re-fetching a branch that is routinely deleted the moment its own PR lands.

This also answers the re-verification baseline question left open above:
**the fresh baseline is whichever tree the child is ultimately packaged
against** — the parent's current head when stacked and the merged-fallback
has not fired, `fetch_head` otherwise — never `fetch_head` unconditionally.
`needs_reverification` and `reverify`'s `new_base_sha` both read that one
value (`target_head`) now, closing the gap the paragraph above named: a
stacked child's baseline used to omit the parent's own commits entirely. The
disagreement decided above — the gates and the policy declaring them staying
pinned to `fetch_head`'s export regardless of stacking — is unchanged; only
the baseline commit `reverify` diffs against moved.

**Left unrecognised, by design: a squash-merged parent.** The ancestor check
above is `git merge-base --is-ancestor tree_base fetch_head`, mirror-local.
GitHub's squash-merge writes a new commit object onto the default branch that
shares no history with the parent branch's own commits, so a squash-merged
parent whose branch was then deleted — the ordinary shape once a PR lands —
reads as "gone without merging" rather than "merged": `ParentGone` fires and
the task ends `MERGE_FAILED` for a change that, in fact, already shipped.
Recognising a squash merge needs GitHub's own merge record (the PR's `merged`
flag and `merge_commit_sha`), not anything the mirror holds, and building that
is not this item's to do. The failure mode this leaves is a false negative
that costs a task, never a pull request opened against a branch that is not
there and never a silent double-apply of the parent's hunks — the two shapes
this item exists to rule out.

**Two more shapes accepted rather than solved, and one debt reassigned.**

- *A parent force-pushed to a history that no longer contains `tree_base`.*
  Distinct from the two `ParentGone` names: the fetch succeeds and the head is
  reachable, so nothing above fires, and the child's patch three-way-rebases
  onto a divergent parent. In the bad cases that conflicts and ends
  `MERGE_FAILED`; in the benign-looking ones it can resurrect content the
  force-push removed. A `merge-base --is-ancestor tree_base parent_head` check
  would name it, and `SA-0026` — which is what first produces a real parent to
  force-push — cannot make it: `saffron/phases/**` is forbidden there. It needs
  a spec of its own, after stacking is live and the shape can be measured.
- *A pruned mirror inverts a gone parent's classification.*
  `assert_base_objects(mirror, tree_base)` has to precede the fetch — it is
  checking for objects the fetch would otherwise supply — so a parent deleted
  without merging, in a mirror since gc'd, raises `PackageError` and exits 2
  before the `ParentGone` path can make it this task's own `MERGE_FAILED`.
  Latent and gc-dependent; the ordering is right and the classification is not.
- *`CONTEXT.md` still owes `tree_base` an entry.* This item asked `SA-0025` for
  it, and `SA-0025` forbids itself `CONTEXT.md` — correctly, since its
  documentation half is by hand. `SA-0026` carries the sentences, and carries
  this one with them: `tree_base` is a noun in a durable artifact and the
  glossary does not have it.

**Decided and implemented, 2026-08-31 (`SA-0026`).** The producer is real now.
`cli._resolve_stacked_on` reads `Ledger.tasks_by_spec_id(repo_id,
depends_on[0])` — every task row this repo has ever run for that one parent
spec id, across every `spec_sha` it has carried, the same "merging is
permanent" reach `merged_anywhere` already takes, because this attended path
never reads the parent's spec file and so has no current sha to filter rows
to. Among those rows, the newest one still in `scheduler.
DEPENDENCY_WAITING_STATES` (`READY_FOR_REVIEW`, `APPROVED`, `MERGE_TRAIN`) is
"the parent's task" — the same waiting-outranks-dead precedence
`_dependency_refusal` already gave the gate's own refusal text. Not the same
row, though: the gate reads only the parent's current `spec_sha`, so a parent
whose spec text moved after its pull request opened has a waiting row here and
none there. The branch is real either way; the gate decides whether the
dependent runs, and the resolver only decides what it is cut from. Its `pushed_sha` becomes `CellSpec.stacked_on`, its `branch`
becomes `package()`'s `parent_branch`, and both are `None` together —
never one without the other — the moment either is missing, empty, or not a
resolved sha: a merged or retired parent (no waiting row at all) yields an
ordinary unstacked cell rather than a `CellSpec.__post_init__` `ValueError`.
K=1: only `depends_on[0]` is ever a stacking candidate. The dependency gate
(`scheduler._dependency_refusal`) now returns `None` — admits — for the three
waiting states instead of refusing them with the sentence this item's own
neighbours quoted; that sentence is gone, not left beside a gate that no
longer says it.

The two shapes named above are exactly as open as they were; shipping the
producer did not close either. Force-push detection is still unbuilt —
`saffron/phases/**` stays forbidden here, so the `merge-base --is-ancestor
tree_base parent_head` check the first bullet names is recorded again, not
added, now that a real stacked parent exists for one to force-push onto.
`CONTEXT.md`'s `tree_base` entry is still owed by hand — this spec forbids
itself that file too, for the same reason `SA-0025` did.

**A canary fired that this spec had no file to retire, and the deny list is
what made that a defect.** `SA-0025` planted `tests/test_package.py::
test_the_operators_reachable_packaging_path_is_unstacked`, asserting the
literal string `parent_branch` does not appear anywhere in `saffron/cli.py`
— true the day it was written, and false the moment a producer exists, by
the test's own docstring ("the one caller reaching `package()` in production
must not pass a parent"). `SA-0026` is that producer, and `tests/test_package.py`
is not among its `touches`, so the cell could satisfy the guard's letter or
fail the `scope` gate and nothing else. It spelled the keyword by
concatenation (`{"parent" + "_branch": ...}`), said so in a comment, and
recorded it here — the right handling of a box a spec put it in, and both
review lenses still flagged the result, correctly: a green guard that proves
only the absence of one spelling misleads whoever next reads it.

Retired by hand at review, 2026-08-31. The text search is deleted rather than
rewritten — it asserted a property of `cli.py` from `tests/test_package.py`,
and a source grep is satisfiable by any caller willing to spell the keyword
differently. Both halves are asserted on the call now, in `tests/test_cli.py`:
`test_a_stacked_worktree_passes_its_parents_branch_to_package` for a stacked
run, and `test_an_unstacked_worktree_passes_no_parent_branch_to_package` for
the converse. `cli.py` spells the keyword.

**The rule this is the second instance of.** A spec that turns on a
capability must own the tests that assert the capability is off, or its
`touches` hands the agent a choice between a false green and a `scope`
refusal. `SA-0022` missed `saffron/cli.py`; this one missed
`tests/test_package.py`. Both were caught in review rather than by the gate
that could have caught them — an inertness guard names the spec that will
retire it, and nothing checks that the named spec can reach the file. At
three instances the rule is wider than tests: `SA-0026` could reach neither
`saffron/cell/session.py`'s nor `saffron/phases/package.py`'s comments saying
stacking was off, both corrected by hand at review. **A spec that turns on a
capability must be able to reach every artifact that says the capability is
off** — the guard, the comment, and the design sentence alike.

**The ledger's recorded sha is not the branch, and nothing put the branch in
the mirror.** Found in review, not by a gate, and it would have killed the
first real stacked run. `_resolve_stacked_on` originally returned the parent
task's `pushed_sha`; two separate problems with that:

- *Nothing fetches it.* `ensure_mirror` fetches `+refs/*:refs/*` from the
  operator's **local checkout** with `--prune`, so a parent branch they do not
  happen to have checked out is deleted from the mirror; `fetch_default_branch`
  fetches only the default branch; and the cell's own seed (`worktree.py`)
  fetches the mirror's default refspec. Measured: this repository's mirror had
  already pruned `refs/heads/saffron/SA-0025` while that pull request was open,
  and its `refs/heads/saffron/*` set is exactly the operator's local branches.
  `git checkout -b <branch> <parent_sha>` in the seed is then
  `fatal: unable to read tree`, exit 2, naming neither the parent nor why.
  `fetch_default_branch`'s own comment made this argument one branch over.
- *It is a commit behind.* `pushed_sha` is written once, by PACKAGE. Every
  review fix an operator commits by hand moves the branch past it. Measured on
  this pull request: task 26's `pushed_sha` was `ab23523` while
  `saffron/SA-0026`'s head was `5ab674e` — a child would have been cut from a
  tree containing the concatenation dodge the review had already removed.

Both are one fix: the ledger says **which branch**, `fetch_parent_branch`
(`SA-0025`, one branch over from where it was already used) says **which
commit**. `ParentGone` there is an unstacked cell and a printed line, not a
failure — a deleted parent branch has either merged or been abandoned, and
neither is worth killing an attended run over.

**The overlap refusal shadowed the widened gate completely.** `_refuse` checks
a candidate's `touches` against every open pull request's changed files
*before* it reaches the dependency check. A parent at `READY_FOR_REVIEW` has an
open pull request by definition, and almost every spec here touches
`docs/BACKLOG.md` — so nearly every stacked child was refused on its own
parent's pull request and never reached the admission this item exists to
build. `SA-0025`'s pull request changed `docs/BACKLOG.md`, which is in
`SA-0026`'s `touches`: this very pair would have been refused. Fixed at review
by exempting `depends_on[0]`'s branch, and only that one — a child cut from
its parent's tree already contains the parent's changes, which is what
stacking is; any other task's pull request over the same file is still the
collision the check exists for.

**The by-hand half, done at review rather than owed.** `DESIGN.md` and
`CONTEXT.md` are `forbidden` to every spec in this sequence, deliberately, so
an operator corrects them: §4.2's dependency-gate rule and §4.2.1's `depends_on`
paragraph (which said every other parent state is still refused), §5.7 (which
described one base, and now carries the two-bases paragraph and the
fetch-never-remember rule), §9's v2 list (which still deferred stacking), and
`CONTEXT.md`'s new **Tree base** entry. §3.1's frontmatter example needed no
edit: `depends_on: [TE-0139] # satisfied at READY_FOR_REVIEW` was the design's
stated intent all along, and is true for the first time.

---

## 34. A turn ceiling that fires with zero commits was total loss, and item 18's prompt was not enough

**Closed by `SA-0028`, 2026-09-01.** Item 18 closed `SA-0005`'s turn-ceiling gap
by making `max_turns` a real, per-spec, printed ceiling and asking
`implement.md` for a commit per coherent step, "with the measurement." That was
necessary and it was not sufficient: `SA-0025`, ledger task 24, hit the same
shape it was written about and died the same way.

**Measured, once, and it cost a whole task.** `SA-0025` ran `NOT_IMPLEMENTED`
at $14.61 — the first zero-commit run of the eight logged at the time. Its two
attempt rows:

| n | turns | cost | subtype | terminal_reason |
|---|---|---|---|---|
| 1 | 36 | $2.93 | `success` | `completed` |
| 2 | 141 | $11.68 | `error_max_turns` | `max_turns` |

The plan was accepted and was good. The implement turn ran to its ceiling
trimming the diff to fit `size`, committed nothing, and `teardown: no commits,
nothing to export` threw all of it away — with $5.39 of the budget still
unspent. **The turn ceiling bound, not the dollars**, which is the fact a
prompt cannot answer: `implement.md` already said "commit your work," and the
agent still ran to 141 turns without doing it. Telling an agent to behave
differently is not a control; it did not become one the second time either.

**The control is structural, at the one boundary the host already owns.**
`session.py` already reads `terminal_reason` off the closed turn and
`commits_ahead` off the worktree — the two facts together are unambiguous: a
turn that ended with `terminal_reason == "max_turns"` and zero commits was cut
off, not finished. When both hold, and only then, the host now spends one more
turn — resumed on the same `session_id`, so the agent keeps the context it
already paid for — whose only instruction is to commit what already exists.
Bounded at `SALVAGE_MAX_TURNS` (five, against `intake`'s default ceiling of
sixty — the spec that measured this set its own to 120), and clamped to the
spec's own `max_turns` so it can never exceed the turn it salvages: a salvage
that could itself run to 140 turns is the defect
this item closes, one level down. The budget ceiling is checked before the
salvage turn is spent, never after — a task with no room left ends exactly as
it did before this existed, and the watch line says the budget stopped it
rather than silently skipping the turn. A turn that finished on its own with
nothing gets no salvage: the agent decided it was done, and §4.3's "doneness is
measured, never reported" does not become "measured, then argued with."

**What this does not cover, on purpose.** It is one turn at one boundary
(IMPLEMENT only — not the REPAIR loop's own turns, which already checkpoint
dirty work on a bound firing, item 4). Two neighbouring branches lose an
uncommitted tree exactly as before, and both are decisions rather than
oversights. A run *over budget* when the ceiling fires takes no host checkpoint:
committing there would push a task with no money left into GATE and spend the
suite it cannot pay for, and `EXHAUSTED` is the outcome it earned. A run ended
by some *other* bound — idle, wall-clock, a crash — takes none either: the
salvage turn is spent on one measured pair of facts, and widening the free
checkpoint to every abnormal ending is a separate argument from the one this
item makes, on a path whose retry is already warranted. Neither is free of
cost, and both are worth revisiting with a measurement rather than a guess. It
also does not raise `max_turns` or spend
the leftover budget on more implementation (the failed run did not need more
turns; it needed to have committed at turn 20), and it does not steer a turn
while it is running — the host cannot inject an instruction mid-turn, only
resume at the boundary it already owns.

**The decision this item also records: a dirty, uncommitted `/work` at
teardown is still never packaged, even after this exists.** The tempting
second half — when the salvage turn also produces nothing, export the working
tree's diff anyway, on the theory that *some* record beats none — was
considered and rejected. Control artifacts are extracted and hashed the moment
they are produced and never re-read from `/work`; a file left in the workspace
is a claim, not a record. A working-tree diff that reached `patch.diff` would
be packaged as though it had passed gates it never faced, and `committed`
exists precisely to refuse that at GATE. If a diagnostic dump of the dirty tree
turns out to be worth having for triage, it needs its own name, its own place
PACKAGE never reads, and its own spec — not a quiet exception carved into the
one artifact the operator trusts.

**What review added after the cell, and what it left open.** Three holes the
gates could not see: the host checkpoint fired only when the salvage turn was
*cut off*, so a salvage that returned cleanly having committed nothing — a
commit hook rejecting it is the likely shape — lost the work it was spent to
save; the crashed-turn watch line keyed on `is_error`, one of the four things
`run_agent`'s own failure predicate ORs, so a turn that crashed after emitting
a clean result still read as "finished and produced nothing"; and the salvage
turn inherited the implement turn's cost as `_reconcile_cost`'s fallback,
which bills a five-turn `git commit` at a 120-turn turn's price and can book
`EXHAUSTED` on a task the salvage just rescued.

**What the second review round found, all four in the same shape.** The cost
scaling was applied in one direction only: the salvage turn was correctly given
a scaled-down fallback, and then its own small figure was carried forward as
`last_cost`, becoming the crash fallback for the *next* turn — which runs on the
full ceiling. That reopens §4.1's budget-that-stops-counting one hop downstream
of where the scaling closed it, so `last_cost` now keeps the implement turn's
figure across the salvage. `commit_dirty` raises rather than returns when a hook
rejects the commit, so a host checkpoint on a tree the repo's own `prek` hooks
refuse converted an earned `NOT_IMPLEMENTED` into an infrastructure abort,
charged to nobody: the salvage path now catches `CellRuntimeError`, says so on
the watch line, and lets the `commits_ahead` re-measure decide. The same shape
is still live in the repair loop's own checkpoint, where the tree is not known
dirty and so is less likely to fire — it needs its own spec. And
`cut_off_at_turn_ceiling` read `terminal_reason` alone where `run_agent` keys on
`subtype`; the ledger row carried both, and a result event arriving without the
one field would have skipped the salvage in silence, which is indistinguishable
from a control that ran and found nothing.

**Owed to an operator, by design.** `DESIGN.md` and `CONTEXT.md` are `forbidden`
to `SA-0028`, and three edits are outstanding: §5.3's account of IMPLEMENT
describes one checkpoint and there are now two; §4.3's "doneness is measured,
never reported" gains the qualification this item argues for (a turn cut off is
not a turn that reported doneness), and its own table still says IMPLEMENT is
measured `base..HEAD` when the code has measured from the plan turn's head since
item 18; and `CONTEXT.md` grants bare-caps status to phases plus the plan
checkpoint by name, which `SALVAGE:` now needs too — it is a turn at a boundary,
deliberately not a phase, the same entry the plan checkpoint carries.

---

## 35. An inertness guard names its own successor, and nothing checked the successor could reach it

**Status:** **done** — `SA-0027`, 2026-09-01.

`SA-0022`, `SA-0025` and `SA-0026` each shipped a capability inert on purpose,
asserting it with a test that the capability is off and a comment naming which
spec will flip it. Nothing checked the named spec's `touches` could reach the
file carrying that comment, and `SA-0026`'s own review is the corpse, twice:
`tests/test_package.py`'s guard (planted by `SA-0025`) asserted the literal
string `parent_branch` never appears in `saffron/cli.py`, but that file was
not in `SA-0026`'s `touches`, so its agent could neither edit the guard nor
run the gates against it — it spelled the keyword
`{"parent" + "_branch": ...}` to dodge the match instead, said so in a
comment, and logged the box it was in as this file's item 33; and
`saffron/cell/session.py` and `saffron/phases/package.py` each carried a
comment saying stacking was off, both `forbidden` to `SA-0026`. Both review
lenses flagged the first, both files were corrected by hand for the same
reason: the file was never one the spec retiring it could reach. A `git grep`
against the mirror at `base_sha` costs no export, no working tree and no
network; what it prevents is a full cell paying for a choice between a false
green and a `scope` refusal on work the spec was right to do.

**Done looks like, and is:** the convention, stated in code
(`mirror.py`'s `retirement_markers` docstring, not only here) — a comment or
docstring carrying `saffron:retired-by <SPEC-ID>` declares that its file
asserts something that spec is expected to falsify.
`mirror.retirement_markers(mirror, sha)` reads every marker out of a bare
mirror with `git grep -n -z`, no export or checkout, answering `[]` rather
than raising on a repository with none (`git grep` exits 1 on no match —
`error` ≠ `fail`). `scheduler.retirement_refusal(spec, markers)` is a pure
refusal in `protected_touch_refusal`'s own shape (item 28), read with
`scope.matches` — the same function `scope`, `integrity`, `size` and item
16's criterion-path refusal already share: a marker this spec's `touches`
cannot reach refuses, naming the file and the declared `touches`; one inside
the spec's own `forbidden` refuses too, worded differently, since "may not
touch it at all" and "touches doesn't reach it" are different operator
fixes. Empty `touches` skips the second check outright — item 16's own bug
guard, since an empty list is a bug awaiting DIAGNOSE, not a spec that failed
to declare — but not `forbidden`, which a bug spec can carry regardless.
Wired into both pre-cell paths item 28's refusal reaches: `build_queue`
(gate 0) and `cli._run_cell`, best-effort against the mirror the way
`_protected_paths_at` already is. A marker naming a spec id nothing in the
directory (or `specs/done/`) declares gets its own line in `build_queue`'s
refusals — item 24's `done/` rule, applied to this class of dangling
reference.

**What this still cannot see.** Reachability, not intent: a marker naming an
id that exists is not flagged even if that spec is long `MERGED` or
`REJECTED`. It garbage-collects nothing — a guard's own removal deletes its
marker by construction, but one left behind some other way still reads as
live. And it is opt-in: a heuristic over every `SA-NNNN` mention would refuse
most of this repository, which cites spec ids as attribution far more than as
a claim about the future — a capability shipped inert *without* a marker is
as invisible to this refusal as it was before.

**What review added after the cell.** Two holes the gates could not see, both
the same shape: `git grep` cannot tell a line that *writes* a marker from a
line that *is* one. A spec must quote the marker it arms in its own
acceptance criteria, so every such spec read back as carrying a marker at its
own path and refused itself — naming its `forbidden` list, which was not the
cause. `.saffron/specs` is now excluded from the grep: a spec is where a
marker is discussed, never where one lives. `tests/**` deliberately is *not*
excluded, because `SA-0025`'s own inertness guard lived in a test file — so
`tests/test_mirror.py` spells the string by concatenation instead, having
otherwise shipped four dangling markers into this repository and four
permanent refusals into every `saffron queue`. And a third limitation for the
list above: the empty-`touches` guard means a bug spec is checked against
markers only *before* DIAGNOSE populates its `touches`, never after — the
same pre-cell-only hole item 28's sibling refusal has.

**What the second review round found, and three more blind spots it named.**
The item shipped carrying a stray diff3 conflict marker — one line, naming an
in-cell commit that exists in no history here — through two review commits. In
a file the project treats as a primary record, that is the workspace-claim
failure in documentation form. And a dangling-marker line asserted more than
the scan had read: `known_ids` is built from the spec files that *parsed*, so a
marker naming an id declared only by an unparseable file was called a dangling
reference. It now says how many files did not parse, the way
`_dependency_refusal` already qualifies the identical case.

Three things this refusal still cannot see, all named rather than fixed:

- **A marker whose id the regex cannot parse is dropped in silence.**
  `saffron:retired-by SA_0027`, a stray colon after the keyword, or a marker
  inside a binary file all *match the grep* and then vanish — the false green
  this item exists to end, one layer down. Fixing it is a decision and not a
  one-liner: this repository writes the literal keyword in a regex, in three
  scheduler f-strings, in two test writers and in this paragraph, and every one
  of those would become a "malformed marker" line on every `saffron queue`. The
  permissive id parse is kept deliberately for the same reason — trailing
  garbage (`SA-0031-extra`) resolves to its prefix and so reaches an operator
  as either a named refusal or a dangling line, where a stricter pattern would
  return it to silence. Visible-and-possibly-misattributed beats invisible.
- **Only `.saffron/specs` is excluded, so a document that writes a real id
  arms a real marker.** This file, `CLAUDE.md` and `DESIGN.md` escape today
  only by writing a placeholder rather than a concrete id. Excluding `docs/**`
  was considered and rejected: `docs/` is a target repo's convention, not
  Saffron's, and core knows nothing about a repo's layout (§2.1). `.saffron/`
  is excluded precisely because it *is* Saffron's own path.
- **The repo-wide `protected` list is not consulted.** `retirement_refusal`
  reads `spec.forbidden` but not `policy.yaml`'s `protected`, which `_refuse`
  already holds. A marker in a protected path, named by a spec whose `touches`
  glob covers it, is admitted here and dies at the plan checkpoint instead —
  the same corpse this refusal exists to prevent, one list over.

---

## 36. The event schema wants its own `DESIGN.md` §4 subsection, and nothing can write one

`saffron/events.py` fixes the nine kinds, the `kind` discriminator and the
timestamp representation, and `DESIGN.md` carries no event schema at all.
`DESIGN.md` is `protected`, so no cell can add one.

Done looks like: a new §4.x naming the nine kinds, the wire discriminator and
`events.jsonl`'s one-file-per-task, no-rotation ceiling — by hand, after
`SA-0040`, when the shape has stopped moving.

## 37. `events.Terminal` and `CONTEXT.md`'s "terminal state" are two different things

`CONTEXT.md` reserves **terminal state** for the states that reach the operator.
`events.Terminal` means the five ways an IMPLEMENT turn ends having committed
nothing. Two of the five map onto a terminal state, which makes the collision
easy to miss rather than hard.

Renaming was deferred because `SA-0029`'s criteria and `SA-0030`/`SA-0040` all
cite `Terminal`. An earlier draft of this item said the name was `DESIGN.md`
§4.1's; it is not — see item 36. Found reviewing PR #91.

Done looks like: `TurnEnded` across the three specs, or a `CONTEXT.md` entry
saying the two terms are deliberately distinct. Protected either way, so by
hand, and worth settling before `SA-0040` and `SA-0038` render the word.

## 38. `events.Phase` splits `GATE ⇄ REPAIR`, and `CONTEXT.md` does not

`CONTEXT.md` names six phases, counting `GATE ⇄ REPAIR` as one; `events.Phase`
lists seven, because a gate attempt and a repair turn print different lines.
The split is probably right and is currently held by a comment and a test.

Done looks like: `CONTEXT.md` saying whether it is sanctioned, and the `Literal`
following. Protected, so by hand. Second divergence — see item 37.

## 39. `types` is a blocking gate that can never fail

**Status:** **done**, by hand, on `joel/ty-typechecking`. The gate executes
`ty` (pinned exactly in `pyproject.toml`), `[tool.pyright]` is gone, a prek hook
carries it into `make check` and CI, and `.saffron/Dockerfile` asserts
`ty --version`. `policy.yaml` is unchanged, as this item predicted. Two things
it did **not** predict, both measured:

**ty, not pyright, and the reason is the cell.** The `pyright` PyPI package is a
Node wrapper that downloads a runtime on first use. `cell-base.python` has no
node, and the proxy allows one host — so the download takes a 403, the same
failure the Dockerfile's `UV_NO_SYNC` note already records for `uv run`. ty is a
single binary from ruff's vendor. It is also the better surface for the agent in
the loop: 0.09s against 1.97s on this tree, 23 KB of `concise` output against
pyright's 127 KB of JSON, and no duplicates (13% of pyright's 206 diagnostics
were exact repeats). Deduped, the two agree on the same production defects.

**"neither touches `saffron/`" was wrong**, and usefully so — turning the gate on
found 11 real defects in it: five `int(cursor.lastrowid)` where sqlite types the
value `int | None`, a `list[str] | None` iterated in `criteria`, two
`list[X] = ()` defaults in `pr_body`, and `fields()` on an untyped `_KINDS`.

**The mutation this item was written about is caught by nothing, and that is not
a ty limitation.** Measured against the shipped gate:

| mutation | `types` | `test_the_enumerations_are_pinned` |
|---|---|---|
| `ceiling: Ceiling` widened to `ceiling: str` | pass | pass |
| `Terminal` dropped from the `Event` union | **fail** | pass |
| a member removed from `Ceiling` | **fail** | **fail** |
| a member added to `Ceiling` | pass | **fail** |

Widening a type cannot error in any checker unless some code exercises the wider
value, and none does; pyright behaves identically. So this item's reading of
`test_the_enumerations_are_pinned` as a "substitute" is backwards — it is the
only control over a member quietly *added* or renamed, and it stays. The row the
gate uniquely covers is the dropped union member.

Caught in review, and the sharpest finding of the branch: the first version set
`[tool.ty.environment] python = ".venv"`. A cell worktree is a fresh
`git init`/fetch/checkout and `.venv` is gitignored, so it is never present —
and a configured environment ty cannot resolve is a hard failure, exit 2 with
nothing on stdout, which this gate correctly calls `error`. `error` aborts the
attempt and is charged to nobody (§5.4), so a blocking `types` gate would have
aborted every attempt against this repo. Item 39 would have been closed by
replacing a gate that could never fail with one that could never run. Reproduced
against a clean clone before fixing; the fix is that ty resolves the environment
from its own executable, so `/opt/venv/bin/ty` finds `/opt/venv`. The test that
should have caught it now exists — none of the others paired the repo's own
config with a tree shaped like a cell's.

The parser is `concise` and reconciles against ty's own `Found N diagnostics`
trailer, so a diagnostic it cannot key (one carrying no line, a message shape
that moved) is `error` rather than a smaller repair target than the real one.
Exit codes beyond 0 and 1 are `error` for the same reason. ty's only JSON output
is its `gitlab` format, which is a schema name and not a destination; a flag
naming a forge this repo does not use would read as an integration it is not.

`# ty: ignore` joins `integrity.suppressions`. ty honours it, and before this
branch that did not matter because nothing enforced types; a blocking gate with
a suppression syntax the anti-gaming gate cannot see is the hole that gate
exists to close.

One standing cost, recorded rather than fixed: `docs/evidence/scripts/` is in
scope, so every future evidence script — a verbatim record of something already
executed — must type-check or a blocking gate goes red. Three existing ones
needed an `assert spec and spec.loader`.

Also fixed in passing: the gate's implementation was first written as
`.saffron/gates/types.py`, which sits on `sys.path[0]` and shadows the stdlib
`types` every `import json` reaches through. It crashed under one interpreter
and survived under another, writing nothing to stdout — a gate that did not run,
reported as nothing at all. Renamed `typecheck.py`, with a test asserting no
gate script shadows a stdlib module name.

`.saffron/gates/types` emits `skip` unconditionally, `policy.yaml` declares it
`blocking: true`, and `pyproject.toml` carries a configured `[tool.pyright]`
block that nothing runs — pyright is not a dependency, a hook, or installed.
`policy.yaml`'s own note on `shacl`, five lines below, states the principle this
breaks: *a control that reads as present and is not is the founding defect of
Appendix I.*

Measured while reviewing PR #91: mutations replacing `Ceiling` and
`TerminalReason` with bare `str`, and removing `Terminal` from the `Event`
union, all left the suite green. `saffron/events.py` is a module whose whole
value is type safety, and `tests/test_events.py` now hand-rolls
`test_the_enumerations_are_pinned` as a substitute.

Done looks like: pyright as a dev dependency and `.saffron/gates/types`
executing it — the gate is already declared and already blocking, so nothing in
`policy.yaml` changes. Or, if that is not wanted, the gate stops claiming to
block. Either is a repo-side change and neither touches `saffron/`.


## 40. A host-side fix round can undo a gate the cell passed

`SA-0029` (PR #91) left its cell at 548 changed lines, inside the 600 a
`feature` gets. Two host-side review rounds took it to **863**. The `size` gate
runs inside the cell, against the cell's own diff; nothing re-runs it after the
operator commits review fixes to the branch, so the branch merges failing a
blocking gate it passed on the way out.

Most of the growth is tests, and that is the second half of the finding:
`_changed_lines` counts the whole diff, so a spec whose acceptance criteria
demand thorough tests is charged for satisfying them. `SA-0029` has fourteen
criteria, and both reviews of it added tests precisely because criteria were
being held up by comments. Cutting those to reach 600 would trade a real
control for a number.

Done looks like: the loop running `size` (at minimum) against the branch before
it is marked ready, and a decision on whether the ceiling should count test
lines at all — §5.4 sets one number for a diff whose test half is mandated
elsewhere. Recorded rather than fixed here: PR #91 is over the ceiling and is
being merged over it deliberately, with this item as the record.


## 41. `NO_PROXY=""` denies a cell its own loopback, so a test that stands up a local server fails at baseline forever

**Status:** **done**, by hand, on `joel/cell-loopback-not-proxied`. `proxy_env`
returns `NO_PROXY: "127.0.0.1,localhost"`, and a driven test asserts the probe
reaches a server started beside it while the upstream stays proxied. The
alternative this item offered — marking the failing test `cell` — was **not**
taken: it passes on the host, and excluding it would have hidden the defect
rather than fixed it. One correction to the reasoning below, from review: the
open question is not whether `--internal` makes these variables inert.
`DESIGN.md` §5.1 records that an `--internal` network still routes to the host
gateway, which is why `assert_host_is_unreachable` exists. What makes the
change safe is narrower and measured — `10.88.0.1` matches neither `NO_PROXY`
entry, so nothing the gateway exposes becomes reachable.

`saffron/cell/proxy.py:proxy_env` returned `{"HTTPS_PROXY": url, "HTTP_PROXY":
url, "NO_PROXY": ""}`. Empty means *nothing* bypasses squid — `127.0.0.1`
included. `test_the_probe_script_itself_answers_a_401` binds an `HTTPServer` on
loopback and probes it
with `preflight._UPSTREAM_PROBE`, which uses `urllib` and so honours the proxy
variables. The container's request to itself is routed out to squid, which
allowlists only the upstream, and is denied.

Measured on `SA-0040`, 2026-09-01. In-cell baseline: `1 failed, 1094 passed`.
Same commit on the host: `1 passed`. That run's teardown printed ten of these,
one per suite execution across baseline, two gate attempts and the
post-rebuttal run:

```
teardown: proxy DENIED … TCP_DENIED/403 3367 GET http://127.0.0.1:37283/v1/models
```

Three costs, in increasing order of seriousness:

- **Every cell run starts with a red `tests` gate.** Baseline subtraction
  absorbs it correctly, which is exactly why it has gone unnoticed since the
  proxy was wired.
- **It misleads the critic.** `SA-0040`'s correctness lens opened its blocker
  with "the `tests` gate reports 1 failure in this run", reasoned to the
  nearest new test, and raised a blocker against the golden fixture's digest.
  The digest was fine — mutating it fails the assertion — but the rebuttal
  turn's artifact was itself lost to a JSON parse error, so the pull request
  shipped a `confirmed` disagreement founded on this line. One environment
  papercut cost a lens finding, a rebuttal, and an operator adjudication.
- **It trains the operator to skim the denials.** `teardown: proxy DENIED` is
  the channel that would show a cell trying to reach something it should not.
  Ten lines per run that are one repo test talking to itself is noise in the
  one place noise is most expensive.

Done looks like a decision, not a patch. `NO_PROXY=""` is the correct isolation
posture for anything off-box and must not be widened to hosts. The open
question is whether loopback *inside the container* — which is the cell
itself, and reaches nothing the cell does not already have — belongs behind
the boundary at all. If it does, the alternative is that `saffron`'s own suite
cannot contain a test that binds a socket, and `test_the_probe_script_itself
_answers_a_401` should carry the `cell` marker and say so.


## 42. A rebuttal lost to a trailing comma is recorded as a confirmed disagreement

`phases/rebut.py:207` discards a rebuttal artifact that is not the schema and
returns `RebuttalTurn(error=...)`. That is deliberate, and the comment says
why: the plan checkpoint re-prompts once (`cell/session.py:404`) because a
rejected plan costs an attempt that has not happened yet, whereas *"this
attempt is already made, and HEAD already says what it did."*

`SA-0040` (PR #93) is the case where the second half of that sentence does not
hold. Measured 2026-09-01:

```
REBUT: 0 rebuttal(s), HEAD moved, not the schema: Illegal trailing comma
       before end of object: line 6 column 1116 (char 1186)
```

The turn cost $2.59, edited the branch, and conceded one of the two blockers —
`describe`'s `Baseline` branch was rewritten and a test added, and the critic's
re-read correctly marked that one `withdrawn`. Its *arguments* were what the
trailing comma destroyed. On the other blocker the critic then wrote
`confirmed: The implementer offered no argument and made no visible change`,
and that finding was false: the fixture digest it doubted is captured, not
typed, and mutating it fails the assertion at `tests/test_events.py:798`.
Nothing needed to change, and there was no surviving argument to say so.

So the operator inherits a pull request body asserting a confirmed
disagreement, founded on a lens finding that was itself founded on the
unrelated red baseline in item 41. "HEAD already says what it did" is true only
for a reader who re-reads the diff against every finding; the generated body
says the opposite, and the body is what gets read.

`SA-0034` (plan Task 6) is the natural home for the *recording* half — it is
already a bug spec about a rebuttal outcome that is not written down — but its
`forbidden` list excludes `saffron/report/**`, and no spec in part 3 touches
`pr_body.py` either. The visible half has no home in that plan yet.

Done looks like the artifact's *shape* failure not being silently equivalent to
the agent having no answer. Cheapest honest fix is not a re-prompt: it is that a
`RebuttalTurn` carrying `error` renders in the pull request body as
**"the rebuttal was unreadable"** rather than as an implementer who declined to
argue, and that `HEAD moved` — already recorded in `rebuttal.json` — is shown
next to it. Whether a malformed rebuttal is also worth one re-prompt is a
separate question from whether the record should imply an answer that was never
read.

## 43. Two of `cell/session.py`'s events never fit a kind, and `emit` is not the whole output seam

`SA-0030` migrated all 47 `watch(...)` call sites in `cell/session.py` to
`emit(<Event>)`, against `events.FAMILIES`. Two did not, by design —
`events.FINDINGS[0]` names them: the task's own terminal announcement
(`f"{outcome}: ${spent:.2f} spent, session {session_id}"`) and the rate-limit
rejection line. Neither `Terminal` (scoped to the five zero-commit IMPLEMENT
endings) nor `Budget` (a ceiling/value/limit triple) fits an arbitrary outcome
word and a session id without a tenth kind, which this spec's own out-of-scope
section forbids. Both stay direct `print()` calls in `_drive_cell`, which means
`events.jsonl` never carries them — `read_log` plus `describe` reproduces every
other printed line in order, but not these two. A future report reading
"what did this task's own log say happened" has to fall back to the ledger's
`tasks.state` for the outcome word, which is already there and already typed;
the gap is real but has a working substitute, which is presumably why `SA-0029`
scoped a tenth kind out from the start.

**The second half of that gap has no substitute and was not disclosed until
review found it: `emit` is no longer the supervisor's total output seam.**
Those two `print()` calls go to process stdout whatever the caller passed.
A caller supplying its own `emit` — which is exactly what `SA-0042` is
specified to do from `cli.py`, and what any batch or headless consumer would
do — still gets two lines it cannot redirect, and the one it most wants is the
task's own terminal announcement. Measured on `saffron/SA-0030`: driving
`run_one_cell(..., emit=seen.append)` without the test harness's
`session.print` double leaks `READY_FOR_REVIEW: $0.40 spent, session sess-1`
to stdout; at base, `watch=` captured 100% of output. Note the harness hides
this — `tests/test_session.py` patches `session.print` with `raising=False`,
so the double silently no-ops if those calls ever move. Done looks like the
tenth kind `SA-0029` scoped out, or an `emit`-shaped sink for lines no kind
carries; not a third `print`.

**Closed by `SA-0041`, 2026-09-02.** `phases/implement.py`, `phases/review.py`
and `phases/rebut.py` were `forbidden` to `SA-0030` and called a plain
`watch(str)` with a line they had already fully formatted — `agent: `,
`agent: (raw) `, `REVIEW: ` or `REBUT: ` were the only four prefixes those
three files ever handed it. `session._phase_watch` recovered the event those
strings were always going to be by matching on that prefix and slicing it
off, which was correct only because no other prefix reached it. `SA-0041`
migrated those three files to construct `Agent`/`PhaseStart` events directly
and call `describe()` themselves — `implement.run_agent` gained a required
`spec_id` and now emits `Agent(event=<dict>)` at the point the cell's own
dict is still available, instead of flattening it to prose first — which is
what let `_phase_watch` itself, both constructions, be deleted outright.
`SA-0031`'s plan to migrate `cli.py`/`phases/package.py` in the same spec is
what died at 141 turns; `SA-0042` carries that half forward on its own, since
`package()` runs outside `run_one_cell` and never received the supervisor's
`emit` in the first place.

**The first half closed by `SA-0042`, 2026-09-02; the second half is still
open and this spec moved against it.** `cli.py` now builds one `emit` fan-out
— print plus a task-scoped `EventLog`, the same shape `session._default_emit`
already used — and hands the identical object to both `run_one_cell` and
`package()`, so PACKAGE's events finally reach `events.jsonl` too. **Seven** of
`package.py`'s eight `watch(str)` call sites and `cli._resolve_stacked_on`'s
two are now `emit(<Event>)`, against existing kinds and with no message change.

The eighth did not migrate, and it is the mirror image of
`events.FINDINGS[0]` above: `reverify`'s `"re-verify: {label} suite at {sha}"`
is `events.FINDINGS[1]`'s own named exception — no `PhaseStart` label fits a
lower-case, hyphenated step without widening `LineLabel`, which needs the
forbidden `events.py` — so it stays a direct, unconditional `print()`.

That leaves the second half of this item worse, not better, and review is what
said so. `session.py`'s two `print`s are untouched (forbidden here), and
`package.py` now adds a **third** — precisely the shape the done condition
above rules out. It is also a small regression in kind: before, a caller could
pass `package(watch=…)` and capture or silence the `re-verify:` line, and no
caller can redirect it now. Done is unchanged: the tenth kind, or an
`emit`-shaped sink for lines no kind carries. Three prints, not two.

One further consequence for whoever takes that on: `session._default_emit`'s
docstring now says `cli.py` "never passes `emit`", which this spec made false
— `cli.py` is the only production caller of `run_one_cell` and always passes
one, so the `emit is None` branch is now reached from tests alone.

## 44. A single turn can overshoot the budget ceiling, because the check runs before it

`_over_budget` gates a turn on what has been spent *so far*. It cannot bound
what the turn about to run will cost, and a turn's cost is not knowable until
it ends.

Measured on `SA-0031`, 2026-09-01. Admitted under an $18.00 budget with roughly
$6 spent, its IMPLEMENT turn ran to the 140-turn ceiling and cost **$13.18 on
its own**, ending the run at **$19.17 — 6.5% over a ceiling it never checked
against.** The ledger row records `budget_usd 18.0, spent_usd_est 19.165`.

The overshoot is bounded only by the turn ceiling and the wall clock, which are
the same two bounds that let the turn get long in the first place. A task with
`max_turns` raised — the obvious response to a turn that ran out of turns — has
a proportionally larger overshoot available to it.

Done looks like a decision about which of two honest options to take, not a
patch: charge the ceiling *before* a turn against a worst-case estimate and
refuse a turn that could exceed it, or accept that `budget_usd` is a
best-effort bound and say so where it is declared. What it should not stay is a
number the system reports as a ceiling and enforces as a suggestion.

## 45. An `EXHAUSTED` run that made commits pushes no branch, so its work survives only as a patch

`SA-0028` closed the door where an implement turn dies on its ceiling with
*nothing* committed. This is the door beside it: commits exist, gates are red,
the budget or the attempts are gone, and PACKAGE never runs — so nothing is
pushed and there is no pull request.

Measured on `SA-0031`: six commits, 39 new gate failures, `$19.17` spent, and a
ledger row reading `branch saffron/SA-0031, pushed_sha NULL, pr_url NULL`. The
only survivor is `teardown`'s `patch.diff`. It is real work — it applies
cleanly to `saffron/SA-0030` and leaves 15 failures, so it was roughly 85%
finished — and nothing in the system will ever look at it again.

The cost is not the disk space. It is that the operator's only route back to
$19.17 of work is to know the batch tree exists, find the patch, and apply it by
hand — none of which any output tells them.

Done looks like pushing the branch on any terminal state that made commits,
recording `pushed_sha`, and saying so on the way out. A pull request is a
separate question — red gates should not open one — but a branch nobody can
reach is not a decision, it is a leak. The split design
(`docs/superpowers/specs/2026-09-01-splitting-a-too-wide-spec-design.md`) needs
this independently: its mid-flight split hands child 1 the parent's branch, and
there is no branch to hand.


## 46. `events.jsonl` now persists an untrusted cell's raw output verbatim, and nothing bounds or scans it

`SA-0041` makes `implement.run_agent` emit the parsed cell event under
`Agent.event`, which is the fix that spec exists for — the dict was previously
flattened to prose before the host ever saw it, so `Agent.event` was
permanently `None`.

The side effect, raised by that run's contract lens: **what reaches persistence
changed shape.** Before, only `_describe`'s bounded renderings were written — a
`tool_result` became the fixed string `agent: tool ok`, `text` was truncated at
160 characters and `tool_use` at 120. Now the raw dict is written verbatim to
`~/.saffron/batches/v0/<id>/events.jsonl`, and for `text`, `tool_use` and
`tool_result` that dict can carry full file contents, whole command outputs, or
anything else an untrusted cell chose to put on stdout.

Two things follow, neither addressed anywhere:

- **Volume is unbounded on the path that matters.** `SA-0041` bounded the raw
  quarantined line at capture (`implement.QUARANTINE_BYTES`, 8192) after review
  measured 5 MB of stdout writing 5 MB of log. That closes the accidental case
  only: the same payload wrapped in nine bytes of JSON takes the `Agent.event`
  path and still writes 5 MB, because bounding it needs `saffron/events.py`,
  which that spec forbids. One value, both paths, is still the open decision.
- **The `secrets` gate never sees it.** That gate reads the diff. A batch tree
  artifact is not a diff, so a credential a cell printed to stdout is persisted
  host-side and scanned by nothing. §5.4 lists `secrets` as a v1 gate, so this
  is a gap that widens rather than one that exists today — which is the reason
  to record it now rather than after it is built.

Neither the golden fixture nor the unit tests can see this: both exercise small
synthetic dicts, so the change is invisible to the suite by construction.

Done looks like a decision about what the log is for. If it is an operator's
record of a night, the rendered line is sufficient and `Agent.event` should be
bounded the way the display already is. If it is evidence, it needs a size cap
and to be in the `secrets` gate's reach. `SA-0041` could not make that choice —
`saffron/events.py` is `forbidden` to it — and made the reachability fix it was
asked for, which is correct.


## 47. Every gate attempt in `events.jsonl` claims zero commits and zero spend, and part 3 is built to read it

`cell/session.py` emits an `Attempt` for each GATE and REBUT decision with
`commits=0, spent_usd_est=0.0` — four call sites — and the rebuttal-time gate
events additionally hardcode `attempt=1`, which is wrong whenever the repair
loop has already reached attempt N.

None of it is visible. `describe`'s `Attempt` branches return on `aborted`,
`drift`, `new_failures`+`decision`, or `new_failures` before ever reaching the
fallthrough that renders `commits` and `spent_usd_est`, so the terminal is
correct, the golden fixture is indifferent, and no test can see the fields at
all. The defect is entirely in what the log *keeps*.

Two consequences, both for a reader rather than an operator:

- **`0` cannot be told from "not computed".** `events.py` sets the opposite
  convention two dataclasses away, in as many words: *"`None`, never `0`: a
  skipped or errored gate had no count computed."* `Attempt.commits: int`
  cannot express it, so a consumer reads a real zero and a missing measurement
  identically.
- **Summing `spent_usd_est` across rows is wrong twice over** — the gate rows
  contribute nothing, and the IMPLEMENT row is *cumulative*, not incremental.
  Measured on `SA-0041`, 2026-09-02: it emitted `IMPLEMENT: 6 commit(s), $11.31
  spent`, and the ledger's attempts for that task read $2.457 and $8.856. The
  line is the running total, so two IMPLEMENT rows in one run double-count.

This is filed now because of who reads it next. `SA-0035`–`SA-0039` build §6's
pages from exactly this data, and a page that sums a column of zeros and one
running total will render a confident wrong number rather than fail. `SA-0034`
is the neighbouring case for the ledger; this is the same question for the log.

Done looks like `commits` and `spent_usd_est` being `int | None` and
`float | None` on `Attempt`, set only where they were measured, and the
rebuttal path carrying the attempt number it actually ran at. That needs
`saffron/events.py`, which `SA-0041` and `SA-0042` both forbid — so it is
either a spec of its own or the first thing part 3's first spec does.


---

## What is *not* here, deliberately

DIAGNOSE and `SCOPE_REVIEW`, the scheduler's conflict sets and stacking, `saffron
gc`, multi-repo, the merge train, and the `secrets`/`revert` gates. All are
v1+ by `DESIGN.md` §9's own build order, and none of them is blocked by anything
above. `size` left this list on 2026-08-25: it is built and unwired, which is
item 17. §4.2's own argument applies: at a two-deep queue they arbitrate contention
that never arrives.
