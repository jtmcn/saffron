---
id: 114
title: A mutant that does not apply carries its `find` text into the critic's prompt
status: open
tier: 1
specs: [SA-0078]
prs: [243]
commits: []
cites: []
related: []
---

## Problem

**Tier 1.** Found reviewing `SA-0078` (PR #243), 2026-09-14. `SA-0078` took the
edit out of a surviving mutant's failure message, which `repair_prompt` hands the
implementer. The other path is untouched: `saffron/mutation.py:148,155` and
`saffron/cell/worktree.py:538,543` spell `{mutant.find!r}` into the reason a mutant
could not apply; `witness_gate`'s `unproven` note puts that reason in the result's
`summary`; `review.gate_summary` (`saffron/phases/review.py:139`) puts every summary
in the lens prompt (`saffron/cell/session.py:1693`), and a lens may quote it back in
REBUT. Reproduced against #243's head with two criteria, one surviving and one whose
`find` is absent:

```
- witness: fail (pytest 8.3.2) — 1 of 2 witness(es) survived their own mutant — 1 mutant(s) not proven: t.py::test_b (a.py: find text not found: 'min(d, CAP_SECRET)')
```

The mutant that does not apply is usually the code the implementer has yet to
write, which makes it the one most worth withholding. `SA-0078`'s spec also says
"No gate summary reaches any prompt"; that sentence is false.

**Done looks like** the mutators' reasons naming a category — not found, ambiguous,
unreadable — rather than the text, with the text kept where only the operator reads
it, and a witness that dumps the whole `witness` result and the lens prompt and
finds neither half of any mutant in either.
