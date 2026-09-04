"""Renders the surfaces derived from `ontology/saffron.ttl`.

Dev-only and deliberately outside `saffron/`: `pyproject.toml` states that
nothing under `saffron/` imports a graph library, and this module imports two.
"""

from __future__ import annotations

import re
from pathlib import Path

import rdflib

NS = "https://saffron.dev/ns#"


def members(class_name: str, *, vocabulary: Path) -> list[str]:
    """Local names of every instance of `saffron:<class_name>`, in the order
    they first appear in the vocabulary's own text.

    Source order, not graph order: rdflib iterates unordered, and the committed
    enumerations are in an order a reader chose. Sorting would rewrite them.
    """
    text = vocabulary.read_text()
    graph = rdflib.Graph().parse(vocabulary, format="turtle")
    names = [
        str(s).removeprefix(NS)
        for s in graph.subjects(rdflib.RDF.type, rdflib.URIRef(f"{NS}{class_name}"))
    ]

    def first_offset(name: str) -> int:
        found = re.search(rf"saffron:{re.escape(name)}\b", text)
        return found.start() if found else len(text)

    return sorted(names, key=first_offset)
