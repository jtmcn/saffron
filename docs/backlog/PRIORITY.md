# Priority — the order to work in

Settled 2026-09-04. The sort is toward **v1's success criterion**: *a full night
runs while you sleep, and you merge at least half of what it produces before the
coffee's cold* (§9). That target is what makes the tiers below mean anything,
and it is the one thing to re-argue if the order looks wrong — the disagreement
will be with the target, not with the sort.

**Re-sorted 2026-09-07, toward the criterion's second half.** Every spec pull
request of the preceding week needed a human review round after packaging, and
the two worst diffs (#154, #160) drew the cleanest critic verdicts. So within
tier 1 the items that decide whether a `READY_FOR_REVIEW` is *sound* now come
before the ones that make a night *honest* about itself, and most of the latter
are cheaper by hand than through a cell. The argument, the exit criterion, and
which items go through a cell are in
`docs/superpowers/plans/2026-09-07-trusting-the-queue.md`.

**Groomed 2026-11-07.** Each open item was checked against the tree, and 47
were closed as done, superseded or wontfix. 19 of those closed on the
operator's rulings. Each paragraph that named only
closed items was dropped. Its ids moved to the closed list at the end of their
tier, so every record's `tier` still resolves. Each item's own `## Record`
says what grooming found.

### Tier 0 — the milestone gate

**Met, as of 2026-11-07.** The gate was a night of more than one task. Batch
67 of the spec loop's run 54 started two cells, then stopped on `BUDGET`
before the third (`docs/evidence/2026-11-06-spec-loop-skill-feedback-run-54.md`).
So the between-task budget check acted on a second candidate. No record
shows the breaker firing in a live night, and that stays unmeasured. Tier 0
holds no open item.

**Closed since they were placed here.** Each id stays so its record's tier still resolves.
- ~~**16**~~, ~~**44**~~.

### Tier 1 — breaks at 03:00 with nobody watching

**Groomed 2026-11-07.** Every item the 2026-09-07 sort named here is closed but
these: **79**, **80**, **119**, **42** and **49**, in that order. Each
closed one is listed at the end of this tier. Each open one's `## Record` says
what is left.

**79 comes first.** It asks whether a `0 blockers` line means the diff is sound
or means nobody looked. The adequacy lens found its defect in two runs of
three. It waits on a corpus pass under the current lens prompts, measured first
for the metric's spread. The newest pass is from 2026-09-11. ~~**93**~~ folded
into it on 2026-11-07. **80** withholds the mutant a witness is judged by and leaves it in
the worktree. **119** leaves the plan turn's share of the budget undecided.
**42** still reads an errored rebuttal as a confirmed disagreement. Under
**49**, `revert` never checks a test whose body changed and whose name stayed.

**Placed 2026-09-20, from the 16 open items that carried no tier**: **170**.
Three records of a night disagree, and no rule says which wins. `CONTEXT.md` §8
calls the ledger authoritative for state, and the morning index renders from the
batch tree instead. A reconstruction of 68 stored rows on 2026-09-17 found
`risk` differing on one row and `attempts` on four. That is this tier's honesty
half. The page an operator reads at 06:30 and the ledger are two accounts, and
nothing says which one to believe.

**Placed 2026-09-28**, from the spec loop's run 20: ~~**b-7e69d0**~~,
~~**b-ab4b33**~~, then **b-abeb74**. They follow ~~**b-2750d5**~~ into the cell.
The PR seats found blockers the critic passed on six of eight pull requests.
Most were wrong versions the spec listed and nothing applied. REBUT argued a
real blocker away on #562, and no lens reads `CLAUDE.md`'s conventions.
Run 21 closed the first two. The third is partial until ADR 8's measured pass.

**Placed 2026-09-29**, from the spec loop's run 21: ~~**b-cf832a**~~, **b-5b1f8a**,
then ~~**b-cd5fd2**~~. The loop repairs each by hand every run. One uncollectable
id makes `revert` check no witness. A witness that reads the constant it tests
cannot fail. A lens withdrew a real `preserves` blocker because its line sat
outside the diff.

**Placed 2026-09-30**, from the spec loop's run 23: **b-f582ee**. A cell that
went green died seeding its gate cell on a transient `Permission denied`. It
was recorded `ORPHANED`, and nothing resumes its patch, so the re-run paid
again.

**Placed 2026-10-12**, from the spec loop's run 36: **b-1c59c3**. A spec
removed a name whose reader sat outside its `touches`, so its cell could not
pass both `scope` and `tests`. It ended `EXHAUSTED` at $41.03.

**Placed 2026-10-13**, from the spec loop's run 37: **b-703e64**. A stack
batch's spec writer revised a spec no `prose` gate read. The finish wrote it
back, and re-verification went red.

**Placed 2026-10-19**, from the spec loop's run 44: ~~**b-e40d09**~~, moved up
from tier 3, then **b-e7898b**. A host-run probe that survived was dropped
for want of an anchor, so `SA-0288` packaged past its own blocker. A spec
that added a refusal refused the specs queued below it, and its cell ended
`EXHAUSTED`.

**Placed 2026-11-04**, from the spec loop's run 53: **b-fa4a83**. A survived
mutant reaches REPAIR as its whole claim, so `SA-0330`'s repair turns never
found the two cases it lacked, and the cell ended `EXHAUSTED`.

**Placed 2026-11-06**, from the spec loop's run 54: **b-d39d9a**. `SA-0335`
spent $76.77 against its $69 budget during REVIEW and REBUT, and nothing
stopped it. The overrun stopped its batch after two of four specs.

**Closed since they were placed here.** Each id stays so its record's tier still resolves.
- ~~**7**~~, ~~**26**~~, ~~**40**~~, ~~**45**~~, ~~**46**~~, ~~**47**~~, ~~**50**~~, ~~**51**~~, ~~**57**~~, ~~**59**~~, ~~**61**~~, ~~**63**~~, ~~**69**~~, ~~**70**~~, ~~**71**~~, ~~**73**~~, ~~**74**~~, ~~**78**~~, ~~**81**~~, ~~**82**~~.
- ~~**83**~~, ~~**84**~~, ~~**85**~~, ~~**88**~~, ~~**89**~~, ~~**94**~~, ~~**95**~~, ~~**97**~~, ~~**102**~~, ~~**109**~~, ~~**112**~~, ~~**114**~~, ~~**115**~~, ~~**117**~~, ~~**118**~~, ~~**120**~~, ~~**136**~~, ~~**137**~~, ~~**140**~~, ~~**141**~~.
- ~~**143**~~, ~~**145**~~, ~~**154**~~, ~~**173**~~, ~~**b-36b551**~~, ~~**b-408cf5**~~, ~~**b-a8270f**~~, ~~**b-a4df62**~~, ~~**b-fd1468**~~, ~~**b-89ec93**~~, ~~**b-032c3e**~~, ~~**b-149df3**~~, ~~**b-4a63b7**~~, ~~**b-19b255**~~, ~~**b-792ab2**~~, ~~**b-8487de**~~, ~~**b-a7e5f3**~~, ~~**b-e471bd**~~, ~~**b-76f08d**~~, ~~**b-43a061**~~.
- ~~**b-877e93**~~, ~~**b-bf0c91**~~, ~~**b-efdf1f**~~, ~~**b-8170eb**~~, ~~**b-a6bfb0**~~, ~~**b-038aef**~~, ~~**b-4c5dc7**~~, ~~**b-d4e015**~~, ~~**b-031ac2**~~, ~~**b-7251b5**~~, ~~**b-34d743**~~, ~~**b-3c7ce9**~~, ~~**b-60a399**~~, ~~**b-032c61**~~, ~~**b-3bba0f**~~, ~~**b-6cd3c2**~~, ~~**b-883f74**~~, ~~**b-a04cc8**~~, ~~**b-f8fa24**~~, ~~**b-6b06e1**~~.
- ~~**b-af24d1**~~, ~~**b-02d328**~~, ~~**b-1c20da**~~, ~~**b-4eaaa4**~~, ~~**b-6677b6**~~, ~~**b-d4b847**~~, ~~**b-e773d9**~~, ~~**b-000d04**~~, ~~**b-4901d2**~~, ~~**b-b24cf7**~~, ~~**b-78a590**~~, ~~**b-9c7001**~~, ~~**b-8f6568**~~, ~~**b-cab612**~~.

### Tier 2 — the morning after

**Placed 2026-11-07**, in grooming, from three open items no tier named:
**b-a714d2**, **b-d9ed45**, then **b-2bc0d5**. A second batch stamps a live
task `ORPHANED`, because nothing holds one batch at a time. A second run of one
spec removes the first run's container. Cell images and the build cache are
never reclaimed, and one host's free disk fell to 16 GB. The first two stand
between ADR 10's sequence and two cells on one host.

**Raised 2026-11-07 from tier 3**, in grooming: ~~**b-719346**~~. `driver.py record`
refuses a finish's follow-up as not in the order. It took the rank of
~~**b-25f2b2**~~, the tier 2 item grooming folded into it.

**Placed 2026-11-07**, from reviewing `SA-0340`: **b-3cf039**. `migrate`
derives no `rebuttal` fact for a blocker that met REBUT's early exit, so it
refuses the ref.

**Placed 2026-11-07**, from reviewing `SA-0338`: **b-c5da95**. Four commands
load a spec without the ref's mutants, so a regate can judge a witness the cell
set aside.

**Placed 2026-11-06**, from the spec loop's run 54: **b-fe3488**, **b-ffb930**,
**b-0add4c**, then **b-71f95f**. A stack batch starts an order its budget
cannot run. The follow-up writer's first draft never parses. The record's
git calls can prompt and drop git's reason. A cell makes CONNECTs no git
call explains.

**Placed 2026-10-15**, from the spec loop's run 40: ~~**b-d31930**~~, then
**b-bba47a**. A queued spec's citations drift and nothing checks them before
its batch. The `tests` gate takes a printed warning for every failure.

**Placed 2026-10-16**, from the spec loop's run 42: ~~**b-2da959**~~, then
**b-f73cd0**. `cite` passes a drifted range and flags a correct one, and
`SA-0294` ports it. A batch stops at a candidate it cannot pay for, though a
later one fits.

**Placed 2026-10-17**, from the spec loop's run 43: **b-3a79a0**. The loop's
driver orders a stack by `depends_on`, not by the stack base a batch built.

**Placed 2026-10-19**, from the spec loop's run 44: ~~**b-619b7d**~~, **b-71e2df**,
**b-32b3db**, **b-3a3081**, then ~~**b-80cc6e**~~. An adopted task keeps its
failed state, so its children stay refused. A spec named a module its own
`forbidden` list made impossible. A multi-line constant derives no mutant.
Redaction misses the files beside `events.jsonl`. The driver and two ADRs
name the old halts.

**Placed 2026-10-12**, from writing `SA-0290`: **b-f5ceaf**, by hand now that
`SA-0290` merged (#919). `CONTEXT.md` has no entry for a removed name.

**Placed 2026-11-07**, from writing `SA-0350`: ~~**b-7c118b**~~, done by hand in
the spec's own pull request.

**Placed 2026-10-13**, from writing `SA-0291`: **b-cd1566**, by hand now that
`SA-0291` merged (#920). `CONTEXT.md` has no entry for a criterion's subject.

**Placed 2026-10-06**, from ADR 10, in this order toward a night on GCP. The
sequence crosses tiers, and each item keeps its own.
First **170**, then **b-2e0b97**, then **108** and ~~**b-ca3bc6**~~. Then
~~**b-0569f7**~~, **b-da550a** and last **b-a9ec4b**.

**Placed 2026-10-11**, from reviewing `SA-0282`: **b-e9153f**, after b-0569f7.
A task a `--stack` batch mints never records whether its thread pool was uncapped.

**Placed 2026-10-10**, from writing `SA-0245` and `SA-0258`: **b-52e670**. A
SIGTERM during a silent agent turn waits for the turn to end, because the
unwind closes a pipe a reader thread holds.

**From the operator visibility plan and the spec loop's runs 5 to 10**, in
this order: **43**, **66**, ~~**67**~~, **98**, ~~**157**~~, ~~**172**~~, **b-eac388**,
**b-bc54d1**, **b-63ac52**, **b-952c34**, **b-60d804**,
**b-281f0a** and **b-7d3810**. Then **160**, which is what
item 141's close left. The Gate-only cell's suite is in a file because the
ledger has no owner column that fits it.

**Placed 2026-09-22**: **b-cafacd**, filed revising `SA-0126`. It is 170's
neighbour. A run's status reaches no fact, so a folded ledger loses the cap
on a cut spec's retries.

**From the spec chain of 2026-09-20** (`SA-0113`): **b-7d3810**. One spec
measured the chain at 35.7 minutes to draft and 6.2 to review. So a revision
costs about six reviews. ~~**b-b69bb6**~~, ~~**b-929465**~~ and ~~**b-ea1d13**~~
are done.

**From the spec loop's run 11** (2026-09-21): ~~**b-440f17**~~ first. The `prose`
gate let three pull requests in a row ship what `CLAUDE.md` forbids, and each
review spent a pass on it. Then **b-490c9c**, ~~**b-61993a**~~, **b-f45f73**
and **b-0de0b3**. The last is the operator's decision to generate
the loop's report in core, and it needs design before a spec.

**From the spec loop's run 13** (2026-09-22): ~~**b-66e82d**~~, **b-055fa3** and
~~**b-a9ee32**~~. The first is why finding the gate behind #433's `EXHAUSTED` took
reproducing every gate by hand. The second is a witness that fails once three
local branches are pruned. The third opens when item b-b5f379 bumps the cell's
git.

**Placed 2026-09-23**, from writing `SA-0142`: **b-466005**. It is the
glossary entry for a stack batch, its order and a predecessor, which a cell
cannot write.

**Placed 2026-09-23**, from asking whether to adopt Pydantic AI: **b-4e0868**.
The pinned SDK can constrain the extraction turn to a schema. Items 42 and 60
lost $6.20 to the shapes it rules out. A spike on the host settled the SDK's
behaviour, and `SA-0141` is its first slice. Then ~~**b-e51967**~~, filed
writing `SA-0141`. It is the by-hand edit to §5.3 and the glossary, done in
that spec's pull request.

**Placed 2026-09-25**, from the spec loop's run 16: ~~**b-04a5d9**~~, ~~**b-e0cd57**~~,
~~**b-bff670**~~, then **b-c375d6**. The first is a PR body that calls a new
advisory failure present at base. The second is a refusal that names ports
and not processes. The last two are the loop's tools reading stale state.

**Placed 2026-09-26**, from the spec loop's run 18: ~~**b-43061c**~~, then
**b-fab381**. The first is text in a string literal that no `prose` rule reads.
The second is `snapshot` stranding a chain behind a merged parent.

**Placed 2026-09-27**, from the spec loop's run 19: **b-20043f**,
~~**b-468378**~~, **b-4acb0e**, then **b-e202e6**. The first is work a spec's
notes asked for that no check reads. The second is a local hook that fails
on a stack branch. The last two are seams in the spec session's cell and
its budget.

**Placed 2026-09-28**, from the spec loop's run 20: **b-ad1285**,
~~**b-b0a187**~~, then **b-c07b92**. The first is a repair turn that passed
`prose` with a false sentence. The last two are the loop's tools. One blocked a
measured estimate, and the other takes a `drop` per spec to scope a loop.

**Placed 2026-09-28**, after run 20: ~~**b-2e7c4d**~~. The loop's `stack` check
merges adjacent pairs, and a sibling cut from `main` hid a conflict below it.

**Placed 2026-09-28**, by hand: **b-12ffc3**. `cell_down` deletes the cell's
session transcript, so a strange PR shows what the agent did but not what it read.

**Placed 2026-09-29**, from the spec loop's run 22: ~~**b-7a70fd**~~, then
**b-ef8543**. Four tests fail in every cell, and subtraction hides them. A
spec's wrong builds listed in prose reach no host run.

**Placed 2026-10-01**, from the spec loop's run 24: **b-426db4**,
~~**b-8d654b**~~, then ~~**b-3d2aa1**~~. A Problem-item obligation no
criterion drove was dropped. The
finishing commit writes through a symlink, unverified, and drops parse
failures.

**Placed 2026-10-03**, from the spec loop's run 27: **b-970f53**, then
~~**b-c94a2f**~~. The `tests` gate reads an interrupted pytest session as
`error`. A second `depends_on` entry carries no code into the cell.

**Placed 2026-10-05**, from the spec loop's run 28: ~~**b-8e30bd**~~,
~~**b-2247dd**~~, then ~~**b-708c8a**~~. A merged draft leaves its task `EXHAUSTED`
and its dependents refused. The loop driver refuses an `EXHAUSTED` layer.
REVIEW's re-prompt is written twice.

**Placed 2026-10-06**, at the operator's request: **b-e880ac**. Saffron takes
the cell token from whoever starts it, so a delegate must hold the credential.

**Placed 2026-10-07**, from the spec loop's run 30: ~~**b-1e106d**~~, then
**b-fbd181**. Nothing runs `terms` over `main`, so it went red unseen. A
measured estimate priced two specs at half what landed, and `size` only advised.

**Placed 2026-10-08**, from the spec loop's run 31: **b-8acb05**, **b-fe82d9**,
then **b-d28fd8**. A rename re-keys `prose`'s docstring hit, and joining lines
slips it back under. An escalated stack finish names none of its failures.
`migrate` drops `spec_findings`. b-d28fd8 took ~~**b-aee31f**~~'s place in
grooming, since both named that gap.

**Placed 2026-10-08**, from diagnosing b-fe82d9: ~~**b-a63235**~~, then **b-fdbedc**. The finish no
longer retires a spec, so the delegate retires each one and closes its item
by hand. A step the repo declares would let the finish do both.

**Placed 2026-10-09**, from the spec loop's run 32: **b-910cef**,
~~**b-a33889**~~, **b-180f9f**, ~~**b-8a0c9a**~~, ~~**b-5abe53**~~, **b-f10412**, then
~~**b-25f2b2**~~. The queue refuses every child of an open stack. A mint or a
revision that meets a cell runtime failure still misses its layer. A
resumed row keeps a stale merged head. The end review grades heads from
before the review commits. A `run` route prints nothing. The driver's
`stack` misreads a stack batch's chain, and its `record` refuses a follow-up.

**Placed 2026-10-10**, from the spec loop's run 33: ~~**b-c9a913**~~, then
**b-27bacc**. A criterion probe is judged against its declared witness
alone, so a blocker another test kills stands after REBUT. A stack batch's
follow-ups are pooled for their own `depends_on`.

**Placed 2026-10-11**, from the spec loop's run 34: **b-f7a591**,
**b-d0fed8**, **b-2f4746**, then **b-e7b6a2**. A lens that errors drops the
host's own probe blockers filed under it. A batch stopped before its row
exists leaves no row. A stack batch at a threshold spends into its shares.
`watch` cannot follow the follow-up writer or the end review.

**Placed 2026-10-12**, from the spec loop's run 35: **b-714ccd**,
**b-aff9ea**, **b-54ad4f**, **b-7ee599**, then **b-82cf2e**. A witness on a
default value passes REBUT. A spec can prescribe a false line. No gate
resolves a citation. A stack batch's follow-up guard has no witness. `migrate`
writes a false package fact for an adopted row.

**Placed 2026-10-12**, from the spec loop's run 36: **b-9efbe2**. A child's
cell deleted its parent's witness setup, and the parent's own wrong version
then passed it. No gate re-runs a parent's wrong versions.

**Placed 2026-10-13**, from the spec loop's run 37: **b-7c8bc4**, then
**b-a12047**. Fakes kept a reordered function's old signature, so a revert
passed. PACKAGE leaves a spec's deferred check out of `## Not covered`.

**Placed 2026-10-23**, from the spec loop's run 46: ~~**b-0bd346**~~, then
~~**b-066901**~~, ~~**b-1572e7**~~, **b-cc87b1** and ~~**b-7c1c99**~~. REBUT ends a task
`EXHAUSTED` on a gate failure its own fix made. A layer cut from a review
commit cannot be packaged again. A child stacks on its lowest open parent.
The writer drafts a follow-up a queued spec owns. One refused /24 stops
every cell.

**Placed 2026-10-23**, from `SA-0312`'s spec review: **b-e39286**. A
deferred finish exempts the stack base's branch but none on its chain.

**Placed 2026-10-24**, from the spec loop's run 47: **b-a68b24**, then
~~**b-781ea4**~~. The witness gate passes a mutant whose find matches twice. The
finish's follow-up drafts fail to parse, so it files nothing.

**Placed 2026-10-27**, from writing `SA-0326`: **b-bc8343**, by hand after
`SA-0326` merges. `CONTEXT.md` names no review commit and no commit review.

**Placed 2026-10-29**, from the spec loop's run 50: **b-298b1c**,
**b-8826cf**, **b-323c97** and ~~**b-0bd8c9**~~. A spec review's lost findings
skip a layer. A rebuttal's suppression ends a green task. An adopted task
gets no end review. A stack batch refuses a spec that meets an earlier
batch's open layer.

**Placed 2026-10-30**, from `SA-0330`'s first review: **b-e9dd4c**. A
`REVIEW_INCOMPLETE` parent whose push was refused still admits its child.

**Placed 2026-11-02**, from the spec loop's run 52: **b-b664d1**, then
**b-4a9207**. A citation that names one construct beside another's lines
passes until a parent moves them, then stops the batch. A finish drafts a
follow-up its own batch refuses, so nothing pushes.

**Placed 2026-11-04**, from the spec loop's run 53: **b-bece8b**, **b-0ac661**,
**b-f011f3** and **b-249808**. A by-hand merge of a `PLAN_REJECTED` parent left
its child refused. A fix to the plan checkpoint could not pass it. A lost
connection after a completed turn ended `NOT_IMPLEMENTED`. A cell cited the
wrong spec at 20 sites.

**Closed since they were placed here.** Each id stays so its record's tier still resolves.
- ~~**36**~~, ~~**37**~~, ~~**38**~~, ~~**48**~~, ~~**52**~~, ~~**60**~~, ~~**72**~~, ~~**103**~~, ~~**104**~~, ~~**113**~~, ~~**135**~~, ~~**138**~~, ~~**142**~~, ~~**144**~~, ~~**146**~~, ~~**147**~~, ~~**148**~~, ~~**149**~~, ~~**152**~~, ~~**153**~~.
- ~~**158**~~, ~~**159**~~, ~~**168**~~, ~~**169**~~, ~~**171**~~, ~~**177**~~, ~~**b-122686**~~, ~~**b-606ea3**~~, ~~**b-60732c**~~, ~~**b-7c41e0**~~, ~~**b-afec7c**~~, ~~**b-b5f379**~~, ~~**b-f2a9d1**~~, ~~**b-044ae7**~~, ~~**b-08a36a**~~, ~~**b-17fb8b**~~, ~~**b-1c7019**~~, ~~**b-3e0dbe**~~, ~~**b-461729**~~, ~~**b-5d5b56**~~.
- ~~**b-5e443c**~~, ~~**b-65e7e2**~~, ~~**b-6f7f8d**~~, ~~**b-865399**~~, ~~**b-a70ec1**~~, ~~**b-ce93aa**~~, ~~**b-0c1d69**~~, ~~**b-250dc7**~~, ~~**b-25766a**~~, ~~**b-602d00**~~, ~~**b-e8027b**~~, ~~**b-343c21**~~, ~~**b-db95e1**~~, ~~**b-1adb50**~~, ~~**b-6377cf**~~, ~~**b-cde96b**~~, ~~**b-dce9a4**~~, ~~**b-b0cd68**~~, ~~**b-38d45f**~~, ~~**b-47659f**~~.
- ~~**b-66d1c3**~~, ~~**b-78ccc7**~~, ~~**b-00534f**~~, ~~**b-209696**~~, ~~**b-23a149**~~, ~~**b-60ff2e**~~, ~~**b-0a08bf**~~, ~~**b-4e1b6d**~~, ~~**b-a1d649**~~, ~~**b-e0e1cf**~~, ~~**b-5df2a7**~~, ~~**b-cf50dc**~~, ~~**b-998bb7**~~, ~~**b-009d51**~~, ~~**b-1b05be**~~, ~~**b-b9365d**~~, ~~**b-8e12c1**~~, ~~**b-549012**~~, ~~**b-e0044f**~~.
- Closed as wontfix: **b-8d5e55**, **b-593d50**.

### Tier 3 — real, not urgent

**Placed 2026-11-07**, in grooming, from six open items no tier named:
**b-ba0cba**, **b-036cc5**, **b-262df1**, **b-4bd68a**, ~~**b-cd4de2**~~, then
**b-98a3be**. A follower of `events.jsonl` sees no typed spend from IMPLEMENT
to the outcome. `saffron watch` has no typed output for a follower outside
Python. Record helpers sit under `tests/`, and the loop's driver imports them.
A lens can search code only as text. The spec loop numbers its passes as runs,
which is a ledger term. The spec chain records no cost per escaped defect, so
no step can be cut on evidence.

**Moved 2026-11-07 from tier 2**, on the operator's ruling: **b-dc5212** and
**b-4589be**. Each bites only on the driver's attended path, which is now the
fallback.

**Placed 2026-11-06**, from the spec loop's run 54: **b-25c0f5**, then
**b-980fbd**. Test setup for the routed ledger is restated across a dozen
files. The record append event's sink skips redaction, and `watch` names the
wrong first line.

**Placed 2026-10-16**, from the spec loop's run 42: **b-60317d**.
`reconcile`'s `head_moved` comment says nothing judges a moved head.

**Placed 2026-10-17**, from the spec loop's run 43: ~~**b-74a122**~~.
`CONTEXT.md`'s Refusal entry lacks the citation cause.

**Placed 2026-11-02**, from the spec loop's run 52: **b-e4cb58**. `CONTEXT.md`
defines a Refusal as before any cell starts, and `ready_task` refuses after one.

**Placed 2026-10-19**, from the spec loop's run 44: **b-b8f0d9**, **b-e9cd43**,
**b-524b1a**, **b-62e00a**, **b-b33854**, **b-d149c6**, ~~**b-0094bd**~~, then
~~**b-8ef729**~~. Each is a gap a seat found and the stack left alone.

**Placed 2026-10-20**, from the spec loop's run 45: **b-5288d7**. Three
modules each split a `consumes` or `removes` entry at its colon.

**Placed 2026-10-20**, from the spec chain for `SA-0300` to `SA-0306`:
**b-a64578**, **b-206d2c**. The view's spend after a resume, and a runaway
row setting a budget floor.

**Placed 2026-10-23**, from the spec loop's run 46: **b-30cbb8**,
**b-d038df**, **b-25634b** and **b-19dbc9**. Each is a gap a
seat or the run found and the stack left alone.

**Placed 2026-10-24**, from the spec loop's run 47: **b-0c5afc**,
**b-fa014a**, **b-22ed54**, **b-c3688d**, **b-7fa522**, **b-54c8b4**,
**b-7655f9** and **b-2d2014**. Each is a gap a seat or the run found and the
stack left alone.

**Placed 2026-10-24**, from ADR 11 and the controlled vocabulary review:
**b-8220e6**, then **b-541e9a**, which apply ADR 11. Then ~~**b-c16c6c**~~ and
~~**b-545741**~~, which close gaps between `factory.ttl` and `CONTEXT.md`.
~~**b-7aefb8**~~ is a property inside `factory.ttl`, and ~~**b-8e14fb**~~ its place
in `policy.yaml`. **b-2227b0**, closed as parked, records a draft ADR.

**Placed 2026-10-25**, from the spec loop's run 48: ~~**b-9c5b11**~~,
~~**b-01c53d**~~, ~~**b-92fdbe**~~, **b-d3f977**, **b-f0e351** and **b-87001a**.
Each is a gap a seat, a finish or the run found and the stack left alone.

**Placed 2026-10-27**, from the spec loop's run 49:
**b-1b8b1e**, **b-92c92a**, **b-2a03c2**, **b-d2afe3**, ~~**b-1ff5a3**~~ and
**b-3a0789**. Each is a gap a seat, a finish or the run found and the stack
left alone.

**Placed 2026-10-30**, from #996's Standards seat and finish 61: **b-25b7ba**.
Two renderers spell a new failure, and they disagree on line 0.

**The 2026-09-04 sort's tier 3, plus what spec loop runs up to 32 added.**
Each line keeps the order it was filed in.

- From the first sort: **31**, **20**, **53**, ~~**54**~~, ~~**55**~~, **75**, **76**,
  **77**, **90**, **92**, **96**, **100**, **101** and **108**.
- Filed 2026-09-12 to 2026-09-19: **116**, **121**, **122**, **130**, **134**,
  ~~**150**~~, **151**, **155**, **156**, **174** and **b-d6bff7**.
- From spec loop runs 7 to 10: **b-990bd9**, **b-7431a2**, **b-9eceda**, **b-bc9951**,
  **b-0281e4**, **b-e9db0e**, **b-397edd**, **b-0e20e9**, **b-98dc4d**,
  **b-27b9db**, ~~**b-bbf663**~~ and **b-6a9707**.
- From the reviews of #393 and `SA-0120`, and spec loop runs 13 and 14: **b-d5d290**,
  **b-9ed36d**, **b-b431c1**, ~~**b-ac2f02**~~ and **b-49329e**.
- From ADR 4's review and the superpowers comparison: ~~**b-07f694**~~,
  **b-7c88f8**, **b-e1afbb** and **b-3732ef**.
- From spec loop runs 15 to 17 and `SA-0135`'s review: **b-f30189**, **b-a90136**,
  **b-e06dbc**, **b-32f492**, **b-8fb227**, **b-79d951**, **b-9ead75** and
  ~~**b-04d4c2**~~.
- From the stack batch's spec reviews: ~~**b-2d9ae9**~~, **b-223244**,
  **b-acee54**, **b-6518ba**, **b-6a101f**, **b-7eb5f5** and **b-22ff3f**.
- From the 2026-09-27 size pricing and spec loop run 32: **b-41664e**, **b-4b386f**,
  **b-d96f14**, **b-9b94c9**, **b-ff3141**, **b-a99c76**, **b-3a8504**,
  **b-7f105f** and **b-8c17dc**.
- From item 52's review: **b-cec9a7**.

**Placed 2026-09-20**: **161**, **162**, **163**, **126**, **128** and **129**,
then **b-7d2acf**. The first three are what PR #317 left on the `prose` gate. A
prompt written as a Python string is invisible to it. Its rules read register
and not instruction form, and its sentence limit fights §8's line budget. 126 is
a cache write the REVIEW lenses pay for three times, at the cost of plan
headroom rather than money. 128 and 129 are the record kind's own defects. One
field name misleads 28 records, and an empty `## Problem` section loads clean.
b-7d2acf, filed the same day, is the check that was missing. Nothing
compares the index to the records in that direction. It ranks here, beside
128 and 129. ~~**b-61127f**~~, the ADR layer, is done.

**Placed 2026-09-26**, from the spec loop's run 18: **b-615466**, **b-50a704**,
**b-17d0d5**, then ~~**b-830357**~~. Each is a stack batch seam that review kept
as written, or a witness too weak at one boundary.

**Placed 2026-09-27**, from the spec loop's run 19: **b-1e9a7a**,
**b-146869**, ~~**b-ec607a**~~, ~~**b-ea3bb5**~~, ~~**b-a5d4af**~~, **b-6d3bcf**,
**b-36d318**, then ~~**b-0e3528**~~. Each is a seam review kept as written, stale
text a split left, or a defect in the loop's own tools.

**Placed 2026-09-28**, from the spec loop's run 20:
**b-30bbd7**, **b-5ec5c5**, **b-64e40c**, **b-710086**, ~~**b-713e90**~~, then
**b-74e564**. Each is a seam review kept as written, text a spec could not
reach, or a gate hole the operator accepted once.

**Placed 2026-09-29**, from the spec loop's run 21: **b-84d4f8**, then
**b-6d43da**. One is vocabulary in summaries a cell wrote under `gates/**`. The
other is a fixture field under `docs/**` that no cell could add.

**Placed 2026-09-29**, from closing item 94: **b-bf970a**. Two tests skip on
uid 0 in every cell, and `--cap-drop ALL` makes the read they test fail.

**Placed 2026-09-29**, from the spec loop's run 22: **b-695234**,
**b-12e717**, **b-2dd65f**, **b-b1a7d4**, then **b-1f1188**.
The first three are defects in REVIEW and REBUT that the run's seats found.
The last two are gaps in the spec chain's own tools. **b-9529e9** and
**b-91ead2** came from closing the run. The scoring driver cannot reach a
fixture head or clean up after a kill, and `labels` reads no cell round.

**Placed 2026-09-30**, from the spec loop's run 23: **b-a09d30**,
**b-979dbe**, ~~**b-4ddb5b**~~, then ~~**b-2dc561**~~. The first two are gaps the
seats left in `SA-0196` and `SA-0161`. `terms` fails at base on a disavowal.
Preflight names a listener's address but not its process.

**Placed 2026-10-01**, from the spec loop's run 24: **b-115f9b**, then
**b-3590be**. The stack batch reads its batch id three ways, and a refused
revised spec gets no task state.

**Placed 2026-10-02**, from the spec loop's run 25: **b-006372**,
**b-7430c1**, **b-1068ea**, ~~**b-8a6f43**~~, then **b-a7e315**. The finish is
judged at the pinned base. One escalation hides a leftover worktree. A
child's tree carries an older spec than it runs. `snapshot --force` drops
holds, and `status` has no one-line form.

**Placed 2026-10-03**, from the spec loop's run 26: **b-cc8099**,
**b-81e109**, then **b-14ccc7**. A finish's narrow `except` has no witness.
`GhRunner` is defined three times. A live-cell test fails when two suites
run at once.

**Placed 2026-10-03**, from the spec loop's run 27: **b-3b8eb2**,
**b-3c17ab**, **b-835bfb**, **b-2944c9**, **b-b2fffe**, then ~~**b-348114**~~.
The host never sees which criterion failed. REVIEW counts a test-side wrong
version as unproven. A host listener that starts mid-loop is caught only at
preflight. The rate's header key is spelled at seven sites. `SETTLED_STATES`
has no vocabulary test. Four documentation lines lag the stack.

**Placed 2026-10-04**, from settling item 170's failures: **b-86fa07**. The
`prose` gate lists every hit in the repo, so the baseline cancels nearly all.

**Placed 2026-10-05**, from the spec loop's run 28: **b-444bed**, then
**b-edcab7**. A budget line says stop
before a REBUT that runs. Three sentences lag the stack.

**Placed 2026-10-08**, from the spec loop's run 31: **b-385eba**. The
regular-file git modes are spelled in three modules.

**Placed 2026-10-10**, from the spec loop's run 33: **b-97357c**,
**b-55186d**, **b-b94076**, then **b-dcf1ec**. Two of `SA-0243`'s witnesses
leave a side untested. The fold writes its spend rollup twice. A closed
`EXHAUSTED` draft reports `head_moved` on every scan. A preflight hit with
no socket list names no process.

**Placed 2026-10-12**, from the spec loop's run 35: ~~**b-bff156**~~,
**b-d3b755**, then ~~**b-d7959f**~~. `ready_task` returns a Refusal after a cell.
The host-probe line is built twice. The Mint entry says a re-offer waits.

**Placed 2026-10-14**, from the spec loop's run 38: **b-6d4704**, **b-65dbbd**,
then ~~**b-573746**~~. An attended cell never asks the image store. Preflight
spells the proxy's Dockerfile by hand. §5.1 calls `/gates` the one bind mount.

**Placed 2026-10-14**, from the spec loop's run 39: ~~**b-d5db52**~~, then
**b-dc41ef**. The loop's driver refuses an `EXHAUSTED` task with a PR. A
History run's snapshot ignores `--home`.

**Placed 2026-10-13**, from the spec loop's run 37: ~~**b-be3adc**~~, then
**b-e4ab6f**. §5.5 lists lens #1 without the failure path. The code calls the
subnet pool a bare pool.

**Placed 2026-10-11**, from the spec loop's run 34: **b-5a69db**,
**b-c86c4b**, then **b-54fee5**. A stopped night closes `INFRASTRUCTURE`,
which the glossary keeps for the breaker. A probe's reason is called a
refusal. The glob characters are spelled in two modules.

**Placed 2026-10-05**, from stage 2's stack batches: ~~**b-937778**~~,
**b-050733**, then **b-0efc31**. The loop driver's `history` counts every
phase's turns against `max_turns`. Specs use bare "run" for a turn. Nothing
compares the host's usage keys to the runner's.

**Placed 2026-10-05**, from ADR 9: **b-b51c9c**. The run record view shows a
night only once it ends.

**Placed 2026-10-06**, from the same review: **b-d269f4**. The view server
exits 1 on a startup failure and shows float noise.

**Placed 2026-10-07**, from the same reading: **b-f6ebc2**. No attempt records
the reasoning effort it ran at.

**Placed 2026-10-02**, from grading Jev's scores: **b-ef334d**. Its noise score
sorts a reviewer's notes, and its stop signal adds nothing over a blocker count.

**Placed 2026-10-07**, from counting the `prose` gate's hits: **b-2d668f**,
**b-817ef7**, **b-80cad7**, **b-37de22**, **b-c962c7**, **b-30fed0**, then
**b-e8f092**. Each clears one area's hits, and together they bring the gate to zero.

**Placed 2026-10-07**, from the spec loop's run 30: **b-cd41ac**, **b-7338e7**,
then ~~**b-d22c5a**~~. A spec named helpers absent at its base. Two repo rows on one
mirror prune each other. The docs name no `saffron migrate`.

**b-d5d290 is filed here and is the fourth instance of one shape.** Building
the record on git refs took four names the tree already held: "event",
`records/`, "index" and "projection". One was caught before code. The `terms`
gate's `AVOIDED` map reads the seven spellings it forbids. It never reads
`CONTEXT.md`'s 86 defined headwords. It cannot see any of the four. It ranks
here because a collision costs a reader rather than a night. It ranks above
nothing, which is where the pattern sat until now.

**76 sits here rather than in tier 1** because `structure`, where the hole was
found, is closed: it refuses every ignore source and states its own file set.
What is left is the same change for ruff, which is a measurement rather than a
risk — not, as an earlier draft of this note said, that `.gitignore` in
`integrity.gate_config` already routes the edit to a person. That is the
*tracked* half only: a `.gitignore` naming itself reaches no diff at all.

**What this ordering costs, recounted in grooming on 2026-11-07.** Tier 1
holds 15 open items, tier 2 holds 96 and tier 3 holds 197. So tier 3 is two
thirds of the backlog. That is the deliberate consequence of ranking by the
milestone rather than by what is nearest to hand. Of the 308 open items, 42
are by hand, since a cell cannot reach their files.

**Placed 2026-11-04**, from the spec loop's run 53: **b-8c6696**, ~~**b-a19ffd**~~
and **b-9bb8b7**. A spec missed the fixtures that pin the plan's sha. §5.3's
`plan.json` lacks the estimate fields. Two resolvers copy one landedness rule.

**Closed since they were placed here.** Each id stays so its record's tier still resolves.
- ~~**14**~~, ~~**19**~~, ~~**22**~~, ~~**23**~~, ~~**56**~~, ~~**62**~~, ~~**64**~~, ~~**65**~~, ~~**68**~~, ~~**86**~~, ~~**87**~~, ~~**91**~~, ~~**99**~~, ~~**105**~~, ~~**106**~~, ~~**107**~~, ~~**110**~~, ~~**111**~~, ~~**123**~~, ~~**124**~~.
- ~~**125**~~, ~~**127**~~, ~~**131**~~, ~~**132**~~, ~~**133**~~, ~~**139**~~, ~~**175**~~, ~~**176**~~, ~~**b-a1bdba**~~, ~~**b-e0bbbf**~~, ~~**b-e403c1**~~, ~~**b-d1d634**~~, ~~**b-ea1d13**~~, ~~**b-5fa523**~~, ~~**b-76953a**~~, ~~**b-0adc85**~~, ~~**b-111c56**~~, ~~**b-26315b**~~, ~~**b-2dea1c**~~, ~~**b-37924b**~~.
- ~~**b-542beb**~~, ~~**b-ac97c0**~~, ~~**b-50b566**~~, ~~**b-6a692d**~~, ~~**b-f4eb52**~~, ~~**b-589cf6**~~, ~~**b-df59f8**~~, ~~**b-e88930**~~, ~~**b-ca3bc6**~~, ~~**b-5aa016**~~, ~~**b-f71105**~~, ~~**b-1c4a14**~~, ~~**b-d0baf7**~~.
- Closed as wontfix: **9**, **10**, **b-1e5572**, **b-013138**, **b-830dc7**, **b-6ac0cd**, **b-7eb6d3**, **b-1fc93b**, **b-8971e6**, **b-8693ef**.

---

