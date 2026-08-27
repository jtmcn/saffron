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

# The git toplevel, not the cwd: `git ls-files` returns paths relative to the
# directory it runs in, so a gate invoked from a subdirectory resolved neither
# the shapes nor the graphs and reported a repo state that does not exist.
_toplevel = subprocess.run(
    ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True
)
REPO = Path(_toplevel.stdout.strip()) if _toplevel.returncode == 0 else Path.cwd()
SHAPES_DIR = REPO / "ontology" / "shapes"
# Vendored W3C vocabularies are third-party and are not ours to conform.
# ponytail: the negative fixtures exist to be rejected, so they are excluded by
# path. A broken graph parked there dodges this gate — `scope` still requires it
# in `touches` and it is still in the diff. Narrow if that ever stops holding.
# The index is also what "every graph" means: an untracked `.ttl` is not
# validated until it is staged, which `committed` requires before gating anyway.
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
reported = (version.stdout.strip() or version.stderr.strip()).splitlines()
tool = reported[0].strip() if reported else ""
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
tracked = [
    REPO / name
    for name in listed.stdout.split("\0")
    # ls-files reads the index, so a tracked file deleted from the worktree is
    # still listed. `committed` fails that attempt anyway; reading it here would
    # charge a dirty tree to the gate as `error`.
    if name and (REPO / name).is_file()
]
# Both halves come from the index. Globbing the shapes directory instead would
# have reintroduced, for the shapes alone, the untracked-file problem the
# `git ls-files` above exists to close.
shapes = sorted(p for p in tracked if p.is_relative_to(SHAPES_DIR))
graphs = sorted(
    p
    for p in tracked
    if p not in shapes
    and not any(p.relative_to(REPO).as_posix().startswith(x) for x in EXCLUDED)
)

if not graphs and not shapes:
    emit({"gate": "shacl", "status": "skip", "summary": "no graphs in this repo"})
if not shapes:
    error(f"{len(graphs)} graphs and no shapes to validate them against", tool)

import rdflib  # noqa: E402  — after the version probe, so a missing tool is `error`
from pyshacl import validate  # noqa: E402

SH = rdflib.Namespace("http://www.w3.org/ns/shacl#")

data = rdflib.Graph()
# Which file holds the offending triple, keyed on (node, predicate) because SHACL
# reports both. Keyed on the node alone, the alphabetically-first file mentioning
# it won — so every violation about a vocabulary term was blamed on the
# vocabulary even when the bad triple was in a fixture.
# ponytail: first file wins. A pair present in two files — which is what a
# cardinality violation spanning them looks like — names the earlier one. Record
# every file per pair if that ever misdirects a repair turn.
declared_in: dict[tuple[rdflib.term.Node, rdflib.term.Node], str] = {}
# And on the node alone, because a `sh:minCount` violation is about a triple that
# does not exist and so has no pair to key on. Precision first, then the node.
holds_node: dict[rdflib.term.Node, str] = {}
try:
    for path in graphs:
        one = rdflib.Graph().parse(path, format="turtle")
        rel = path.relative_to(REPO).as_posix()
        for subject, predicate, _ in one:
            declared_in.setdefault((subject, predicate), rel)
            holds_node.setdefault(subject, rel)
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
    path = results.value(report, SH.resultPath)
    source = results.value(report, SH.sourceConstraintComponent)
    message = results.value(report, SH.resultMessage)
    failures.append(
        {
            # "" is the fileless failure, which `implement.py` already renders
            # without a path. A directory would anchor to nothing.
            "file": declared_in.get((focus, path)) or holds_node.get(focus, ""),
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
