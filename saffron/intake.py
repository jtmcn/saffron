"""Spec discovery, parse and validation (DESIGN.md §3.2).

A spec is the input; a task is the execution. This module only knows about the
former.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

SpecType = Literal["feature", "bug", "refactor", "test", "docs", "chore"]
RiskTier = Literal["standard", "elevated"]

_FRONTMATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?(.*)\Z", re.DOTALL)
# Captures from one checklist marker up to the next (or the end of the
# section), never stopping at a bare `$` — a wrapped criterion's continuation
# lines belong to it, not to nothing. Whitespace inside the span, including
# the newlines between wrapped lines, is collapsed by the caller.
_CRITERION = re.compile(
    r"^[ \t]*-\s*\[[ xX]\]\s*(.+?)(?=\n[ \t]*-\s*\[[ xX]\]|\Z)",
    re.MULTILINE | re.DOTALL,
)
_CRITERIA_SECTION = re.compile(
    r"^##\s*Acceptance criteria\s*$(.*?)(?=^##\s|\Z)",
    re.MULTILINE | re.DOTALL | re.IGNORECASE,
)


class SpecError(ValueError):
    """A spec that cannot be trusted to describe what it asks for."""


class Criterion(BaseModel):
    """One acceptance criterion and the witness the host checks it by.

    `witness` is a test node id, opaque here as everywhere else: intake never
    splits it and the gate never parses it (§5.4).
    """

    model_config = ConfigDict(extra="forbid")

    claim: str
    """The prose the PR body renders. Where `acceptance:` is declared it *is*
    the acceptance criteria, and the markdown section is omitted."""
    witness: str
    preserves: bool = False
    """The criterion claims the change did *not* break this, so its witness is
    checked the opposite way — green at both sides. A new test can never
    preserve: it did not pass at base."""


class Spec(BaseModel):
    """The unit of work. Never a ticket, an issue, or a prompt."""

    model_config = ConfigDict(extra="forbid")

    # Reaches a filesystem path (out_dir / spec.id) and an href in the index,
    # so it is constrained to the shape CONTEXT.md §10 states.
    id: str = Field(pattern=r"^[A-Za-z0-9]+-[0-9]+$")
    title: str
    type: SpecType
    priority: int = 3
    depends_on: list[str] = Field(default_factory=list)
    envelope: list[str] = Field(default_factory=list)
    touches: list[str] = Field(default_factory=list)
    forbidden: list[str] = Field(default_factory=list)
    # The three ceilings, and this is now where their defaults live: `cli`
    # discards nothing and `CellSpec`'s copies are only reached by tests.
    # 12.0, not the 10.0 that stood here — nothing read this field until now,
    # while `--budget`'s argparse default of 12.0 governed every run, and
    # §3.2's worked example says 12. A silent 17% cut is not a refactor.
    # `gt=0` because these are read now: `max_attempts: 0` reaches
    # `repair_loop`, skips `range(1, 1)` entirely and raises the unreachable
    # assertion — a spec typo surfacing as an infrastructure abort.
    budget_usd: float = Field(default=12.0, gt=0)
    max_attempts: int = Field(default=4, gt=0)
    # The one that has actually stopped a task: SA-0005 died at turn 61 with
    # 56% of its budget unspent, against a hardcoded 60 no spec could raise.
    max_turns: int = Field(default=60, gt=0)
    risk: RiskTier = "standard"

    body: str = ""
    acceptance_criteria: list[str] = Field(default_factory=list)
    acceptance: list[Criterion] = Field(default_factory=list)


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

    reserved = {"body": body, "acceptance_criteria": _acceptance_criteria(body)}
    for key in reserved:
        if key in fields:
            raise SpecError(f"spec frontmatter may not set reserved key {key!r}")

    # One list or the other. Both is two sets of criteria with nothing keeping
    # them in sync, and no way for `pr_body` to say which one it ticks.
    if fields.get("acceptance") and reserved["acceptance_criteria"]:
        raise SpecError(
            "spec declares both `acceptance:` and a `## Acceptance criteria` "
            "section; where `acceptance:` is declared it is the criteria"
        )

    # model_validate, not Spec(**fields): a non-string frontmatter key (`1:`,
    # or an unquoted `on:`) makes ** raise TypeError past this guard.
    try:
        return Spec.model_validate({**fields, **reserved})
    except ValidationError as exc:
        raise SpecError(f"spec frontmatter is invalid: {exc}") from exc


def load_spec(path: Path) -> tuple[Spec, str]:
    """Parse a spec and return it with its `spec_sha`.

    The sha is over the file's bytes: edit a spec mid-batch and the task is
    invalidated rather than silently building the old thing (DESIGN.md §4.1).
    """
    try:
        raw = path.read_bytes()
        text = raw.decode()
    except (OSError, UnicodeDecodeError) as exc:
        raise SpecError(f"spec at {path} could not be read: {exc}") from exc
    return parse_spec(text), hashlib.sha256(raw).hexdigest()


def _acceptance_criteria(body: str) -> list[str]:
    section = _CRITERIA_SECTION.search(body)
    if section is None:
        return []
    # A wrapped criterion's continuation lines carry indentation and the
    # newline itself; neither belongs in the claim the PR body renders.
    return [" ".join(item.split()) for item in _CRITERION.findall(section.group(1))]


@dataclass(frozen=True)
class DiscoveredSpec:
    """One spec `discover_specs` could parse, with the sha it was found at."""

    path: Path
    spec: Spec
    spec_sha: str


@dataclass(frozen=True)
class DiscoveryFailure:
    """One path `discover_specs` could not parse, and why.

    A malformed spec is a refusal candidate downstream (`SA-0016`), never a
    reason for the scan itself to raise.
    """

    path: Path
    reason: str


def discover_specs(
    directory: Path,
) -> tuple[list[DiscoveredSpec], list[DiscoveryFailure]]:
    """Parse every spec in `directory`, letting no single file take down the scan.

    Takes a directory, never a repo: resolving `base_sha` and exporting
    `.saffron/specs/` from it is the caller's job, not this one's.

    Ordered by filename — never by `priority`, which the caller may also
    order by, and never by mtime, which is not stable across a checkout — so
    that a tie resolves the same way on every machine.
    """
    specs: list[DiscoveredSpec] = []
    failures: list[DiscoveryFailure] = []
    for path in sorted(directory.glob("*.md")):
        try:
            spec, spec_sha = load_spec(path)
        except SpecError as exc:
            failures.append(DiscoveryFailure(path=path, reason=str(exc)))
            continue
        specs.append(DiscoveredSpec(path=path, spec=spec, spec_sha=spec_sha))
    return specs, failures
