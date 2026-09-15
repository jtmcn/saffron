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

Soundness first: **79**, **69**, **117** (69 answered by running the probe the lens
already names), **93**, **94**, ~~**109**~~ (filed 2026-09-12; it
leaks a mutant wherever 80 stores one), **114** (109's other path, to the critic),
**115** (a path hidden from `scope` by committed content), **80** (~~**83**~~, ~~**85**~~, ~~**84**~~,
~~**82**~~ and ~~**81**~~, pulled up from tier 3 as why 69's gate could not be
declared against safely, are done — 2026-09-08), then **97**, ~~**102**~~, ~~**112**~~, **119**, **120** and **118**. Honesty second:
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

### Tier 2 — the morning after

Operator visibility parts 2 and 3 — `SA-0032`–`SA-0039`, with the plan's Task 6
rewritten onto **42** — then Task 11's by-hand documents (**36**, **37**,
**38**), plus **43**, **48**, **52**, **60**, **66**, **67**, ~~**72**~~, **98**, **103**,
~~**104**~~, **113**.

**72 is done** (2026-09-07, by hand), taken ahead of Track A by operator
decision because it was the one item whose defect was a guard that could not
fire. Its number stays listed because item numbers are cited from `saffron/`.

### Tier 3 — real, not urgent

~~**22**~~, ~~**23**~~, **31**, **19**, **20**, **53**, **54**, **14** + **55**,
**56**, ~~**57**~~, ~~**61**~~, ~~**62**~~, **63**, ~~**64**~~, **75**, **76**, **77**,
~~**81**~~, ~~**82**~~, ~~**83**~~, ~~**84**~~, ~~**85**~~, **86**, **87**, **89**, **90**, **92**, **96**, **99**, **100**, **101**, **105**, **106**, ~~**107**~~, **108**, ~~**110**~~, ~~**111**~~, **116**, **121**, **122**, **123**, **124**, **125**.
(**65** and **68** are done, and **81**–**85** on 2026-09-08; **80** moved to tier 1 when its evidence arrived, and **69** is ranked there too.
**91** is done — the spike record landed. **92** was appended un-indexed, which
is the same defect as filing one nowhere at all. **94** was filed here and moved
to tier 1 the same day, when a host run turned it into a correctness item.)

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
were filed open the same day from the spec reviewer's backtest, all to tier 3.)

---
