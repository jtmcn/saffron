# vulture's whitelist for the `dead` gate: one `_.name` per line, each with its reason.
# A person writes it: `integrity` fails a cell's change here unless its spec names the file.

# Called by a framework, not by a name vulture can see.
_.model_config  # pydantic reads it on every model class
_._commits_are_quoted  # pydantic field_validator, records/kinds.py
_._shapes  # pydantic model_validator, records/kinds.py
_._closure  # pydantic model_validator, records/kinds.py
_._file_is_named  # pydantic field_validator, saffron/intake.py
_._find_is_not_empty  # pydantic field_validator, saffron/intake.py
_._no_core_gate_names  # pydantic field_validator, saffron/repos/policy.py
_.by_hand  # BacklogItem field: extra="forbid" refuses a record that sets it unless it exists
_.related  # BacklogItem field: extra="forbid" refuses a record that sets it unless it exists
_.envelope  # Spec field (§3.2): extra="forbid" needs it for a bug spec to parse
_.envelope_default  # Policy field (§2.1): extra="forbid" needs it for policy.yaml to parse
_.pending_symbols  # Spec field: pydantic validates it, and .saffron/gates/dead.py reads it from YAML
_.understanding  # Plan field (§5.3): validates the extraction turn's plan.json
_.approach  # Plan field (§5.3): validates the extraction turn's plan.json
_.test_strategy  # Plan field (§5.3): validates the extraction turn's plan.json
_.risks  # Plan field (§5.3): validates the extraction turn's plan.json
_.timestamp  # event dataclass field: EventLog writes it through asdict, saffron/events.py
_.row_factory  # sqlite3 reads it on every query, saffron/ledger.py
_.__getattr__  # module attribute hook: saffron/cell/runtime.py, saffron/phases/implement.py

# Called from outside the scanned roots.
_.load_corpus  # docs/evidence/scripts/2026-09-08-lens-corpus.py
_.calibrate_corpus  # docs/evidence/scripts/2026-09-08-lens-corpus.py
_.graded_per_run  # docs/evidence/scripts/2026-09-08-lens-corpus.py
_.score_probes  # docs/evidence/scripts/2026-09-08-lens-corpus.py
_.render_corpus_table  # docs/evidence/scripts/2026-09-08-lens-corpus.py
_.check_probe  # docs/evidence/scripts/2026-09-08-lens-corpus.py
_.render_table  # docs/evidence/scripts/2026-09-07-lens-scoring.py
_.recover_fixture  # docs/evidence/scripts/2026-09-08-recover-fixture.py
_.FIXTURE_FILES  # docs/evidence/scripts/2026-09-08-recover-fixture.py
_.task_results  # .claude/skills/run-saffron-spec-loop/driver.py

# Documented, or edited in place by an open spec.
_.CPU_OFFSET  # dialect value DESIGN.md §5.1 documents, read only by the cell-marked image test
_.FAMILIES  # open specs SA-0101 and SA-0102 edit this table
_.FINDINGS  # open specs SA-0101 and SA-0102 edit this table

# Kept by an operator decision.
_.read_manifest  # harness/register_scoring.py: the pending instrument of docs/superpowers/specs/2026-09-17-prompt-change-measurement-design.md
_.per_1k  # harness/register_scoring.py: the pending instrument of docs/superpowers/specs/2026-09-17-prompt-change-measurement-design.md
_.register_spread  # harness/register_scoring.py: the pending instrument of docs/superpowers/specs/2026-09-17-prompt-change-measurement-design.md
_.driver_path  # harness/register_scoring.py: the pending instrument of docs/superpowers/specs/2026-09-17-prompt-change-measurement-design.md
_.baseline_results  # Ledger: the read-side partner of task_results, read by the ledger tests
_.batch_runs  # ledger read API, kept like baseline_results by operator decision
