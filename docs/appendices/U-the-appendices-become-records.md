---
id: U
title: "rev 25: the appendices become records"
revisions: [25]
question: "Can the appendices leave `DESIGN.md`? Yes, because a refusal reaches only as far as its reason, and the reason against ADRs was a parallel tree"
---

Appendix P answered no to ADRs three times, and `CONTEXT.md` §11 gave the
reason. A `docs/adr/` tree beside the appendices would be a second address
space for what §-numbers and letters already address. The first two records
to disagree would do it undetectably. That reason is about a *parallel*
tree. It was read as a refusal of any record per file, which it never argued.

Two costs grew under that reading. The appendices record decisions as a
timeline, so where one decision stands today is spread across several: the
emitter across `ontology/RATIONALE.md` and Appendices O, P and T. And nothing
marks a decision replaced. Appendix P still says the emitter is deferred after
Appendix T reopened it.

**What changed.** The twenty appendices, A to T, moved verbatim into
`docs/appendices/`, one record each, as `records/`' second kind. Their letters
are permanent ids, so every citation still resolves. `DESIGN.md` keeps §0 to
§11, and both of its indexes render from the records. `docs/appendices/**` is
`protected`, as `DESIGN.md` is. `CONTEXT.md` §11's ADR entry and its naming
decision 4 narrow the same way, to a parallel tree. Design:
`docs/superpowers/specs/2026-09-18-appendices-as-records-design.md`.

**What did not change.** There is still no `docs/adr/`, and ADR still means
prior art's records. An appendix is still a permanent record of what one
revision found. It is never replaced and has no status.

**The intent.** Decisions are to be recorded one per file, as their own kind,
and migrated out of the appendices. That kind is not designed here. Its name,
its numbering, and how one decision replaces several are open in backlog item
`b-9ff0fd`, and the first record it holds is this reversal.

62. **A refusal reaches only as far as its reason.** "No ADRs" was argued
    against a parallel tree and enforced against every record per file. Read
    the reason before the verdict. Where the reason stops, the refusal stops,
    and a question outside it is still open.
