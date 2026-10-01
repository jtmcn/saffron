"""REVIEW's two cells, started as `_drive_cell` starts them beside a live
implementer, and probed from inside (items 127, 131 and 135). Needs the image
CLAUDE.md names and `SAFFRON_ALLOW_HOST_PROCESS` for this host's listeners.

Every negative connect has a positive control from the same client, because a
probe that cannot succeed reports isolation (principle 34, item 108).
"""

import base64
import json
import os
import subprocess
from pathlib import Path

import pytest

from saffron.cell import proxy, runtime, session, worktree
from saffron.gates.suite import GateSuite, SuiteRun
from saffron.repos import image as repo_image
from saffron.repos import mirror as mirror_ops
from saffron.repos.policy import load_policy

pytestmark = pytest.mark.cell

_SPEC_ID = "SA-9127"
_PORT = 8127
_MARKER = "/usr/local/saffron-implementer-marker"
_TAMPERED = "Python tampered"
# The implementer, as root, swaps the `python3` on its PATH for one that lies
# about its version and still runs everything else.
_TAMPER = (
    'p=$(command -v python3); real=$(readlink -f "$p"); rm -f "$p"; '
    'printf \'#!/bin/sh\\n[ "$1" = --version ] && { echo "%s"; exit 0; }'
    '\\nexec %s "$@"\\n\' '
    f'"{_TAMPERED}" "$real" > "$p"; chmod 755 "$p"'
)
_ENV_NAMES = "import json, os; print(json.dumps(sorted(os.environ)))"
_OUTSIDE = "1.1.1.1"

# One program for every probe: argv is a JSON list of (label, kind, args).
_PROBE = r"""
import json, os, socket, sys, time

def connect(host, port, tries=1):
    for _ in range(tries):
        s = socket.socket(); s.settimeout(3)
        try:
            s.connect((host, int(port))); return "connected"
        except OSError as e:
            last = type(e).__name__
        finally:
            s.close()
        time.sleep(1)
    return last

def tunnel(proxy, port, target):
    s = socket.create_connection((proxy, int(port)), timeout=10)
    s.sendall(f"CONNECT {target} HTTP/1.1\r\nHost: {target}\r\n\r\n".encode())
    line = s.recv(200).split(b"\r\n")[0].decode()
    s.close()
    return line.split()[1] if len(line.split()) > 1 else line

def own_ip(peer):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect((peer, 9))
    return s.getsockname()[0]

out = {}
for label, kind, args in json.loads(sys.argv[1]):
    if kind == "env":
        out[label] = "present" if os.environ.get(args[0]) else "absent"
    elif kind == "env_names":
        out[label] = sorted(os.environ)
    elif kind == "file":
        out[label] = "present" if os.path.exists(args[0]) else "absent"
    elif kind == "own_ip":
        out[label] = own_ip(args[0])
    elif kind == "connect":
        out[label] = connect(*args)
    elif kind == "tunnel":
        out[label] = tunnel(*args)
print(json.dumps(out))
"""

_LISTEN = (
    'nohup python3 -c "import http.server as h; '
    f"h.HTTPServer(('0.0.0.0', {_PORT}), h.SimpleHTTPRequestHandler)"
    '.serve_forever()" >/dev/null 2>&1 &'
)

# The same probe, as the Gate-only cell's `tests` gate. Its targets arrive
# through the repo's declared gate env.
_TESTS_GATE = f"""#!/bin/sh
cat > /tmp/probe.py <<'EOF'
{_PROBE}
EOF
{_LISTEN}
report=$(python3 /tmp/probe.py "$SAFFRON_PROBE_PLAN" | base64 | tr -d '\\n')
printf '{{"gate":"tests","status":"pass","tool":"%s","collected":["t::a"],"summary":"%s"}}\\n' \\
  "$(python3 --version)" "$report"
"""

_POLICY = """gates:
  tests: { blocking: true }
integrity:
  test_paths: ["tests/**"]
thread_env:
  SAFFRON_PROBE_MARK: "1"
"""


def _git(repo: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-c", "user.email=t@e", "-c", "user.name=t", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return done.stdout.strip()


def _probe(container: str, plan: list) -> dict:
    done = runtime.exec_(
        container, ["python3", "-c", _PROBE, json.dumps(plan)], timeout_s=120
    )
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


@pytest.fixture(scope="module")
def task(tmp_path_factory):
    """One task's cells up, with a listener the implementer backgrounded and a
    file it wrote as root outside `/work`."""
    root = tmp_path_factory.mktemp("review-cells")
    repo = root / "review-cells-origin"
    (repo / ".saffron" / "gates").mkdir(parents=True)
    (repo / ".saffron" / "Dockerfile").write_text("FROM saffron/cell-base:python\n")
    (repo / ".saffron" / "policy.yaml").write_text(_POLICY)
    gate = repo / ".saffron" / "gates" / "tests"
    gate.write_text(_TESTS_GATE)
    gate.chmod(0o755)
    (repo / "app.py").write_text("X = 1\n")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    base = _git(repo, "rev-parse", "HEAD")
    (repo / "app.py").write_text("X = 2\n")
    patch = _git(repo, "diff") + "\n"

    saved = {
        k: os.environ.get(k) for k in ("ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN")
    }
    os.environ["ANTHROPIC_API_KEY"] = "sk-ant-host-key-must-not-reach"
    os.environ["CLAUDE_CODE_OAUTH_TOKEN"] = "host-token-for-the-critic-only"

    mirror = mirror_ops.ensure_mirror(repo, root / "m.git")
    policy, _ = load_policy(repo)
    gates_dir = mirror_ops.export_saffron_dir(mirror, base, root / "gates")
    spec = session.CellSpec(
        spec_id=_SPEC_ID,
        spec_sha="0" * 40,
        branch=f"saffron/{_SPEC_ID}",
        base_sha=base,
        touches=["app.py"],
        spec_type="bug",
        body="",
    )
    names = dict(
        network="saffron-cells",
        critic_network=session.CRITIC_NETWORK,
        volume=f"saffron-wt-{_SPEC_ID}",
        state=f"saffron-st-{_SPEC_ID}",
        container=f"saffron-cell-{_SPEC_ID}",
    )
    created: set[str] = set()
    try:
        session.cell_up(
            repo=repo,
            mirror=mirror,
            tree_base=base,
            branch=spec.branch,
            network=names["network"],
            critic_network=names["critic_network"],
            volume=names["volume"],
            state=names["state"],
            container=names["container"],
            gates_dir=gates_dir,
            thread_env=policy.thread_env,
            created=created,
            note=lambda *a: None,
        )
        impl = names["container"]
        proxy_ip = runtime.container_ip(proxy.PROXY_NAME)
        assert proxy_ip
        runtime.exec_(impl, ["sh", "-c", _LISTEN], timeout_s=30)
        runtime.exec_(impl, ["sh", "-c", f"echo x > {_MARKER}"], timeout_s=30)
        runtime.exec_(impl, ["sh", "-c", _TAMPER], timeout_s=30)
        found = _probe(
            impl,
            [
                ["ip", "own_ip", [proxy_ip]],
                ["marker", "file", [_MARKER]],
            ],
        )
        found |= _probe(impl, [["listener", "connect", [found["ip"], _PORT, 5]]])
        impl_version = runtime.exec_(impl, ["python3", "--version"], timeout_s=30)
        # Controls on the implementer's side: its listener answers, its file
        # exists, and its `python3` lies.
        assert found["listener"] == "connected", found
        assert found["marker"] == "present", found
        assert impl_version.stdout.strip() == _TAMPERED, impl_version
        # What the bare image carries, so a cell's env is read as a difference.
        bare = runtime.run_ephemeral(
            repo_image.cell_tag(repo),
            ["sh", "-c", f"python3 --version; python3 -c '{_ENV_NAMES}'"],
            network=session.CRITIC_NETWORK,
            env={},
        )
        assert bare.returncode == 0, bare.stderr
        image_version, image_env = bare.stdout.strip().splitlines()
        yield {
            "spec": spec,
            "repo": repo,
            "mirror": mirror,
            "gates_dir": gates_dir,
            "policy": policy,
            "patch": patch,
            "created": created,
            "impl_ip": found["ip"],
            "proxy_ip": proxy_ip,
            "critic_proxy": session.proxy_address(runtime.SUBNETS["critic"]),
            "image_version": image_version,
            "image_env": set(json.loads(image_env)),
        }
    finally:
        session.cell_down(
            network=names["network"],
            critic_network=names["critic_network"],
            volume=names["volume"],
            state=names["state"],
            container=names["container"],
            created=created,
            note=lambda *a: None,
        )
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _critic(task):
    return session.critic_cell(
        spec=task["spec"],
        repo=task["repo"],
        mirror=task["mirror"],
        network=session.CRITIC_NETWORK,
        env=session.cell_env(task["critic_proxy"], task["policy"].thread_env),
        gates_dir=task["gates_dir"],
        patch=task["patch"],
        created=task["created"],
        note=lambda *a: None,
    )


def test_the_critic_cell_and_the_implementer_cannot_reach_each_other(task):
    """Item 135. On the shared task network both directions connected
    (2026-09-30). The critic cell reaches the proxy and nothing of the
    implementer's, and the implementer reaches nothing of the critic's."""
    critic_proxy = task["critic_proxy"]
    port = proxy.PROXY_PORT
    with _critic(task) as critic:
        mine = _probe(critic, [["ip", "own_ip", [critic_proxy]]])["ip"]
        runtime.exec_(critic, ["sh", "-c", _LISTEN], timeout_s=30)
        seen = _probe(
            critic,
            [
                ["proxy", "connect", [critic_proxy, port]],
                ["own", "connect", [mine, _PORT, 5]],
                ["implementer", "connect", [task["impl_ip"], _PORT]],
                ["proxy_cells_leg", "connect", [task["proxy_ip"], port]],
                [
                    "tunnel_upstream",
                    "tunnel",
                    [critic_proxy, port, "api.anthropic.com:443"],
                ],
                [
                    "tunnel_implementer",
                    "tunnel",
                    [critic_proxy, port, f"{task['impl_ip']}:{_PORT}"],
                ],
            ],
        )
        back = _probe(
            f"saffron-cell-{_SPEC_ID}", [["critic", "connect", [mine, _PORT]]]
        )
    assert seen["proxy"] == "connected", seen
    assert seen["own"] == "connected", seen
    assert seen["tunnel_upstream"] == "200", seen
    assert seen["implementer"] != "connected", seen
    assert seen["proxy_cells_leg"] != "connected", seen
    assert seen["tunnel_implementer"] == "403", seen
    assert back["critic"] != "connected", back


def test_the_critic_cell_holds_the_token_alone_and_the_images_rootfs(task):
    """Item 127. The critic cell's env is the bare image's plus what `cell_env`
    puts there, the token among it. Nothing else arrives from the host. What
    the implementer changed as root is absent."""
    # Spelled out, not read off `cell_env`: a leak there would read as expected.
    expected = {
        "HTTPS_PROXY",
        "HTTP_PROXY",
        "NO_PROXY",
        "CLAUDE_CONFIG_DIR",
        "CLAUDE_CODE_OAUTH_TOKEN",
        *task["policy"].thread_env,
    }
    with _critic(task) as critic:
        seen = _probe(
            critic,
            [
                ["names", "env_names", []],
                ["token", "env", ["CLAUDE_CODE_OAUTH_TOKEN"]],
                ["marker", "file", [_MARKER]],
                ["outside", "connect", [_OUTSIDE, 443]],
            ],
        )
        version = runtime.exec_(critic, ["python3", "--version"], timeout_s=30)
    assert set(seen["names"]) - task["image_env"] == expected, seen
    assert seen["token"] == "present", seen
    assert seen["marker"] == "absent", seen
    assert version.stdout.strip() == task["image_version"], version
    assert seen["outside"] != "connected", seen


def test_the_gate_only_cell_holds_no_credential_and_reaches_nothing(task):
    """Item 131, through `_gate_cell_suite` as REVIEW calls it. Its gate reports
    from inside: the image's env plus the declared gate env alone, no route to
    either proxy leg or outside, and none of the implementer's files. Its `tool`
    is the image's `python3`, not the one the implementer swapped. Its own
    listener is the control. It reaches no proxy, by design."""
    critic_proxy = task["critic_proxy"]
    port = proxy.PROXY_PORT
    plan = [
        ["names", "env_names", []],
        ["marker", "file", [_MARKER]],
        ["own", "connect", ["127.0.0.1", _PORT, 5]],
        ["proxy_cells_leg", "connect", [task["proxy_ip"], port]],
        ["proxy_critic_leg", "connect", [critic_proxy, port]],
        ["implementer", "connect", [task["impl_ip"], _PORT]],
        ["outside", "connect", [_OUTSIDE, 443]],
    ]
    policy = task["policy"]
    gate_env = {**policy.thread_env, "SAFFRON_PROBE_PLAN": json.dumps(plan)}
    suite = GateSuite(
        gates=policy.gate_executables(Path(worktree.GATES_MOUNT)),
        spec=task["spec"],
        policy=policy,
        diff_base=task["spec"].tree_base,
    )
    comparison = session._gate_cell_suite(
        spec=task["spec"],
        repo=task["repo"],
        mirror=task["mirror"],
        gates_dir=task["gates_dir"],
        thread_env=gate_env,
        patch=task["patch"],
        suite=suite,
        baseline=SuiteRun(
            results=[], effective_risk="standard", advisory_gates=frozenset()
        ),
        created=task["created"],
        note=lambda *a: None,
    )
    (tests,) = [r for r in comparison.run.results if r.gate == "tests"]
    assert tests.tool == task["image_version"], tests
    seen = json.loads(base64.b64decode(tests.summary))
    assert seen["own"] == "connected", seen
    assert set(seen["names"]) - task["image_env"] == set(gate_env), seen
    assert seen["marker"] == "absent", seen
    for target in ("proxy_cells_leg", "proxy_critic_leg", "implementer", "outside"):
        assert seen[target] != "connected", (target, seen)
