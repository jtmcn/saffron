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
