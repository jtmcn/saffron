"""Control artifacts: the extraction turn and the plan checkpoint (§5.3).

A control artifact left in the workspace is a claim, not a record. The host
extracts and hashes it the moment it is produced and never reads it from /work
again — a validated plan the implementer then quietly edits is exactly the kind
of failure that leaves no trace in the diff.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import PurePosixPath
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from saffron.gates.core.scope import matches
from saffron.gates.core.size import _CEILINGS, _DEFAULT_CEILING

EXTRACTION_PROMPT = (
    "Emit a single <output> block as the last thing in your response. "
    "Do not change files. Do not run commands. "
    "Do not include text outside the block."
)

_BLOCK = re.compile(r"<output>(.*?)</output>", re.DOTALL)


class PlanRejected(Exception):
    """The plan failed host-side validation. No *implementation* token is spent
    — but the checkpoint's own turns were, and a shape rejection is final only
    after a second one has run. `plan_checkpoint` sets `spent_usd`."""

    spent_usd: float = 0.0


class PlanNotSchema(PlanRejected):
    """The output was not the schema — a failure of *shape*, not of content.

    The one rejection worth a single bounded re-prompt (§5.3). Every other
    rejection is about what the plan says, and re-asking would be negotiating.
    """


class ScopeProposed(Exception):
    """The extraction turn proposed scope instead of a plan, and it was
    accepted (SA-0018). Not a rejection: a valid way for an IMPLEMENT attempt
    to end when its `touches` cannot satisfy its own acceptance criteria.

    Carries the validated `proposal` and the exact `raw` `<output>` text it
    came from — hashed by the caller the moment it is produced, the same rule
    `plan.json` follows, and never re-read from `/work`. `plan_checkpoint`
    sets `spent_usd`, mirroring `PlanRejected`.
    """

    spent_usd: float = 0.0

    def __init__(self, proposal: ScopeProposal, raw: str) -> None:
        super().__init__("scope proposed")
        self.proposal = proposal
        self.raw = raw


class Plan(BaseModel):
    understanding: str
    approach: str
    files_to_change: list[str]
    test_strategy: str
    risks: list[str] = Field(default_factory=list)
    blocking_questions: list[str] = Field(default_factory=list)
    estimated_lines: int = Field(gt=0)
    """Added + removed, the same count `size_gate` takes off the real diff.
    Required, not defaulted: a ceiling nothing estimates against is not a
    control (§5.3's plan checkpoint spends zero model calls to reject early)."""


class ScopeProposalNotSchema(PlanRejected):
    """The output claimed `kind: scope_proposal` but was not that schema — a
    shape failure, bounded to one re-prompt exactly like `PlanNotSchema`
    (SA-0018)."""


class ScopeProposalRefused(PlanRejected):
    """Every proposed path already matches the spec's declared `touches` (or
    the proposal named none, or gave no root cause) — refused, not recorded.

    Deliberately re-promptable rather than final like an ordinary content
    `PlanRejected`: a proposal is the door SA-0016's spec-shaped refusal has no
    equivalent for, and treating a refused attempt at it as terminal would
    make the door itself an escape hatch from any spec the agent finds hard.
    The caller gives it exactly one more turn to produce a real plan (or a
    proposal that actually escapes `touches`), the same one turn a shape
    failure already gets.
    """


class ScopeProposal(BaseModel):
    """Proposed scope from inside IMPLEMENT (§5.2's contract, reached from a
    door §5.2 never opened for anything but a bug — SA-0018).

    Not a plan and not `scope.json`'s fuller shape: no `evidence` field, only
    what SA-0018's acceptance criteria ask for — a path list and a root cause.
    """

    kind: Literal["scope_proposal"]
    proposed_touches: list[str]
    root_cause: str


def extraction_kind(raw: str) -> str:
    """Which schema the extraction turn's `<output>` block is claiming.

    Defaults to `"plan"` on anything that is not recognisably a scope
    proposal — including a parse failure — so every existing plan-only path
    (and every existing plan-only test) is completely unaffected; only an
    explicit `"kind": "scope_proposal"` takes the other branch.
    """
    try:
        parsed = json.loads(parse_output_block(raw))
    except ValueError:
        return "plan"
    if isinstance(parsed, dict) and parsed.get("kind") == "scope_proposal":
        return "scope_proposal"
    return "plan"


def validate_scope_proposal(raw: str, *, touches: list[str]) -> ScopeProposal:
    """Validate a scope proposal, or raise a `PlanRejected` subclass.

    A proposal that names nothing outside `touches` is refused rather than
    recorded (SA-0018's acceptance criteria) — an empty `touches` (a bug
    awaiting ratification) always escapes, since there is nothing yet to be
    outside of.
    """
    try:
        proposal = ScopeProposal.model_validate(json.loads(parse_output_block(raw)))
    except (ValueError, ValidationError) as exc:
        raise ScopeProposalNotSchema(
            f"scope proposal is not the schema: {exc}"
        ) from exc

    if not proposal.proposed_touches:
        raise ScopeProposalRefused("scope proposal names no paths")
    if not proposal.root_cause.strip():
        raise ScopeProposalRefused("scope proposal carries no root cause")
    if touches and all(
        _matches_any(path, touches) for path in proposal.proposed_touches
    ):
        raise ScopeProposalRefused(
            "every proposed path is already inside touches — this spec's "
            "touches already cover it, so write a plan instead"
        )
    return proposal


def parse_output_block(text: str) -> str:
    # The last block, because that is what EXTRACTION_PROMPT asks for: a draft
    # block followed by the real one would otherwise validate the draft (§5.3).
    blocks = _BLOCK.findall(text)
    if not blocks:
        raise ValueError("no <output> block in the response")
    return blocks[-1].strip()


def hash_artifact(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _matches_any(path: str, patterns: list[str]) -> bool:
    """Same matcher scope_gate uses — a plan that clears this must also clear the gate."""
    return any(matches(path, pattern) for pattern in patterns)


def _names_a_test(path: str) -> bool:
    """What a test runner would collect: pytest's `test_*.py` / `*_test.py`, and
    the same stems for the other ecosystems a target repo might be (`.spec.ts`,
    `Test.java`). Directory names do not count — a plan must name the file."""
    name = PurePosixPath(path).name
    stem = name.split(".")[0]
    return (
        stem.startswith("test_")
        or stem.endswith("_test")
        or stem.endswith("Test")
        or ".test." in name
        or ".spec." in name
    )


def validate_plan(
    raw: str,
    *,
    touches: list[str],
    forbidden: list[str],
    protected: list[str],
    spec_type: str,
) -> Plan:
    """Validate, or raise PlanRejected. Every rule here costs zero model calls."""
    try:
        plan = Plan.model_validate(json.loads(parse_output_block(raw)))
    except (ValueError, ValidationError) as exc:
        raise PlanNotSchema(f"plan.json is not the schema: {exc}") from exc

    if plan.blocking_questions:
        raise PlanRejected(
            "plan carries a blocking question, which means the spec is "
            f"underspecified: {plan.blocking_questions[0]}"
        )

    if not touches:
        raise PlanRejected(
            "the spec declares no touches — a plan cannot be validated "
            "against an empty set"
        )

    for path in plan.files_to_change:
        if not _matches_any(path, touches):
            raise PlanRejected(f"{path} is outside touches")
        if _matches_any(path, forbidden):
            raise PlanRejected(f"{path} is forbidden")
        if _matches_any(path, protected):
            raise PlanRejected(f"{path} is a protected path")

    # The collection convention, not a substring: `"test" in path` is satisfied
    # by `latest_config.py` — and so is `"test" in name`, since "latest" itself
    # contains it. A rule a plan satisfies by accident is not a rule.
    if spec_type in {"feature", "bug"} and not any(
        _names_a_test(path) for path in plan.files_to_change
    ):
        raise PlanRejected(
            f"a {spec_type} plan names no test file — "
            "acceptance criteria that cannot fail are prose"
        )

    ceiling = _CEILINGS.get(spec_type, _DEFAULT_CEILING)
    if plan.estimated_lines > ceiling:
        raise PlanRejected(
            f"plan's own estimate of {plan.estimated_lines} changed lines "
            f"exceeds the {spec_type} ceiling of {ceiling} — the diff `size` "
            "gate will fail on before a single edit is made"
        )

    return plan
