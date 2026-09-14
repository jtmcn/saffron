# Feedback on run-saffron-spec-loop (first run after the rework, 2026-09-13/14)

## Summary: what to change first

Ranked by cost to the loop this run, measured, not by how often each came up.

1. **The ordering and `next` serialise the tail** (items 10, 14, 17). A fan-out parent
   (SA-0080, with 3 descendants) sorted fifth, so no independent spec was left once it
   ran. Its review and its children's reviews each sat on the critical path. `next` also
   names a child that can't start, exits 0, and keeps saying "push its review commits
   first" after they're pushed. Fix: sort by descendant count within a priority tier, and
   have `next` print the first spec startable now, checking the parent's review push
   against `pushed_sha`.
2. **Nothing reviews the delegate's own commits** (items 19, 20). My review commit took
   #247 over its `size` ceiling (294 → 367 against 300), and I nearly shipped a module-scope
   import that made a witness error at collection against base. Fix: step 2c.6 requires each
   review-added witness to fail at base, and prints the branch's size against its ceiling
   before the push.
3. **Step 1 never shows the operator the queue** (item 5, raised by the operator). Fix:
   `snapshot` prints titles, budgets, the summed budget and the queue's refusals, and the
   step ends by showing them.
4. **Mechanical steps done by hand** (items 2, 6, 7, 22). The host allowlist isn't in the
   command block, review prompts are filled in by hand, the Monitor never exits, and
   `pattern` matches the agent's own greps. Fix: `driver.py command|prompt SA-NNNN`, and
   an anchored `pattern` whose grep ends on the CLI's final state line.
5. **GOTCHAS gaps** (items 11, 16, 18, 23). Probes need pyc caching off. A turn-ceiling
   line isn't terminal. A cell can run to ~1.7× its budget. `stack`'s sibling warning is a
   false alarm when the parent is two layers down (measured on GitHub, #249).

**What worked and should stay:** the two-seat split (every seat-only finding on #243–#250
came from running a probe, and the seats found a real defect the lenses missed on every
one of the eight PRs, #243–#250, including two where all three lenses came back clean);
the seats'
"read-only, another process edits it" line; `make check > file; echo $?`; `stack` as a
mid-loop dry run; `stack --execute`'s read-back.

---

Observations, in the order they happened. Each: what happened, what the skill said, suggested change.

1. **`snapshot`'s sibling note miscounts, or reads that way.** Four specs declare no
   `depends_on` (78, 82, 79, 80), and the note says "3 spec(s) declare no depends_on". It
   is probably counting the roots above the bottom one (the ones `rebase` would move), but
   the sentence says something else. Fix: "4 specs declare no depends_on; `rebase` would
   move the 3 above the bottom one", or change the count to match the sentence.
2. **The host allowlist is in GOTCHAS, not the command.** SKILL.md step 2a's command leaves out
   `SAFFRON_ALLOW_HOST_PROCESS` and mentions it in a sentence after the block. On this host
   every cell needs it, so a delegate who copies the block verbatim fails preflight. Fix: put
   `${SAFFRON_ALLOW_HOST_PROCESS:+SAFFRON_ALLOW_HOST_PROCESS=…}` in the block, or have the
   driver print the full command (`driver.py command SA-NNNN`) with the host's var already
   included, the way `pattern` prints the grep.
3. **The push question ended up asked twice.** The skill says to ask once for ordinary
   pushes and to ask about every force-push separately. Right after approving ordinary
   pushes, the operator also approved force-pushes to this loop's branches without being
   asked. The step 4 `rebase` push is the only force-push the skill plans for, and it's
   several hours away. Fix: ask both at the start as one question with two scopes (ordinary
   only / ordinary + force on `saffron/SA-*`), and say that a standing force grant still
   excludes `main` and every branch outside the loop. The same question should cover
   step 5's own branch and PR. Today the grant names `saffron/SA-NNNN` branches only,
   so the backlog PR's push needs a second question at the very end, when the operator
   is least likely to be around.
4. **The skill never says why it isn't `saffron batch`.** The operator asked mid-run. The
   reasons are all in the code, not the skill. `run_batch` takes `build_queue`'s candidates
   once, at start, so any child whose parent has not yet run is refused ("has no task at its
   current spec_sha"). It also runs cells back to back, with no gap for review commits
   before a child is cut from its parent's branch. And the only way it can be attended is
   through `watch`. Fix: one paragraph in SKILL.md's intro, "why attended cells rather than
   a batch", and a note on when a batch is the better tool (independent specs, no review
   between cells).
5. **Step 1 never has the delegate show the operator the queue.** The operator: "after the
   skill was invoked you should have checked the whole queue and displayed it." `snapshot`
   printed the order into tool output only, which the operator doesn't see, and the step's
   "Done when" is about `status`, not about the operator. Fix: step 1 ends by showing the
   operator a table (id, title, priority, depends_on, budget, risk) plus `saffron queue`'s
   refusals, so any spec the loop will *not* run is visible before the first cell. Better
   still, have `snapshot` print titles and budgets itself, and the summed budget as the
   loop's worst-case cost.
6. **Review prompts are filled by hand.** `{BASE}`, `{HEAD}`, `{SPEC}`, the diff stat and
   `{KNOWN}` from `findings.json` are all mechanical, and for a child `{BASE}` changes
   (the parent's branch, not main). Hand-filling that for 16 prompts over 8 PRs invites a
   wrong BASE. Fix: `driver.py prompt SA-NNNN --seat spec|standards` prints the filled
   prompt, with only `{WHAT}` left as a marked placeholder for the delegate to write.
7. **The `tail -F` Monitor never exits on its own.** It outlives the cell, so each spec
   needs a manual TaskStop, and one that's forgotten keeps streaming the old log.
   Fix: have the Monitor end on the CLI's final `SA-NNNN  <STATE>` line (a
   `grep -m`-free `awk '…; /^SA-[0-9]+ +[A-Z_]+/{exit}'`), or say in 2b to stop it.
8. **Worked: the seats' "read-only, another process edits it" line.** I applied the
   Standards seat's verified fixes in the main checkout while the Spec seat was still
   probing. The Spec seat saw the uncommitted edits, recognised they weren't its own, and
   left them alone; it probed only in its `/tmp/review-*` worktrees. Keep that sentence.
   SA-0078's two seats overlapped on 3 of 5 findings and each had one the other lacked
   (Standards: wrong phase name, item-71 citation; Spec: the P6 probe table). That supports
   the two-seat design.
9. **Worked: `make check > file; echo $?` and staging by name.** Both ran as written.
10. **`next` names a child that can't start yet, exits 0, and doesn't name the spec that
    can.** After SA-0082 packaged, `next` printed `note: SA-0083 is cut from SA-0082: push its
    review commits first` and `SA-0083`, exit 0. The delegate then has to read the order to
    find SA-0079 and start it by path. Exit 0 with a spec id normally means "start this", so
    a delegate scripting `next` would start the child from the unreviewed parent branch.
    Fix: `next` prints the first spec that can start *now*, and names the waiting child in a
    note ("SA-0083 waits on SA-0082's review push"). Alternatively, `next --ready`.
11. **Probes need bytecode caching off, and REVIEW-PROMPT doesn't say so.** On #244 the
    Spec seat's first pass swapped `worktree.py` faster than the pyc mtime check could
    notice, and reported one false "survived". It caught this itself and re-ran with
    caching off. A seat that didn't would file a false blocker, or clear a real one. Fix:
    the Spec seat's probe paragraph says "run every probe with `PYTHONDONTWRITEBYTECODE=1`
    and `-p no:cacheprovider`".
12. **Worked: the Spec seat's criterion walk found what the lenses missed, again.** On #244
    it found that the AC1 witness survives the one alternative the spec's own table calls
    equivalent (`-c diff.ignoreSubmodules=none`). A committed `.gitmodules` defeats that
    alternative, and no lens raised it. On #243 and #244, every seat-only finding came from
    running a probe, never from reading.
13. **"Operator's call" findings the delegate can settle.** The Spec seat marks a
    witness-strengthening test inside `touches` as "the operator's call". The skill only
    routes gate-bypass and outside-`touches` findings to the operator, so I settled this one
    myself (added the test). Fix: REVIEW-PROMPT tells seats which calls are the operator's
    (gate bypass, outside `touches`, fix incomplete without an outside change), so a seat
    doesn't escalate a test that sits within scope.
14. **`next` still says "push its review commits first" after they're pushed.** Once
    `a913d37` was on `origin/saffron/SA-0082`, `next` printed the same note. The driver
    can't tell that a review push happened, so the note is noise until the child starts,
    and a careful delegate may hold the child forever. Fix: compare
    `origin/saffron/<parent>` with the ledger's `pushed_sha` for the parent. If it has moved
    past PACKAGE's head, say "SA-0082's review commits are pushed (a913d37); SA-0083 can
    start". Otherwise say "none pushed yet". `status` would benefit from the same check: it
    shows `READY_FOR_REVIEW #243` whether or not the review has happened, so it can't
    answer "what's left to review?". A `reviewed a913d37` column would.
15. **Why a withdrawn blocker still goes in `{KNOWN}`.** SA-0079's adequacy blocker was
    "fixed" in REBUT by tightening a timing bound, and the lens withdrew it. But the
    rebuttal's own numbers (0.4–0.8s observed against a 1.0s bound) show the fix may have
    traded a vacuous test for a flaky one. The prompt's `{KNOWN}` line ("any blocker a lens
    withdrew after REBUT") is what surfaces that, so keep it. `rebuttal.json` holds the
    implementer's argument and is worth naming in step 2c.1 beside `findings.json`.
16. **A turn-ceiling line reads like a terminal one, and GOTCHAS doesn't say it isn't.**
    SA-0080's Monitor showed `IMPLEMENT: the session failed — the agent reached its ceiling
    of 40 turns`. The `pattern` grep passes it through because it starts with `IMPLEMENT`.
    To a delegate it looks like the cell is over. It isn't: §4.3 keeps the committed work
    (2 commits here) and the next gate suite measures it. Fix: a GOTCHAS "Starting cells"
    or "Recording" line: "`the session failed … ceiling of N turns` is not terminal; wait
    for `gates:` and the process exit." A spec whose IMPLEMENT hits the ceiling is also
    worth flagging in review (`max_turns` may be too low for the spec), which is a
    step-5 signal the skill doesn't collect.
17. **The order puts a fan-out parent last, so the tail runs serially.** SA-0080 is the
    ancestor of three of the eight specs (81, 84 and 85 via 84), yet it sorted fifth, by
    priority 3. Once it's running, no independent spec is left. Its review (~15 min of seats
    plus fixes) then sits on the critical path before 81 can start, and again before 84
    and 85. "Reviewing while the next runs" only works while an independent spec is left
    to run. Fix: within a priority tier, `snapshot` sorts by descendant count, so a parent
    with children goes before a leaf. Here that means 80 before 79. Or keep priority first
    and let `next` prefer a parent whose children are waiting over a leaf.
18. **A cell over its own budget looks like a bug, and the skill doesn't say it isn't.**
    SA-0080 finished `READY_FOR_REVIEW` at $7.55 against `budget_usd: 6`. That's within
    the ~1.7× overshoot `DESIGN.md` §3 documents (an attempt is the unit, item 44's
    closure). GOTCHAS says the loop's cost isn't bounded by the specs' budgets only in the
    rate-limit bullet. Fix: a Recording line, "a spec can finish up to ~1.7× its
    `budget_usd` (§3); over that, file it". And `record` could print spent/budget so the
    delegate sees it without reading the log.
19. **Nobody reviews the delegate's own review commits, and they carry the same defect
    classes.** On #247 I added a module-scope import of `read_log_since` to
    `tests/test_events.py`. Against base, the whole file then errors at collection instead
    of the witness failing. The cell agents avoid that on purpose, and both seats had
    praised it. I only caught it because I ran the witnesses against base's `saffron/`
    myself. Step 2c.6 says "fix, check, commit, push" and never says the fix gets the
    scrutiny the cell's diff got. Fix: 2c.6 requires each review-added witness to be run
    against the spec's base (or the declared mutant) before the push, the same bar as
    REVIEW-PROMPT's "each new witness failing at `{BASE}`". Better still, `driver.py
    base-run SA-NNNN <test ids>` builds the base tree and runs the given tests.
    The same goes for the delegate's own probes. On #250 my first P3 mutant crashed with
    `TypeError`: it took `base[0]`, and the baseline's first gate enumerates nothing. On
    #249 three probes silently failed to apply, because of shell quoting. Each time,
    "1 failed" or empty output would have read as "killed". What caught them was a probe
    script that asserts the edit applied and prints the `E` line. Fix: a probe runner in
    the driver (`driver.py probe <file> <find> <replace> <test>`) that refuses an edit
    that didn't apply, and reports "killed (AssertionError)" apart from "broke (TypeError)".
23. **`stack` warns that a sibling child "will show its parent's changes", and it
    won't.** With 81 and 84 both children of 80, the dry run printed `warning: SA-0084
    sits above SA-0081, not its parent SA-0080: #249 will show SA-0080's changes`.
    Measured: with base `saffron/SA-0081`, the merge base is SA-0080's head (`9e6a4cfcc`),
    and `git diff SA-0081...SA-0084` is exactly SA-0084's own range (2 files, +140/−7).
    A PR shows its parent's changes only when the parent is absent from the stack (the
    GOTCHAS case). A parent two layers down is fine. Fix: warn only when the parent
    isn't an ancestor of the layer below. Otherwise say "SA-0084 sits above its
    sibling SA-0081; its diff is unaffected, and `rebase` would chain it if asked".
    A linear stack over a fan-out parent always produces this, so a false alarm here
    trains the delegate to ignore the warning.
22. **`pattern`'s unanchored state names match the agent's own tool calls.** During
    SA-0084's REBUT/REVIEW, the Monitor fired on
    `agent: Grep {"pattern": "SCOPE_REVIEW|PhaseStart|…"`. A spec about events or states
    greps for those names, and the notification reads as a terminal state. The skill
    leaves the states unanchored because the CLI prints them after a padded spec id.
    Fix: anchor that alternation to the CLI's own shape, `^SA-[0-9]+ +(STATE…)` plus
    `^(STATE…):` for the phase-summary lines. Or exclude `^agent:` lines, which never
    carry a real state.
21. **Worked: `stack` as a mid-loop dry run.** Run after 5 of 8 PRs, it printed the order,
    with SA-0083 kept directly above SA-0082, and a clean `merge-tree` for every pair. So
    conflicts can be caught hours before step 3. Step 2 could say "run `stack` (dry) after
    each review push", so a conflict between neighbours is found while its branch is
    still fresh. `stack --execute` also worked first time: 4 bases retargeted,
    stack #251 created, all 8 bases read back correct, drafts left as drafts. It prints
    the whole dry-run block again before the read-back, false-alarm warning included,
    so the one line that matters ("bases, read back") is at the bottom of 30.
20. **Review commits can push a diff past `size` with no gate noticing.** #247 was 294
    changed lines against the `bug` ceiling of 300. The review added a witness and a
    shared helper, which puts it over. That's item 40's known hole (`size` runs only in the
    cell), but the skill never tells the delegate to check. Fix: 2c.6 prints the branch's
    changed-line count against its type's ceiling after the review commit. Anything over
    goes to the operator as a gate-policy call, which the skill already routes that way.

