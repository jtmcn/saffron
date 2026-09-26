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

### Tier 0 — the milestone gate

**58 is done** (merge `57b676c`, 2026-09-05), and with it **16** and half of
**44**. `saffron batch` exists and the machine below can start.

What replaced it as the gate was not an item: **run a night.** One has now run
against an empty queue (`DRAINED`, 2026-09-05) — the plumbing works. ~~What is
still unmeasured is a night that *runs* something: no cell has started under a
batch.~~ Stale by the evening it was written: batches 3–12 (2026-09-05 to
2026-09-10) each started one cell, read off `runs.batch_id` on 2026-09-12, and
batch 8 is `SA-0059`'s night, where the budget gate got its first evidence (item
73). What none of them was is a night of more than one task, so the between-task
budget check and the breaker have still never had a second candidate to act on.
That is the gate now.

### Tier 1 — breaks at 03:00 with nobody watching

**b-792ab2** leads tier 1 from 2026-09-23. The operator asked for a loop that runs
every queued spec with little input, and ADR 7 decides how. Its build specs
come before the rest of this tier. **b-b0cd68** comes before the finish's
specs run: until it lands, every finish with a layer turns this repo's gate
suite red and pushes nothing.

Soundness first: **79**, ~~**69**~~, **117** (69 answered by running the probe the lens
already names), **93**, **94**, ~~**109**~~ (filed 2026-09-12; it
leaks a mutant wherever 80 stores one), ~~**114**~~ (109's other path, to the critic),
~~**115**~~ (a path hidden from `scope` by committed content), **80** (~~**83**~~, ~~**85**~~, ~~**84**~~,
~~**82**~~ and ~~**81**~~, pulled up from tier 3 as why 69's gate could not be
declared against safely, are done — 2026-09-08), then **97**, ~~**102**~~, ~~**112**~~, **119**, **120**, **118** and ~~**136**~~. Honesty second:
~~**73**~~, ~~**70**~~, ~~**45**~~, **51** (with **49**/**50**, which its fix closes),
~~**47**~~, **46** (with ~~**95**~~, which compounds it), **40**, ~~**26**~~,
~~**7**~~, and ~~**78**~~.

Closed since the 2026-09-04 sort, and left in place because their numbers are
cited: **74** is done (`SA-0063`, `SA-0064`); **88** is closed on a negative
result (2026-09-08 — the gate summary was not the confound); **71** is
done (2026-09-08), **78** is done (its `DESIGN.md` half 2026-09-12), and **94** has its recording half done
and its explanation half open — each item's own `Status` line says what is left.
(**59** is done — `SA-0052`, PR #118.) Stack #222, merged 2026-09-12, closed
**45**, **57**, **61**, **70** and **95**, and the spec'd half of **42**, **46**,
**63** and **89**; each of those four stays listed for the half its `Status`
line names.

**93 and 94 sit with them** because they decide whether their numbers can be
read at all: 93 is the metric's unknown resolution, and 94 is that 2 of the
baseline's 8 verified vacuities rest on a cell baseline nobody can inspect.
The corpus has a baseline (`3/12`, 2026-09-09), and the adequacy prompt changed
between the only two passes there have ever been — so nobody knows the metric's
resolution, and two passes disagree by 1 of 12. Until that is measured, a prompt
change read off a single pass is the mistake item 88 left on the harness this
corpus replaced.

**79 and 69 are first** because they are the only items here about the
factory's ability to tell whether its own work is sound. Nine tests shipped in
one session naming behaviour they did not guard, every one of them past the lens
built to catch exactly that; and REVIEW filed no blocker on the one diff that
destroyed a worktree.

**79 is 69's sibling and no longer the only one of its kind.** 69 is the lens
failing at a question only running can answer; 79 is the same lens answering it
in two runs of three and not the third — measured, so the item's own "a question
no lens owns" is retired in place. Both bear on the same thing: whether a
`0 blockers` line means the diff is sound or means nobody looked.

**88 was directly under 79** rather than filed behind it, and is answered
(2026-09-08) without moving the number. The harness still reads three times
harsher than production on the same diff and the leading suspect explains none
of it, so its absolute numbers steer nothing — and 79's exit criterion is
written against an absolute. Track C can start on the harness's *differences*
between two prompts; it cannot be declared met on them.

Each fails in the dark or destroys work no one is awake to rescue. **45** loses
a run's commits nightly; **51** switches the anti-theater gate off for one
printed line; **47** feeds part 3 a column of zeros; **46** is the only account
of a night nobody watched; **40** merges a diff over a ceiling it passed;
**26** is done (`SA-0065`, PR #185, 2026-09-10) and its number stays listed
because item numbers are cited; **95** is what that fix left open — the refusal
reaches a terminal and never the ledger; **7** is done (`fix(review): no lens
was shown the invariants it judged a diff against`, 2026-09-11,
`docs/evidence/2026-09-11-lens-corpus-spread.md`, beside
`docs/evidence/2026-09-11-lens-corpus-claude-md.md`) and its number stays
listed too.

**From the spec loop's run of 2026-09-16** (stack #285): ~~**145**~~, then ~~**141**~~,
~~**143**~~, ~~**140**~~, **137**. **145** first because `SA-0092` built the ceilings
comparison and the prompt that should read it does not know it exists, so the
whole item-123 fix is inert until it does. **141** and **143** are `SA-0089`'s
two open edges — a judged suite that lands in no record, and a subnet space
nothing enumerates whose collision surfaces at REVIEW after IMPLEMENT is paid.
**140** is item 134's duplication grown by a third copy, in the same file.
**137** is the loop refusing its own dependents when a spec is edited mid-flight.

**From the spec loop's run 5, 2026-09-16** (stack #308): ~~**154**~~. Every mutant
on `session.py` is now `error`, and the one that tried wedged its cell on this
host.

**From the spec loop's run 6, 2026-09-17** (stack #320 ← #321 ← #323): ~~**173**~~.
A test red only in the cell is subtracted from every cell's result.

**From the spec loop's run 8, 2026-09-19** (stack #351 ← #360 ← #355 ← #366 ←
#353): ~~**b-2750d5**~~, **b-a8270f**, then ~~**b-36b551**~~. The first two are checks
the loop's delegate ran by hand after every cell. Mutating the line behind
each criterion found a witness hole in all five pull requests. A run over a
real ledger found #355 leaving out 75 of 76 merged tasks. ~~**b-36b551**~~ is a
wall cut that lost a cell's work and still settled its spec.
**b-149df3** is its by-hand half: the glossary and §4.5 after `SA-0126`.

**From the spec loop's run 9, 2026-09-19** (#375, #377): ~~**b-408cf5**~~. A plan
was refused on a ceiling its own `size` gate does not enforce, at the cost of a
cell and then two acceptance criteria.

**Placed 2026-09-20, from the 16 open items that carried no tier**: **170**.
Three records of a night disagree, and no rule says which wins. `CONTEXT.md` §8
calls the ledger authoritative for state, and the morning index renders from the
batch tree instead. A reconstruction of 68 stored rows on 2026-09-17 found
`risk` differing on one row and `attempts` on four. That is this tier's honesty
half. The page an operator reads at 06:30 and the ledger are two accounts, and
nothing says which one to believe.

**Placed 2026-09-20, from an architecture review**: ~~**b-fd1468**~~. The ledger
writes each fact kind and the fold reads it back in a second module. It makes
170's rebuild test hold by construction rather than kind by kind.

**From the spec loop's runs 8 to 10, placed 2026-09-20**: **b-a4df62**.
Reviewing a spec before its cell is the delegate's largest manual step, and
Saffron does none of it. Run 8 reviewed five specs and re-reviewed at parent
branches. Run 10 took five rounds over two specs. No run reached a review with
no finding. It sits in this tier because the step is what keeps a cell from
being paid to satisfy a spec that cannot be satisfied.

**From the spec loop's run 12** (2026-09-21): ~~**b-89ec93**~~. A cell near a
blocking `size` ceiling packed its SQL onto long lines, and passed. The gate
rewards the reformat, and the operator asked for a fix soon.

**From the spec loop's run 13** (2026-09-22): **b-4a63b7**. `revert` failed a
witness REBUT added to kill a surviving probe, since the property it pins was
already true at base. A correct diff ended `EXHAUSTED`, and the operator
opened #433 by hand.

**Placed 2026-09-23**, from the spec loop's run 15: ~~**b-19b255**~~, then
**b-8487de**. Both are REVIEW telling the operator something false. A probe
that only broke the format test read as killed on `SA-0127`. A verdict
session too big for argv left `SA-0128` halted at `REBUTTING`.

**Placed 2026-09-25**, from the spec loop's run 16: **b-e471bd**, then
**b-a7e5f3**. The cell's agent refused every write under `.claude/`, and
`SA-0129` ended `NOT_IMPLEMENTED`. Its by-hand pull request then merged, and
the ledger still refused its child.

**Placed 2026-09-26**, from the spec loop's run 18: **b-76f08d**. The `tests`
gate reads a flag error in captured output as its own, so `revert` skips every
witness for a new CLI flag.

### Tier 2 — the morning after

**From the spec loop's run 14** (2026-09-22): **b-db95e1**. Two cells in a row
landed within 25 lines of the `refactor` ceiling, and the second crossed it.
`driver.py check` reads no size estimate, so nothing asks for the split.

Operator visibility parts 2 and 3 — `SA-0032`–`SA-0039`, with the plan's Task 6
rewritten onto **42** — then Task 11's by-hand documents (**36**, ~~**37**~~,
~~**38**~~), plus **43**, **48**, **52**, **60**, **66**, **67**, ~~**72**~~, **98**, ~~**103**~~,
~~**104**~~, ~~**113**~~, **135**, and from stack #285: **147**, **146**, ~~**144**~~,
**149**, **148**, ~~**142**~~, ~~**138**~~, then ~~**152**~~ and ~~**153**~~, and
from stack #308: ~~**159**~~, **157**, **158**, and from run 6: **172**, and from run 7: ~~**b-b5f379**~~, **b-60732c**, **b-eac388**, **b-bc54d1**, **b-63ac52**, ~~**b-122686**~~, ~~**b-afec7c**~~, and from `SA-0109`'s spec review: **b-7c41e0**, and from run 8: **b-044ae7**, **b-65e7e2**, **b-5e443c**, **b-5d5b56**, **b-952c34**, **b-60d804**, **b-4589be**, **b-6f7f8d**, and from the spec-writer
measurement: **b-281f0a** and **b-08a36a**, and from run 9: ~~**b-17fb8b**~~, ~~**b-a70ec1**~~, ~~**b-ce93aa**~~, ~~**b-461729**~~, and from run 10: ~~**b-865399**~~, **b-1c7019**, **b-3e0dbe**, and from the spec chain of 2026-09-20: **b-b69bb6**, **b-7d3810**, ~~**b-929465**~~, **b-250dc7**. Then **160**, which is what
item 141's close left. The Gate-only cell's suite is in a file because the
ledger has no owner column that fits it.

**Placed 2026-09-20**: ~~**171**~~, ~~**177**~~, **168**, **169**, ~~**b-606ea3**~~,
~~**b-f2a9d1**~~, ~~**b-0c1d69**~~ and **b-25766a**. 171 and 177 are 170's neighbours. One holds a
diff stat no authoritative record carries, and the other minted a run per task
where `CONTEXT.md` defined one per repo. #444 redefined **Run**. The last five are vocabulary a cell
cannot write, because `CONTEXT.md` is generated from `ontology/factory.ttl` and
is `protected`. They are items 65 and 72 again, with five more words.
`b-0c1d69` was filed writing `SA-0113`, and it carries a `DESIGN.md`
§5.4.1 paragraph beside its glossary entry. `b-25766a` is the newest, the
record's own fact kinds, and it is 168 and 169 a third time.

**Placed 2026-09-22**: **b-cafacd**, filed revising `SA-0126`. It is 170's
neighbour. A run's status reaches no fact, so a folded ledger loses the cap
on a cut spec's retries.

**Placed 2026-09-24**: **b-dce9a4**, filed checking item 29's closure against
the tree. Item 29 left one window open for `SA-0020` to close, and `SA-0020`
shipped without it. A reconcile that runs mid-PACKAGE can move a resumed
task's live row into `CHANGES_REQUESTED`, and the scan then offers the task as
resumable. It sits in tier 2 because `saffron queue` starts no cell, and the
second cell needs another command to consume the candidate.

**152 and 153 are the spec loop's authoring half**, filed 2026-09-16 from
writing #290's three specs and reading their reviews. 152 is the mechanical
part — nothing resolves a queued spec's `witness` node ids until a cell has been
paid for, though `tests/test_queued_specs.py` reads the whole live corpus on
every commit. 153 is the measurement behind it: the author's conventions cover
one of the spec review's six checks, and the largest defect class in those three
specs — five sentences about current code that were false — has no authoring
rule at all. They rank here rather than in tier 1 because the spec review
already catches both classes by hand, every spec, before any cell runs; what
these buy is that it stops having to. Both are done (2026-09-16, by hand).

**72 is done** (2026-09-07, by hand), taken ahead of Track A by operator
decision because it was the one item whose defect was a guard that could not
fire. Its number stays listed because item numbers are cited from `saffron/`.

**From the stack batch's last spec reviews** (2026-09-25): **b-b0cd68**.
Retiring a spec turns this repo's gate suite red, so a stack batch's finish
cannot push here until the two tests it names are reworked.

**From the spec chain of 2026-09-20** (`SA-0113`): **b-b69bb6**, then
**b-7d3810**. One spec measured the chain at 35.7 minutes to
draft and 6.2 to review, so a revision costs about six reviews. b-b69bb6 is
first because it removes the findings that need no judgement, which was three
of the first review's six. ~~**b-929465**~~ and ~~**b-ea1d13**~~ are done by
#392, which leaves the two above.

**From the spec loop's run 11** (2026-09-21): ~~**b-440f17**~~ first. The `prose`
gate let three pull requests in a row ship what `CLAUDE.md` forbids, and each
review spent a pass on it. Then **b-490c9c**, **b-61993a**, **b-f45f73**,
**b-8d5e55** and **b-0de0b3**. The last is the operator's decision to generate
the loop's report in core, and it needs design before a spec.

**From the spec loop's run 12** (2026-09-21): **b-e8027b**. A re-snapshot
released a hold whose spec edit was still open, and `next` named the old text.

**From the spec loop's run 13** (2026-09-22): **b-66e82d**, **b-055fa3** and
~~**b-a9ee32**~~. The first is why finding the gate behind #433's `EXHAUSTED` took
reproducing every gate by hand. The second is a witness that fails once three
local branches are pruned. The third opens when item b-b5f379 bumps the cell's
git.

**From comparing Saffron with the superpowers skills** (2026-09-21):
~~**b-602d00**~~. A stacked child whose parent built its names differently pays for
a cell overnight and packages nothing mergeable. A host check refuses it first.
Then **b-343c21**, filed writing `SA-0134`. It is the glossary entry for a
consumed name, which a cell cannot write.

**Placed 2026-09-23**, from writing `SA-0142`: **b-466005**. It is the
glossary entry for a stack batch, its order and a predecessor, which a cell
cannot write.

**Placed 2026-09-23**, from the stack batch's spec reviews: **b-1adb50**. Two
`DESIGN.md` sentences go false once `SA-0149` and `SA-0152` merge, and only a
person edits that file.


**Placed 2026-09-23**, from the spec loop's run 15: ~~**b-6377cf**~~, then
**b-cde96b**. Baseline subtraction hid a `preserves` mutant that survived at
base on `SA-0127`. The second is the by-hand half of run 15's merges.

**Placed 2026-09-23**, from asking whether to adopt Pydantic AI: **b-4e0868**.
The pinned SDK can constrain the extraction turn to a schema. Items 42 and 60
lost $6.20 to the shapes it rules out. A spike on the host settled the SDK's
behaviour, and `SA-0141` is its first slice. Then ~~**b-e51967**~~, filed
writing `SA-0141`. It is the by-hand edit to §5.3 and the glossary, done in
that spec's pull request.

**Placed 2026-09-25**, from the spec loop's run 16: **b-04a5d9**, **b-e0cd57**,
**b-bff670**, then **b-c375d6**. The first is a PR body that calls a new
advisory failure present at base. The second is a refusal that names ports
and not processes. The last two are the loop's tools reading stale state.

**Placed 2026-09-26**, from the spec loop's run 18: **b-43061c**, then
**b-fab381**. The first is text in a string literal that no `prose` rule reads.
The second is `snapshot` stranding a chain behind a merged parent.

### Tier 3 — real, not urgent

~~**22**~~, ~~**23**~~, **31**, **19**, **20**, **53**, **54**, **14** + **55**,
**56**, ~~**57**~~, ~~**61**~~, ~~**62**~~, **63**, ~~**64**~~, **75**, **76**, **77**,
~~**81**~~, ~~**82**~~, ~~**83**~~, ~~**84**~~, ~~**85**~~, **86**, ~~**87**~~, ~~**89**~~, **90**, **92**, **96**, **99**, **100**, **101**, **105**, **106**, ~~**107**~~, **108**, ~~**110**~~, ~~**111**~~, **116**, **121**, **122**, ~~**123**~~, **124**, **125**, **127**, **130**, **131**, **132**, **133**, **134**, ~~**139**~~, **150**, **151**, **155**, **156**, **174**, **175**, ~~**176**~~, **b-d6bff7**, and from run 7: **b-990bd9**, **b-7431a2**, **b-9eceda**, **b-bc9951**, and from run 8: **b-0281e4**, **b-e9db0e**, **b-397edd**, ~~**b-e0bbbf**~~, and from run 9: **b-0e20e9**, ~~**b-e403c1**~~, **b-98dc4d**, **b-27b9db**, and from the dead-code-gate plan's Task 6: ~~**b-a1bdba**~~, and from run 10: **b-bbf663**, **b-6a9707**, and from the spec chain of 2026-09-20: ~~**b-ea1d13**~~, and from the review of #392: **b-d1d634**, and from PR #393's review: **b-d5d290**, and from `SA-0119`'s review: **b-5fa523**, and from writing `SA-0120`: **b-76953a**, **b-9ed36d**, and from run 13: **b-542beb**, **b-37924b**,
**b-b431c1**, **b-ac2f02**, and from run 14: **b-49329e**, ~~**b-111c56**~~, ~~**b-2dea1c**~~, and from ADR 4's review: **b-26315b**, **b-e40d09**, **b-ac97c0**, **b-07f694**, **b-032c3e**, **b-7c88f8**, and from ADR 5: ~~**b-0adc85**~~, and from comparing Saffron with the superpowers skills: **b-e1afbb**, **b-3732ef**, and from run 15: **b-f4eb52**, **b-f30189**, **b-a90136**, **b-e06dbc**, and from `SA-0135`'s review: **b-32f492**, **b-50b566**, and from run 16: **b-8fb227**, **b-79d951**, **b-9ead75**, **b-e88930**, **b-1e5572**, and from run 17: **b-04d4c2**, and from the stack batch's spec reviews: **b-6a692d**, **b-2d9ae9**, **b-223244**, **b-df59f8**, **b-acee54**, **b-6518ba**, **b-6a101f**, **b-7eb5f5**, **b-22ff3f**, **b-589cf6**.
(**65** and **68** are done, and **81**–**85** on 2026-09-08; **80** moved to tier 1 when its evidence arrived, and **69** is ranked there too.
**91** is done — the spike record landed. **92** was appended un-indexed, which
is the same defect as filing one nowhere at all. **94** was filed here and moved
to tier 1 the same day, when a host run turned it into a correctness item.)

**Placed 2026-09-20**: **161**, **162**, **163**, **126**, **128**, **129** and
**b-61127f**. The first three are what PR #317 left on the `prose` gate. A
prompt written as a Python string is invisible to it. Its rules read register
and not instruction form, and its sentence limit fights §8's line budget. 126 is
a cache write the REVIEW lenses pay for three times, at the cost of plan
headroom rather than money. 128 and 129 are the record kind's own defects. One
field name misleads 28 records, and an empty `## Problem` section loads clean.
b-61127f is the ADR layer `SA-0110` stopped short of, which nothing loads or
indexes yet. **127** and **131** were listed above with no `tier` field, so the
index ranked neither. They now carry the 3 this list already gave them.
**b-7d2acf**, filed the same day, is the check that was missing. Nothing
compares the index to the records in that direction. It ranks here, beside
128 and 129.

**Placed 2026-09-26**, from the spec loop's run 18: **b-615466**, **b-50a704**,
**b-17d0d5**, then **b-830357**. Each is a stack batch seam that review kept
as written, or a witness too weak at one boundary.

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

**What this ordering costs, stated plainly:** tiers 2 and 3 hold 38 of the 56
open items the index ranks, including every ontology item and every
operator-visibility spec there is already a full plan for. That is the deliberate
consequence of ranking by the milestone rather than by what is nearest to hand.
(Recounted 2026-09-10 from each item's own `Status` line to 34 of 51, then items
**97**–**101**, filed open that day, added — **97** to tier 1, the rest to these
two. **9** and **10**, each done bar a remnant, sit outside the index. Items
**102**–**106** were filed open on 2026-09-12 from the reviews of stack #222 —
**102** to tier 1, **103** and **104** to tier 2, **105** and **106** to tier 3.
**107** and **108** were filed 2026-09-11 as 102 and 103, when running the suite
on Linux turned "the runtime is one file behind a seam" into a claim with a test
against it, and renumbered when #222's items landed first. **112** was filed
2026-09-13 as a second 109, and renumbered when #234's 109 was found to have
landed first. **113** was filed open on 2026-09-13, to tier 2 beside 37 and 38.
**114**–**117** were filed open on 2026-09-14 from the reviews of the spec loop's
stack — **114**, **115** and **117** to tier 1, **116** to tier 3.
**119**–**122** were filed open the same day from the loop's second run —
**119** and **120** to tier 1, **121** and **122** to tier 3. **123**–**125**
were filed open the same day from the spec review's backtest, all to tier 3.
**130**, how to measure it again, was filed open on 2026-09-15, to tier 3.
**132**–**136** were filed open on 2026-09-15 from the spec loop's review of
`SA-0087` (#274) — **136** to tier 1 beside 118, **135** to tier 2, and
**132**–**134** to tier 3. It was filed as a second **131** and renumbered
when the spec pass's own 131 was found to have landed first, the same way
**112** and **107**–**108** were. **131** itself is ranked here, beside the
**127** it is the sibling of. **152** and **153** were filed open on 2026-09-16
from writing #290's specs and reading their reviews, both to tier 2.
**154**–**159** were filed open on 2026-09-16 and 2026-09-17 from the spec
loop's run 5 (stack #308): **154** to tier 1, **157**–**159** to tier 2, and
**155** and **156** to tier 3. The 16 items with no `tier` field were
placed 2026-09-20: **170** to tier 1, six to tier 2, and nine to tier 3.)

---
