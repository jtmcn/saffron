"""A cell runs the `shacl` gate through `CellExecutor` (backlog item 20).

The host suite runs the gate with Saffron's own venv on its path, so it never
shows the gate working where a task runs it.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from saffron.cell import proxy, runtime, worktree
from saffron.gates.runner import CellExecutor, run_gate
from saffron.repos import image
from saffron.repos import mirror as mirror_ops

_ROOT = Path(__file__).resolve().parents[1]
_NETWORK = proxy.proxy_name("shaclcelltest")

_SHAPE = """\
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix ex: <http://example.com/> .
ex:ThingShape a sh:NodeShape ;
    sh:targetClass ex:Thing ;
    sh:property [ sh:path ex:name ; sh:minCount 1 ] .
"""
_GOOD = """\
@prefix ex: <http://example.com/> .
ex:a a ex:Thing ; ex:name "a" .
"""
_BAD = """\
@prefix ex: <http://example.com/> .
ex:b a ex:Thing .
"""


@pytest.fixture
def network():
    runtime.remove_network(_NETWORK)
    runtime.allocate_network(_NETWORK)
    yield _NETWORK
    runtime.remove_network(_NETWORK)


def _commit_repo(path: Path, graph: str) -> str:
    path.mkdir(parents=True)
    gates = path / ".saffron" / "gates"
    gates.mkdir(parents=True)
    for name in ("shacl", "shacl.py"):
        shutil.copy2(_ROOT / ".saffron" / "gates" / name, gates / name)
    (path / "ontology" / "shapes").mkdir(parents=True)
    (path / "ontology" / "shapes" / "thing.ttl").write_text(_SHAPE)
    (path / "graph.ttl").write_text(graph)

    def run(*argv: str) -> None:
        subprocess.run(argv, cwd=path, check=True, capture_output=True)

    run("git", "init", "-q", "-b", "main")
    run("git", "config", "user.email", "t@example.com")
    run("git", "config", "user.name", "t")
    run("git", "add", "-A")
    run("git", "commit", "-qm", "graphs")
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=path, capture_output=True, text=True
    ).stdout.strip()


def _gate_in_a_cell(tmp_path: Path, network: str, graph: str, name: str):
    origin = tmp_path / name
    base = _commit_repo(origin, graph)
    mirror = tmp_path / f"{name}.git"
    subprocess.run(
        ["git", "clone", "--bare", "-q", str(origin), str(mirror)], check=True
    )
    gates_dir = mirror_ops.export_saffron_dir(mirror, base, tmp_path / f"{name}-out")
    volume, container = f"saffron-test-shacl-{name}", f"saffron-test-shacl-{name}"
    runtime.remove_volume(volume)
    runtime.remove_volume(f"{volume}-state")
    runtime.create_volume(volume)
    runtime.remove_container(container)
    try:
        worktree.prepare_worktree(
            mirror=mirror,
            volume=volume,
            base_sha=base,
            branch="saffron/test",
            image=image.cell_tag(_ROOT),
            container=container,
            network=network,
            env={},
            gates_dir=gates_dir,
        )
        in_cell = runtime.exec_(container, ["sh", "-c", "pyshacl --version 2>&1"])
        result = run_gate(
            "shacl",
            Path(worktree.GATES_MOUNT) / ".saffron" / "gates" / "shacl",
            cwd=tmp_path,
            executor=CellExecutor(container),
        )
        return result, in_cell.stdout.strip().splitlines()[0].strip()
    finally:
        runtime.remove_container(container)
        runtime.remove_volume(volume)
        runtime.remove_volume(f"{volume}-state")


@pytest.mark.cell
def test_the_shacl_gate_judges_a_graph_inside_a_cell(tmp_path, network):
    """In the repo's own cell image, `shacl` passes a conforming graph and fails
    one missing a required property. Its `tool` is the cell's own `pyshacl`."""
    good, tool = _gate_in_a_cell(tmp_path, network, _GOOD, "good")
    assert good.status == "pass", good
    assert good.tool == tool
    assert "pyshacl" in tool.lower()

    bad, _ = _gate_in_a_cell(tmp_path, network, _BAD, "bad")
    assert bad.status == "fail", bad
    assert [f.file for f in bad.failures] == ["graph.ttl"]
