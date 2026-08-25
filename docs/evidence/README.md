# Evidence

Primary records from v0.5, salvaged out of `.superpowers/` before it was lost.

That directory is gitignored — it holds the per-task briefs and implementation
reports from the session that built v0.5, and none of it survives a merge. Most
of it is scaffolding worth losing. These three are not: they are the only
verbatim record of what happened when parts of the system first met a live model,
and `DESIGN.md`'s appendices summarise them rather than reproduce them.

| File | What it is |
|---|---|
| `2026-08-20-critic-first-run.md` | §5.5's critic, first live run, against `SA-0004`'s patch — a factory-written change that passed every gate and that adversarial review rejected. Verbatim findings, per-lens drop rates, and which of the known defects it caught and missed. Nothing was tuned after seeing output. |
| `2026-08-20-rebut-first-run.md` | §5.6's REBUT, first live run. A deliberately false blocker put to the implementer: its rebuttal verbatim, and the critic's verdict verbatim. The first datum for the withdraw rate. |
| `2026-08-20-v0.5-execution-ledger.md` | The controller's ledger for the eleven-task build: every task's outcome, every review finding, and fourteen numbered rulings made on the operator's behalf with what each costs if wrong. |

Read these when a claim in `DESIGN.md` Appendices I–L needs its source, or when
deciding whether a component that "works" has actually been run.

Records written since, by the same rule — a measured fact beats a reasoned one:

| File | What it is |
|---|---|
| `2026-08-21-subscription-turn-accounting.md` | What a turn costs on a subscription token, measured rather than inferred. |
| `2026-08-22-integrity-rejected-gate-measured.md` | `SA-0004`'s rejected gate, executed against real `git diff` output rather than read. Three corrections to Appendix K, including one defect nothing recorded: the gate fails this repository's own merge commits. Scripts in `scripts/`. |
| `2026-08-25-mutation-testing-vs-a-lens.md` | Issue #33: whether "would the tests catch this code being wrong" needs a mutation-testing tool. `SA-0002`'s untested header reset run against diff-scoped coverage, `cosmic-ray`, `mutmut` and a prompted lens. Coverage reports nothing and `cosmic-ray` misses it; `mutmut` finds it and will not run here; the lens named it 3/3. |
