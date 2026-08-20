"""`.saffron/policy.yaml` — everything repo-shaped that is not an executable.

Core supplies the meaning of a gate role; the repo supplies the executable
(DESIGN.md §5.4).
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class PolicyError(ValueError):
    """A repo whose declarations cannot be trusted. It fails preflight."""


class GateDeclaration(BaseModel):
    model_config = ConfigDict(extra="forbid")

    blocking: bool = True
    when: str | None = None


class IntegrityPatterns(BaseModel):
    """The repo's vocabulary for a question core asks (DESIGN.md §5.4).

    Read in v0, acted on in v1 — the `integrity` gate exists to catch an agent
    gaming a gate, and v0 has no agent.
    """

    model_config = ConfigDict(extra="forbid")

    test_paths: list[str] = Field(default_factory=list)
    suppressions: list[str] = Field(default_factory=list)
    gate_config: list[str] = Field(default_factory=list)


class Policy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gates: dict[str, GateDeclaration] = Field(default_factory=dict)
    elevate_on: list[str] = Field(default_factory=list)
    protected: list[str] = Field(default_factory=list)
    envelope_default: list[str] = Field(default_factory=list)
    integrity: IntegrityPatterns = Field(default_factory=IntegrityPatterns)
    thread_env: dict[str, str] = Field(default_factory=dict)

    def gate_executables(self, repo_dir: Path) -> dict[str, Path]:
        """Declared gates in declaration order, mapped to their executables."""
        gates_dir = repo_dir / ".saffron" / "gates"
        return {name: gates_dir / name for name in self.gates}


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
