#!/usr/bin/env python3
"""SHACL validation of every graph this repo owns -> the gate contract.

A repo-defined gate against a hard-to-fake surface (DESIGN.md §5.4). It is keyed
on a file pattern rather than a list, which is the whole point: `tests/ontology/`
validates the graphs it names, and this validates every `.ttl` in the tree, so a
new graph no test loads is still checked.
"""

import json
import subprocess
import sys
from pathlib import Path

REPO = Path.cwd()
SHAPES_DIR = REPO / "ontology" / "shapes"
# Vendored W3C vocabularies are third-party and are not ours to conform.
# ponytail: the negative fixtures exist to be rejected, so they are excluded by
# path. A broken graph parked there dodges this gate — `scope` still requires it
# in `touches` and it is still in the diff. Narrow if that ever stops holding.
EXCLUDED = ("ontology/vendor/", "tests/ontology/fixtures/negative/")


def emit(payload):
    print(json.dumps(payload))
    sys.exit(0)


def error(summary, tool=None):
    payload = {"gate": "shacl", "status": "error", "summary": summary}
    if tool:
        payload["tool"] = tool
    emit(payload)


try:
    version = subprocess.run(["pyshacl", "--version"], capture_output=True, text=True)
except FileNotFoundError:
    error("pyshacl not on PATH")
if version.returncode != 0:
    error("pyshacl not on PATH")
# pyshacl prints its version on stderr. Taking stdout alone produced a `tool` of
# "" on a gate that otherwise passed — the exact false green Appendix H is about,
# so an empty identifier is an error rather than a field left blank.
tool = (version.stdout.strip() or version.stderr.strip()).splitlines()[0].strip()
if not tool:
    error("pyshacl ran and reported no version")

# Tracked files only. rglob walked `.venv` and validated four of pyshacl's own
# asset graphs as if this repo owned them — and a cell, whose venv is at
# /opt/venv, would not have seen them, so host and cell disagreed on what the
# gate measured.
listed = subprocess.run(
    ["git", "ls-files", "-z", "*.ttl"], capture_output=True, text=True, cwd=REPO
)
if listed.returncode != 0:
    error(f"git ls-files failed: {listed.stderr.strip()}", tool)
graphs = sorted(
    REPO / name
    for name in listed.stdout.split("\0")
    if name and not any(name.startswith(x) for x in EXCLUDED)
)
shapes = sorted(SHAPES_DIR.glob("*.ttl")) if SHAPES_DIR.is_dir() else []

if not graphs and not shapes:
    emit({"gate": "shacl", "status": "skip", "summary": "no graphs in this repo"})
if not shapes:
    error(f"{len(graphs)} graphs and no shapes to validate them against", tool)

import rdflib  # noqa: E402  — after the version probe, so a missing tool is `error`
from pyshacl import validate  # noqa: E402

SH = rdflib.Namespace("http://www.w3.org/ns/shacl#")

data = rdflib.Graph()
# Which file introduced a node, so a violation names a path rather than an IRI.
declared_in: dict[rdflib.term.Node, str] = {}
try:
    for path in graphs:
        one = rdflib.Graph().parse(path, format="turtle")
        rel = path.relative_to(REPO).as_posix()
        for subject in set(one.subjects()):
            declared_in.setdefault(subject, rel)
        data += one
    shapes_graph = rdflib.Graph()
    for path in shapes:
        shapes_graph.parse(path, format="turtle")
except Exception as exc:  # a graph that will not parse is not a conformance result
    error(f"{type(exc).__name__}: {exc}", tool)

try:
    conforms, results, _ = validate(data, shacl_graph=shapes_graph, advanced=True)
except Exception as exc:
    error(f"pyshacl raised {type(exc).__name__}: {exc}", tool)

failures = []
for report in results.subjects(rdflib.RDF.type, SH.ValidationResult):
    focus = results.value(report, SH.focusNode)
    source = results.value(report, SH.sourceConstraintComponent)
    message = results.value(report, SH.resultMessage)
    failures.append(
        {
            "file": declared_in.get(focus, "ontology/"),
            "code": str(source).rsplit("#", 1)[-1] if source else "shacl",
            "message": f"{focus}: {message}".strip(),
        }
    )

emit(
    {
        "gate": "shacl",
        "status": "fail" if failures else "pass",
        "tool": tool,
        "failures": failures,
        "summary": f"{len(failures)} violations across {len(graphs)} graphs",
    }
)
