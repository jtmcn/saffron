"""One pydantic model per record kind, and the registry that names them.

Every field is a scalar or a list of ids, so a later lift into the ontology
graph is mechanical. An appendix's `title` and `question` are the exception:
short prose the appendix index renders."""

from __future__ import annotations

import datetime as dt
import re
import secrets
from dataclasses import dataclass
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    Strict,
    field_validator,
    model_validator,
)

Status = Literal["open", "partial", "done", "superseded", "wontfix"]
CLOSED: frozenset[str] = frozenset({"done", "superseded", "wontfix"})
_SPEC_ID = r"^[A-Za-z0-9]+-[0-9]+$"
_SECTION = r"^§\d+(\.\d+)*[a-z]?$"
_COMMIT_SHA = r"^[0-9a-f]{7,40}$"

# Strict: a string or bool is refused by name rather than coerced to an int.
Number = Annotated[int, Strict(), Field(ge=1)]

# Items 1–177 keep their numbers; every later item takes a random id, so two
# branches filing at once almost never claim the same one.
RANDOM_ID = r"b-[0-9a-f]{6}"
RandomId = Annotated[str, Field(pattern=rf"^{RANDOM_ID}$")]
ItemId = Number | RandomId


def as_id(token: str) -> ItemId:
    """A backlog id as written: a filename prefix, a citation, an argument."""
    return int(token) if token.isdigit() else token


def new_id(taken: set[ItemId]) -> str:
    while (candidate := f"b-{secrets.token_hex(3)}") in taken:
        pass
    return candidate


class Identified(BaseModel):
    """What every kind's model has: an id the filename repeats."""

    model_config = ConfigDict(extra="forbid")

    id: Annotated[int, Strict()] | str


class BacklogItem(Identified):
    id: ItemId
    title: str = Field(min_length=1)
    status: Status
    tier: Annotated[int, Strict(), Field(ge=0, le=3)] | None = None
    filed: dt.date | None = None
    closed: dt.date | None = None
    by_hand: bool = False
    specs: list[str] = Field(default_factory=list)
    prs: list[Number] = Field(default_factory=list)
    commits: list[str] = Field(default_factory=list)
    cites: list[str] = Field(default_factory=list)
    related: list[ItemId] = Field(default_factory=list)
    superseded_by: ItemId | None = None
    awaiting: list[Number] = Field(default_factory=list)
    """Open pull requests this item waits on — never the one carrying the
    edit, which closes the item in its own diff instead."""

    @field_validator("commits", mode="before")
    @classmethod
    def _commits_are_quoted(cls, v: object) -> object:
        if isinstance(v, list):
            bad = [x for x in v if not isinstance(x, str)]
            if bad:
                raise ValueError(
                    f'commits: quote shas as strings, e.g. "{bad[0]}" — an '
                    f"unquoted all-digit sha reads as a number: {bad}"
                )
        return v

    @model_validator(mode="after")
    def _shapes(self) -> BacklogItem:
        bad = [s for s in self.specs if not re.match(_SPEC_ID, s)]
        if bad:
            raise ValueError(f"specs: not a spec id: {bad}")
        bad = [c for c in self.cites if not re.match(_SECTION, c)]
        if bad:
            raise ValueError(f"cites: not a § address: {bad}")
        bad = [c for c in self.commits if not re.match(_COMMIT_SHA, c)]
        if bad:
            raise ValueError(f"commits: not a sha (7-40 lowercase hex): {bad}")
        return self

    @model_validator(mode="after")
    def _closure(self) -> BacklogItem:
        if self.status in CLOSED:
            if self.closed is None:
                raise ValueError(f"closed: required when status is {self.status}")
            if not (self.specs or self.prs or self.commits):
                raise ValueError("specs, prs or commits: a close names what closed it")
            if self.awaiting:
                raise ValueError(
                    f"awaiting: a {self.status} item waits on nothing; "
                    f"move {self.awaiting} to prs"
                )
        elif self.closed is not None:
            raise ValueError(f"closed: set on an item whose status is {self.status}")
        if self.status == "superseded" and self.superseded_by is None:
            raise ValueError("superseded_by: required when status is superseded")
        if self.status != "superseded" and self.superseded_by is not None:
            raise ValueError(
                f"superseded_by: set on an item whose status is {self.status}"
            )
        if self.filed and self.closed and self.filed > self.closed:
            raise ValueError(f"filed: {self.filed} is after closed {self.closed}")
        return self


# A to Z, then AA: letters are permanent ids.
APPENDIX_ID = r"[A-Z]{1,2}"


AppendixRef = Annotated[str, Field(pattern=rf"^{APPENDIX_ID}$")]


class Appendix(Identified):
    """What one revision found. Never replaced, so it has no status."""

    id: AppendixRef
    title: str = Field(min_length=1)
    revisions: list[Number] = Field(min_length=1)
    question: str = Field(min_length=1)


AdrStatus = Literal["accepted", "superseded", "deprecated"]


class Adr(Identified):
    """One decision, as it stands today. Never edited except to record a
    supersession, which is written on both sides in one pull request."""

    id: Number
    title: str = Field(min_length=1)
    status: AdrStatus
    date: dt.date
    supersedes: list[Number] = Field(default_factory=list)
    superseded_by: list[Number] = Field(default_factory=list)
    principles: list[Number] = Field(default_factory=list)
    appendices: list[AppendixRef] = Field(default_factory=list)


BACKLOG_SECTIONS = ("Problem", "Done looks like", "Record")
ADR_SECTIONS = (
    "Context",
    "Decision",
    "Options considered",
    "Principles",
    "Consequences",
)
# Derived, so a required heading cannot drift out of the allowed ones: a kind
# whose `required` is not a subset makes every record of it unloadable.
ADR_REQUIRED = tuple(s for s in ADR_SECTIONS if s != "Options considered")


@dataclass(frozen=True)
class Kind:
    name: str
    directory: str
    pattern: str
    model: type[Identified]
    hand_written: frozenset[str] = frozenset()
    # `## ` headings the body may use, in order. Empty means the body is free prose.
    sections: tuple[str, ...] = ()
    # The subset of `sections` that must appear. `_sectioned` refuses a missing one.
    required: tuple[str, ...] = ()


KINDS: dict[str, Kind] = {
    "backlog": Kind(
        "backlog",
        "docs/backlog",
        rf"^(\d{{3}}|{RANDOM_ID})-[a-z0-9-]+\.md$",
        BacklogItem,
        frozenset({"README.md", "PRIORITY.md"}),
        sections=BACKLOG_SECTIONS,
        required=("Problem",),
    ),
    "appendix": Kind(
        "appendix",
        "docs/appendices",
        rf"^({APPENDIX_ID})-[a-z0-9-]+\.md$",
        Appendix,
    ),
    "adr": Kind(
        "adr",
        "docs/adr",
        r"^(\d{4})-[a-z0-9-]+\.md$",
        Adr,
        sections=ADR_SECTIONS,
        required=ADR_REQUIRED,
    ),
}
