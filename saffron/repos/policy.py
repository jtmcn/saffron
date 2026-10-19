"""`.saffron/policy.yaml` — everything repo-shaped that is not an executable.

Core supplies the meaning of a gate role; the repo supplies the executable
(DESIGN.md §5.4).
"""

from __future__ import annotations

import hashlib
import os
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Annotated

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from saffron.gates.core.scope import matches

# A gate name reaches a filesystem path and then an exec, so it is constrained
# the way Spec.id is: no separator, nothing that climbs out of .saffron/gates.
GateName = Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]+$")]

# Core's names, never a repo's: a declared `criteria` shadowed the host's own
# result (item 22). A test holds this equal to factory:CoreGate.
CORE_GATE_NAMES = frozenset(
    {
        "scope",
        "size",
        "secrets",
        "integrity",
        "census",
        "committed",
        "criteria",
        "revert",
        "witness",
    }
)


# Versioned per module (DESIGN.md §3.2). Only 1 exists today.
SCHEMA_VERSIONS: tuple[int, ...] = (1,)


class PolicyError(ValueError):
    """A repo whose declarations cannot be trusted. It fails preflight."""


class GateDeclaration(BaseModel):
    model_config = ConfigDict(extra="forbid")

    blocking: bool = True


class IntegrityPatterns(BaseModel):
    """The repo's vocabulary for a question core asks (DESIGN.md §5.4).

    Read in v0, acted on in v1 — the `integrity` gate exists to catch an agent
    gaming a gate, and v0 has no agent.
    """

    model_config = ConfigDict(extra="forbid")

    test_paths: list[str] = Field(default_factory=list)
    suppressions: list[str] = Field(default_factory=list)
    gate_config: list[str] = Field(default_factory=list)


class ConstantPattern(BaseModel):
    """One spelling of a constant, and the mutant that falsifies it.

    `pattern` is a Python `re` expression whose `name` group names the
    constant and whose `value` group is the span `constant_mutants` edits.
    `replace` is a template `re` expands against a match of `pattern`.
    It takes the `value` span's place, so it names the value's own group
    and nothing else a match of `pattern` does not also carry.
    """

    model_config = ConfigDict(extra="forbid")

    pattern: str
    replace: str

    @model_validator(mode="after")
    def _is_checkable(self) -> ConstantPattern:
        try:
            compiled = re.compile(self.pattern)
        except re.error as exc:
            raise ValueError(
                f"witness constant pattern {self.pattern!r} is not a valid regular expression: {exc}"
            ) from exc
        if "name" not in compiled.groupindex:
            raise ValueError(
                f"witness constant pattern {self.pattern!r} has no `name` group"
            )
        if "value" not in compiled.groupindex:
            raise ValueError(
                f"witness constant pattern {self.pattern!r} has no `value` group"
            )
        try:
            compiled.sub(self.replace, "")
        except (re.error, IndexError) as exc:
            raise ValueError(
                f"witness constant replace {self.replace!r} for pattern {self.pattern!r}: {exc}"
            ) from exc
        return self


class WitnessPatterns(BaseModel):
    """The repo's vocabulary for deriving a constant mutant from its own
    diff (DESIGN.md §5.4.1, backlog item b-5b1f8a).

    Every field is absent by default. An omitted `witness:` block must
    derive nothing, since every spec and every repo predates this field.
    """

    model_config = ConfigDict(extra="forbid")

    witness_name: str | None = None
    witness_body: str | None = None
    constants: list[ConstantPattern] = Field(default_factory=list)

    @field_validator("witness_name")
    @classmethod
    def _witness_name_is_checkable(cls, value: str | None) -> str | None:
        if value is None:
            return value
        try:
            compiled = re.compile(value)
        except re.error as exc:
            raise ValueError(
                f"witness_name {value!r} is not a valid regular expression: {exc}"
            ) from exc
        if "name" not in compiled.groupindex:
            raise ValueError(f"witness_name {value!r} has no `name` group")
        return value

    @field_validator("witness_body")
    @classmethod
    def _witness_body_is_checkable(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if "{name}" not in value:
            raise ValueError(f"witness_body {value!r} has no {{name}} in it")
        try:
            re.compile(value.replace("{name}", re.escape("x")))
        except re.error as exc:
            raise ValueError(
                f"witness_body {value!r} is not a valid regular expression once {{name}} is filled in: {exc}"
            ) from exc
        return value


class Policy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Absent or 1 reads as the integer 1. Any other value is refused below.
    schema_version: int = 1
    gates: dict[GateName, GateDeclaration] = Field(default_factory=dict)
    elevate_on: list[str] = Field(default_factory=list)
    protected: list[str] = Field(default_factory=list)
    integrity: IntegrityPatterns = Field(default_factory=IntegrityPatterns)
    witness: WitnessPatterns = Field(default_factory=WitnessPatterns)
    thread_env: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _schema_version_is_supported(cls, data: object) -> object:
        """Refuse a bool or a float by its own type, before pydantic coerces it."""
        if isinstance(data, dict) and "schema_version" in data:
            value = data["schema_version"]
            if type(value) is not int or value not in SCHEMA_VERSIONS:
                raise ValueError(
                    f"schema_version {value!r} is not supported; this engine "
                    f"reads: {sorted(SCHEMA_VERSIONS)}"
                )
        return data

    @field_validator("gates")
    @classmethod
    def _no_core_gate_names(
        cls, gates: dict[str, GateDeclaration]
    ) -> dict[str, GateDeclaration]:
        if taken := sorted(CORE_GATE_NAMES & gates.keys()):
            raise ValueError(
                f"{', '.join(taken)}: a core gate's name, which a repo cannot declare"
            )
        return gates

    def gate_executables(self, repo_dir: Path) -> dict[str, Path]:
        """Declared gates in declaration order, mapped to their executables."""
        gates_dir = repo_dir / ".saffron" / "gates"
        return {name: gates_dir / name for name in self.gates}


def effective_risk(
    spec_risk: str, changed_files: Sequence[str], elevate_on: Sequence[str]
) -> str:
    """§5.6: `elevated` when the spec says so, or when a changed path matches
    an `elevate_on` pattern. Otherwise the spec's own tier, unchanged.

    Pure, so the wiring spec's own rule — compute this once per attempt, from
    the changed-file list `_suite` already built, never from a second read —
    is the caller's to keep, not this function's. `matches` is `scope`'s own
    glob (`*` stops at `/`, `**` doesn't) — `fnmatch` and `PurePath.full_match`
    are both wrong here, for the reasons `scope.py` gives.
    """
    if spec_risk == "elevated":
        return "elevated"
    for path in changed_files:
        for pattern in elevate_on:
            if matches(path, pattern):
                return "elevated"
    return spec_risk


def load_policy(repo_dir: Path) -> tuple[Policy, str]:
    path = repo_dir / ".saffron" / "policy.yaml"
    if not path.is_file():
        raise PolicyError(f"no policy.yaml at {path}")

    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise PolicyError(f"policy.yaml at {path} could not be read: {exc}") from exc

    try:
        fields = yaml.safe_load(raw.decode()) or {}
    except (yaml.YAMLError, UnicodeDecodeError) as exc:
        raise PolicyError(f"policy.yaml is not valid YAML: {exc}") from exc

    try:
        policy = Policy.model_validate(fields)
    except ValidationError as exc:
        raise PolicyError(f"policy.yaml is invalid: {exc}") from exc

    for name, executable in policy.gate_executables(repo_dir).items():
        if not executable.is_file():
            raise PolicyError(f"gate {name!r} declared but {executable} does not exist")
        if not os.access(executable, os.X_OK):
            raise PolicyError(f"gate {name!r} at {executable} is not executable")

    return policy, hashlib.sha256(raw).hexdigest()
