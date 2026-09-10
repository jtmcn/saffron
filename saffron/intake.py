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
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

SpecType = Literal["feature", "bug", "refactor", "test", "docs", "chore"]
RiskTier = Literal["standard", "elevated"]

_FRONTMATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?(.*)\Z", re.DOTALL)
# A criterion is its marker line plus the *indented, non-marker* lines that
# follow it. A blank line or a column-0 line ends it: `_CRITERIA_SECTION` stops
# only at `##`, so an `###` subsection would otherwise be absorbed into the last
# criterion (measured: SA-0001's ran to 758 chars, 640 of them a table). The
# lookahead keeps an indented or nested checklist from collapsing into one
# criterion, and `[ \t]*` after the `]` keeps a text-less `- [ ]` from swallowing
# the next marker. Whitespace inside the span is collapsed by the caller.
# ponytail: "indented" is the whole rule, so an indented fenced block is
# absorbed and an unindented lazy continuation is still dropped.
_CRITERION = re.compile(
    r"^[ \t]*-\s*\[[ xX]\][ \t]*(.+(?:\n[ \t]+(?!-\s*\[[ xX]\])\S.*)*)", re.MULTILINE
)
_CRITERIA_SECTION = re.compile(
    r"^##\s*Acceptance criteria\s*$(.*?)(?=^##\s|\Z)",
    re.MULTILINE | re.DOTALL | re.IGNORECASE,
)


class SpecError(ValueError):
    """A spec that cannot be trusted to describe what it asks for."""


class DisclosedMutantError(SpecError):
    """A spec that reads cleanly but gives its own mutant away (item 82).

    Carries the parsed spec, which the plain `SpecError` cannot: the
    frontmatter validated and the id is trustworthy, so this refusal is about
    admitting the spec as a *candidate*, not about being unable to read it.
    `scheduler._retired_ids` needs exactly that distinction — a spec refused
    here and then retired to `done/` still credits its dependents, where a file
    that does not parse declares no id to credit.
    """

    def __init__(self, message: str, spec: Spec) -> None:
        super().__init__(message)
        self.spec = spec


class Mutant(BaseModel):
    """The smallest edit that would falsify the claim beside it (§5.4.1).

    Not a unified diff: a diff carries line numbers, and a mutant naming line
    51 stops meaning anything the moment the implementation shifts by a line.
    Exact text is stable under everything except a rewrite of the construct
    itself, and a rewrite of the construct is a change the claim should
    notice.

    Only "empty" is judged here. A `find` that matches more than once, or not
    at all, can only be judged against a tree, and `saffron/mutation.py` is
    where that half lives — this module never reads the repo it describes.
    """

    model_config = ConfigDict(extra="forbid")

    file: str
    find: str
    replace: str = ""

    @field_validator("file")
    @classmethod
    def _file_is_named(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("mutant names no file")
        return value

    @field_validator("find")
    @classmethod
    def _find_is_not_empty(cls, value: str) -> str:
        # An empty `find` matches at every position in the file, so it is not
        # a weak mutant but an unrunnable one — refused here rather than
        # discovered at gate time.
        if not value:
            raise ValueError("mutant find text is empty")
        return value


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
    mutant: Mutant | None = None
    """The edit that would falsify `claim` (§5.4.1). Absent by default, and
    every spec in this repo predates the field — an omitted `mutant` must
    parse exactly as it did before this field existed."""


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
        spec = Spec.model_validate({**fields, **reserved})
    except ValidationError as exc:
        raise SpecError(f"spec frontmatter is invalid: {exc}") from exc

    # Item 82: a mutant the spec itself spells out is a mutant handed to the
    # implementer. The body *is* prompt text — `build_system_prompt` passes it
    # as the substituted `{spec}` value — and so is a claim, which
    # `context.witnesses_block` gives the implementer and `criteria_section`
    # gives the critic. A test written to kill a known edit is the theater
    # `witness` exists to refuse, and its verdict then measures the disclosure
    # rather than the tests. `SA-0063` did exactly this and no reviewer caught
    # it: both lenses that read the diff missed it.
    #
    # Refused at parse, where it costs nothing, and against *every* claim
    # rather than the criterion's own: `witnesses_block` hands the implementer
    # the whole list, so a sibling claim spelling out this mutant's text
    # discloses it just as completely.
    #
    # No length threshold. Whether one is needed has not been measured — this
    # corpus declares two mutants in 54 specs, so the check has fired on the
    # only two chances it has had, which is not evidence about how often it
    # would fire on an honest one. The reasoning for going without is that a
    # `find` has to match exactly once in its file, so a very short one is
    # already unusable; that argument thins as the text gets longer, and
    # `docs/BACKLOG.md` item 82 carries what to do if it starts biting.
    claims = [(c.witness, c.claim) for c in spec.acceptance]
    for criterion in spec.acceptance:
        if criterion.mutant is None:
            continue
        find = criterion.mutant.find
        where = "body" if find in body else None
        if where is None:
            for witness, claim in claims:
                if find in claim:
                    where = (
                        "its own claim"
                        if witness == criterion.witness
                        else f"the claim for {witness}"
                    )
                    break
        if where is not None:
            raise DisclosedMutantError(
                f"{criterion.witness}'s mutant names text this spec also "
                f"puts in {where} ({find!r}); the "
                "implementer reads that, so the witness would be written "
                "to kill a known edit. Pin text the existing code already "
                "determines, or declare a witness and no mutant",
                spec,
            )
    return spec


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
    spec: Spec | None = None
    """Set when the file parsed and was refused on policy rather than shape —
    `DisclosedMutantError`. The id is readable, which is the whole difference
    for `scheduler._retired_ids`."""


def discover_specs(
    directory: Path,
) -> tuple[list[DiscoveredSpec], list[DiscoveryFailure]]:
    """Parse every spec in `directory`, letting no single file take down the scan.

    Takes a directory, never a repo: resolving `base_sha` and exporting
    `.saffron/specs/` from it is the caller's job, not this one's.

    Ordered by filename — never by `priority`, which the caller may also
    order by, and never by mtime, which is not stable across a checkout — so
    that a tie resolves the same way on every machine.

    `Path.glob` is silent for a missing path and for a path that exists but
    is not a directory, exactly as it is for a genuinely empty one — so
    without a check here, an export that produced nothing (a wrong base
    commit, a repo that never had the directory, a path assembled with the
    wrong join) reaches the scheduler indistinguishable from a repo with no
    specs. Only the third case is an ordinary night with no work in it; the
    first two are faults and are refused rather than answered.
    """
    if not directory.exists():
        raise SpecError(f"spec directory {directory} does not exist")
    if not directory.is_dir():
        raise SpecError(f"spec directory {directory} is not a directory")

    specs: list[DiscoveredSpec] = []
    failures: list[DiscoveryFailure] = []
    # Sort on the name, not the `Path`: `PurePath.__lt__` compares
    # `_parts_normcase` (3.14), which case-folds on the Windows flavour, not POSIX.
    for path in sorted(directory.glob("*.md"), key=lambda p: p.name):
        try:
            spec, spec_sha = load_spec(path)
        except DisclosedMutantError as exc:
            failures.append(DiscoveryFailure(path=path, reason=str(exc), spec=exc.spec))
            continue
        except SpecError as exc:
            failures.append(DiscoveryFailure(path=path, reason=str(exc)))
            continue
        specs.append(DiscoveredSpec(path=path, spec=spec, spec_sha=spec_sha))
    return specs, failures
