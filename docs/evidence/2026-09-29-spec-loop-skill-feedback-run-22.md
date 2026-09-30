# Feedback on run-saffron-spec-loop (run 22, 2026-09-29)

Run 22 queued fifteen specs: `SA-0193` to `SA-0196`, and the eleven of the
`SA-0161` chain. Three ran as attended cells, and all three reached
`READY_FOR_REVIEW`. The operator stopped the loop before the chain, at 47%
of the delegate's context. Run 21's feedback is checked below.

**Outcome:** a stack of three pull requests, #596 ← #598 ← #600, with step 5
as #602. The operator merged all four on 2026-09-30. The cells cost **$29.34** against $64 of budget. Four failed
cell starts cost nothing.

| Spec | PR | Spent | Starts | In-cell blockers | Seat blockers the critic passed | Size after review |
|---|---|---|---|---|---|---|
| `SA-0193` | #596 | $10.44 of $26 | 3, two infrastructure | 0 | 1 surviving probe | 1266 of 3000 |
| `SA-0194` | #598 | $8.37 of $14 | 1 | 1 host probe, withdrawn in REBUT | 1, the withdrawn one | 584 of 1300 |
| `SA-0195` | #600 | $10.53 of $24 | 2, one infrastructure | 0 | 1 concern | 1344 of 3000 |

## What happened, in order

1. **The operator chose the order.** The four new specs ran first, then the
   chain. `snapshot` sorts by priority, so it put nine chain specs first. The
   delegate held `SA-0161` to go first on the others (b-c07b92).
2. **Step 1b reviewed all fifteen specs in parallel.** It found one blocker,
   in `SA-0167`, and about fifty concerns. `SA-0194` was clean. `SA-0196`
   needed a witness edit, three rounds, and spec PR #595.
3. **Eleven spec writers revised the chain in parallel.** They worked in one
   shared worktree, each editing one file and committing nothing. The
   operator decided four scope questions, and `SA-0177` now files the finish
   as a fact. Spec PR #597 carried all of it, and `SA-0161` took four review
   rounds.
4. **Two of five agent starts got `Connection refused` on every API retry.**
   Preflight's egress check had passed five minutes earlier each time. The
   first time, Colima held `*:53` and stopping it helped. The second time
   nothing held port 53. Both were recorded `NOT_IMPLEMENTED` at $0.
5. **Main's `tests` baseline was red in every cell.** Four setup-saffron
   template tests from #552 fail in a cell and pass on the host (b-7a70fd).
6. **The seats found one real defect the critic passed, on each PR.**
   - `SA-0193`: a guard matching the host's text anywhere survived both
     witnesses. Step 1b had named it as a note.
   - `SA-0194`: the host's probe blocker on a `preserves` criterion was real,
     and the lens withdrew it after REBUT. It is b-cd5fd2's case exactly, one
     run after it was filed. `SA-0193`'s fix is not on main, and REVIEW runs
     main's code.
   - `SA-0195`: a new test helper restated the parser beside it. The
     conventions lens ran main's prompt, so it had not yet gained `SA-0195`'s
     reach.
7. **ADR 8's measured pass ran for `SA-0195`.** It used the five-fixture set
   this run built, one run per fixture and arm, with the frozen `CLAUDE.md`.
   The rule, written before any run, asked the new prompt to see at least
   two more of the five defects and lose none. Both arms saw two. The new
   prompt gained `SA-0186` and lost `SA-0160`, so the effect is unmeasured
   at one run per arm, and `SA-0160` is a regression to watch.

## ADR 8's pass for `SA-0195`

Arm A ran main's prompts. Arm B ran `SA-0195`'s. Both passed the frozen
`CLAUDE.md`, one run per fixture. The rule is in the run's scratch notes
and was fixed before the first run.

| Fixture | A seen | A graded | B seen | B graded |
|---|---|---|---|---|
| `SA-0182` | 0 | 0 | 0 | 0 |
| `SA-0184` | 0 | 0 | 0 | 0 |
| `SA-0186` | 0 | 0 | 1 | 1 |
| `SA-0160` | 1 | 1 | 0 | 0 |
| `SA-0164` | 1 | 0 | 1 | 0 |

- The pass cost about $48 across thirteen runs, against the operator's $35.
  Each run took 13 to 15 minutes, not five.
- Arm B's first `SA-0182` run hit the lens's 30-turn ceiling. It is no
  sample, and a second run replaced it.
- `SA-0184`'s and `SA-0186`'s first arm-A runs failed. Their heads were
  reachable only from `refs/fixtures/*`, and the scoring cell fetches
  `refs/heads/*`. Local branches fixed it.
- Ten runs outlasted the 2-hour background limit. The kill left the scoring
  cell and the proxy running, and the delegate removed both by hand.
- One run per arm cannot tell a two-defect effect from noise. Three runs
  per arm would, at about $140 for the pass.

## Run 21's items, checked

1. **`revert` judges each new witness on its own** (b-cf832a): closed by
   hand in #586 before this run. No run-22 cell hit it.
2. **A host-filed probe blocker on a `preserves` criterion cannot be argued
   away** (b-cd5fd2): landed as `SA-0193` (#596), not merged. `SA-0194` hit
   the same case meanwhile.
3. **Anchoring needs an identifier, not a stopword** (b-38d45f): landed as
   `SA-0194` (#598).
4. **A stack exercises its own new lens or phase** (b-66d1c3): `SA-0196`
   queued and reviewed but not run. `SA-0194` and `SA-0195` each paid for its
   absence.
5. **The conventions lens reads beyond the hunk** (b-78ccc7): landed as
   `SA-0195` (#600). The verdict prompt's part stays open.
6. **A witness whose expected value is the code under test is refused**
   (b-5b1f8a): the adequacy prompt names it (#600). No gate refuses it yet.
7. Run 21's loop gaps are unchanged. `bookkeeping` still drafts an appended
   smoke-test paragraph, and step 5 rewrote it in place by hand. `labels`
   still reads no cell round, and `jev --kind cell` still writes outside
   `spec-loop/`.

## Summary: what Saffron should absorb next

Each item moves a step the delegate did by hand into a gate, a lens or a
phase. The rejection lines in `.saffron/rejections.md` are the evidence.

1. **An agent that never reached the API is infrastructure** (b-8170eb). It
   hit two of five starts, and each became a decided `NOT_IMPLEMENTED`. The
   delegate re-ran each by path. `error` is not `fail`.
2. **Report why the agent's API calls were refused** (b-a6bfb0). The proxy's
   state and the cell's resolver belong in the record before teardown. No
   cause could be found this run.
3. **Merge REVIEW changes before the stack that needs them** (b-66d1c3,
   b-cd5fd2). Two of three seat findings were defects a queued lens change
   would have caught.
4. **A spec's wrong builds in prose reach no REVIEW** (b-ef8543). About 35
   per spec sat outside `wrong_versions:` on three chain specs.
5. **Fix main's in-cell red** (b-7a70fd). Subtraction hides it from every
   cell.
6. **`snapshot` takes the operator's order** (b-c07b92). One `hold` did the
   job this run, and the next loop's chain needs the same.
7. **The skill ends every loop with a handoff** (operator, 2026-09-29).
   Step 6 of `SKILL.md` now says so. It is a skill-text change, the cheapest
   and weakest bucket.
8. **A step 1b note that names a surviving wrong build is fixed like a
   concern.** `SA-0193`'s only seat finding was its step 1b note. This is a
   skill-text change too.

## Filed from the reviews

- b-8170eb: the agent never reached the API.
- b-a6bfb0: a refused API call after preflight passed.
- b-7a70fd: the setup-saffron tests red in cells.
- b-695234: REBUT's guard restates the claim prefix.
- b-12e717: a wrong version left unexpressed.
- b-2dd65f: rename tokens.
- b-ef8543: wrong builds in prose.
- b-830dc7: prototype measurements left unrecorded.
- b-b1a7d4: `cite`.
- b-1f1188: cross-spec staleness.
- b-9529e9: the scoring driver's fixture heads, kills and resume.
- b-91ead2: `labels` reads no cell round.
- Dated lines went on b-c07b92, b-b0a187, b-cd5fd2 and b-abeb74.

## The loop's own gaps

- The scoring driver's cell sees only `refs/heads` (b-9529e9).
- Saving a subagent's report verbatim needs a transcript extractor. `jev`
  could read the agent's output file directly.
- `driver.py cite` takes a path, not an id.
