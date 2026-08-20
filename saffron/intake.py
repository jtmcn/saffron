"""Spec discovery, parse and validation (DESIGN.md §3.2).

A spec is the input; a task is the execution. This module only knows about the
former.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

SpecType = Literal["feature", "bug", "refactor", "test", "docs", "chore"]
RiskTier = Literal["standard", "elevated"]

_FRONTMATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?(.*)\Z", re.DOTALL)
_CRITERION = re.compile(r"^\s*-\s*\[[ xX]\]\s*(.+?)\s*$", re.MULTILINE)
_CRITERIA_SECTION = re.compile(
    r"^##\s*Acceptance criteria\s*$(.*?)(?=^##\s|\Z)", re.MULTILINE | re.DOTALL
)


class SpecError(ValueError):
    """A spec that cannot be trusted to describe what it asks for."""


class Spec(BaseModel):
    """The unit of work. Never a ticket, an issue, or a prompt."""

    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    type: SpecType
    priority: int = 3
    depends_on: list[str] = Field(default_factory=list)
    envelope: list[str] = Field(default_factory=list)
    touches: list[str] = Field(default_factory=list)
    forbidden: list[str] = Field(default_factory=list)
    budget_usd: float = 10.0
    max_attempts: int = 4
    risk: RiskTier = "standard"

    body: str = ""
    acceptance_criteria: list[str] = Field(default_factory=list)


def parse_spec(text: str) -> Spec:
    match = _FRONTMATTER.match(text)
    if match is None:
        raise SpecError("spec has no YAML frontmatter block")

    raw, body = match.group(1), match.group(2)
    try:
        fields = yaml.safe_load(raw) or {}
    except yaml.YAMLError as exc:
        raise SpecError(f"spec frontmatter is not valid YAML: {exc}") from exc
    if not isinstance(fields, dict):
        raise SpecError("spec frontmatter is not a mapping")

    # A null value for an omitted-but-present key (`touches:`) means "not
    # declared", which is the documented shape for a bug awaiting DIAGNOSE.
    fields = {k: v for k, v in fields.items() if v is not None}

    try:
        return Spec(
            **fields, body=body, acceptance_criteria=_acceptance_criteria(body)
        )
    except ValidationError as exc:
        raise SpecError(f"spec frontmatter is invalid: {exc}") from exc


def load_spec(path: Path) -> tuple[Spec, str]:
    """Parse a spec and return it with its `spec_sha`.

    The sha is over the file's bytes: edit a spec mid-batch and the task is
    invalidated rather than silently building the old thing (DESIGN.md §4.1).
    """
    raw = path.read_bytes()
    return parse_spec(raw.decode()), hashlib.sha256(raw).hexdigest()


def _acceptance_criteria(body: str) -> list[str]:
    section = _CRITERIA_SECTION.search(body)
    return _CRITERION.findall(section.group(1)) if section else []
