"""One pydantic model per record kind, and the registry that names them.

Every field is a scalar or a list of ids — never prose — so a later lift into
the ontology graph is mechanical (spec, "Follow-ons")."""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Status = Literal["open", "partial", "done", "superseded", "wontfix"]
CLOSED: frozenset[str] = frozenset({"done", "superseded", "wontfix"})
_SPEC_ID = r"^[A-Za-z0-9]+-[0-9]+$"
_SECTION = r"^§\d+(\.\d+)*[a-z]?$"


class Identified(BaseModel):
    """What every kind's model has — an id the filename repeats, and a status."""

    model_config = ConfigDict(extra="forbid")

    id: int
    status: str


class BacklogItem(Identified):
    model_config = ConfigDict(extra="forbid")

    id: int = Field(ge=1)
    title: str = Field(min_length=1)
    status: Status
    tier: int | None = Field(default=None, ge=0, le=3)
    filed: dt.date | None = None
    closed: dt.date | None = None
    by_hand: bool = False
    specs: list[str] = Field(default_factory=list)
    prs: list[int] = Field(default_factory=list)
    commits: list[str] = Field(default_factory=list)
    cites: list[str] = Field(default_factory=list)
    related: list[int] = Field(default_factory=list)
    superseded_by: int | None = None

    @model_validator(mode="after")
    def _shapes(self) -> BacklogItem:
        bad = [s for s in self.specs if not re.match(_SPEC_ID, s)]
        if bad:
            raise ValueError(f"specs: not a spec id: {bad}")
        bad = [c for c in self.cites if not re.match(_SECTION, c)]
        if bad:
            raise ValueError(f"cites: not a § address: {bad}")
        return self

    @model_validator(mode="after")
    def _closure(self) -> BacklogItem:
        if self.status in CLOSED:
            if self.closed is None:
                raise ValueError(f"closed: required when status is {self.status}")
            if not (self.specs or self.prs or self.commits):
                raise ValueError("specs, prs or commits: a close names what closed it")
        elif self.closed is not None:
            raise ValueError(f"closed: set on an item whose status is {self.status}")
        if self.status == "superseded" and self.superseded_by is None:
            raise ValueError("superseded_by: required when status is superseded")
        return self


@dataclass(frozen=True)
class Kind:
    name: str
    directory: str
    pattern: str
    model: type[Identified]


KINDS: dict[str, Kind] = {
    "backlog": Kind(
        "backlog", "docs/backlog", r"^(\d{3})-[a-z0-9-]+\.md$", BacklogItem
    ),
}
