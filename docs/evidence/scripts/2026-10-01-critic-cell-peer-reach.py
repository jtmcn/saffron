"""Item 135: whether the critic cell and the implementer's container reach each other.

`usage: SAFFRON_ALLOW_HOST_PROCESS=... python <this> [--shared]`

Starts the implementer cell through `cell_up` and the critic cell through
`critic_cell`, as `_drive_cell` does. Each cell runs a listener, and each
connect has a positive control beside it (principle 34). `--shared` puts the
critic cell on the task network, the layout measured on 2026-09-30.
Needs the cell runtime and `saffron/cell-base:python` on the host.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from saffron.cell import proxy, runtime, session
from saffron.repos import mirror as mirror_ops
from saffron.repos.policy import load_policy

PORT = 8135
LISTEN = (
    'nohup python3 -c "import http.server as h; '
    f"h.HTTPServer(('0.0.0.0', {PORT}), h.SimpleHTTPRequestHandler).serve_forever()\" "
    ">/dev/null 2>&1 &"
)
CONNECT = (
    "import socket,sys\n"
    "s=socket.socket(); s.settimeout(4)\n"
    "try:\n s.connect((sys.argv[1], int(sys.argv[2]))); print('CONNECTED')\n"
    "except Exception as e: print('REFUSED', type(e).__name__, e)\n"
)
# Read from inside: `container_ip` on a cell matches the proxy address in its env.
OWN_IP = (
    "import socket,sys; s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM); "
    "s.connect((sys.argv[1], 9)); print(s.getsockname()[0])"
)
LISTENERS = (
    "for f in ('/proc/net/tcp','/proc/net/tcp6'):\n"
    " for l in open(f).read().splitlines()[1:]:\n"
    "  p=l.split()\n"
    "  if p[3]=='0A': print(f, p[1])\n"
)
SPEC_ID = "SA-9135"


def _git(repo: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-c", "user.email=t@e", "-c", "user.name=t", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return done.stdout.strip()


def _py(container: str, code: str, *args: str) -> str:
    done = runtime.exec_(container, ["python3", "-c", code, *args], timeout_s=30)
    return (done.stdout + done.stderr).strip()


def _listen(container: str) -> None:
    runtime.exec_(container, ["sh", "-c", LISTEN], timeout_s=30)


def _fixture(root: Path) -> tuple[Path, str, str]:
    repo = root / "p135"
    (repo / ".saffron" / "gates").mkdir(parents=True)
    (repo / ".saffron" / "Dockerfile").write_text("FROM saffron/cell-base:python\n")
    (repo / ".saffron" / "policy.yaml").write_text(
        "gates:\n  tests: { blocking: true }\nintegrity:\n  test_paths: ['tests/**']\n"
    )
    gate = repo / ".saffron" / "gates" / "tests"
    gate.write_text("#!/bin/sh\necho '{}'\n")
    gate.chmod(0o755)
    (repo / "app.py").write_text("X = 1\n")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    base = _git(repo, "rev-parse", "HEAD")
    # `critic_cell` refuses an empty patch.
    (repo / "app.py").write_text("X = 2\n")
    return repo, base, _git(repo, "diff") + "\n"


def main() -> int:
    shared = "--shared" in sys.argv[1:]
    root = Path(tempfile.mkdtemp(prefix="p135-"))
    repo, base, patch = _fixture(root)
    mirror = mirror_ops.ensure_mirror(repo, root / "m.git")
    policy, _ = load_policy(repo)
    gates_dir = mirror_ops.export_saffron_dir(mirror, base, root / "gates")
    spec = session.CellSpec(
        spec_id=SPEC_ID,
        spec_sha="0" * 40,
        branch=f"saffron/{SPEC_ID}",
        base_sha=base,
        touches=["app.py"],
        spec_type="bug",
        body="",
    )
    network = "saffron-cells"
    critic_network = network if shared else session.CRITIC_NETWORK
    own_critic_network = None if shared else critic_network
    volume, state = f"saffron-wt-{SPEC_ID}", f"saffron-st-{SPEC_ID}"
    impl = f"saffron-cell-{SPEC_ID}"
    created: set[str] = set()
    try:
        session.cell_up(
            repo=repo,
            mirror=mirror,
            tree_base=base,
            branch=spec.branch,
            gates_dir=gates_dir,
            thread_env=policy.thread_env,
            created=created,
            note=lambda step, detail: print(f"[up] {step}: {detail}"),
            network=network,
            critic_network=own_critic_network,
            volume=volume,
            state=state,
            container=impl,
        )
        proxy_ip = runtime.container_ip(proxy.PROXY_NAME)
        if proxy_ip is None:
            raise runtime.CellRuntimeError("the proxy has no address")
        critic_proxy_ip = (
            proxy_ip if shared else session.proxy_address(runtime.SUBNETS["critic"])
        )
        impl_ip = _py(impl, OWN_IP, proxy_ip)
        print(f"implementer {impl_ip}, proxy {proxy_ip}")
        _listen(impl)
        print("control impl->own ip:", _py(impl, CONNECT, impl_ip, str(PORT)))

        with session.critic_cell(
            spec=spec,
            repo=repo,
            mirror=mirror,
            network=critic_network,
            env=session.cell_env(critic_proxy_ip, policy.thread_env),
            gates_dir=gates_dir,
            patch=patch,
            created=created,
            note=lambda *a: print("[critic]", a),
        ) as critic:
            critic_ip = _py(critic, OWN_IP, critic_proxy_ip)
            print(f"critic {critic_ip}")
            print("critic listeners:", _py(critic, LISTENERS) or "none")
            port = str(proxy.PROXY_PORT)
            print("control critic->proxy:", _py(critic, CONNECT, critic_proxy_ip, port))
            print("probe critic->impl:", _py(critic, CONNECT, impl_ip, str(PORT)))
            _listen(critic)
            print("control critic->own ip:", _py(critic, CONNECT, critic_ip, str(PORT)))
            print("probe impl->critic:", _py(impl, CONNECT, critic_ip, str(PORT)))
    finally:
        session.cell_down(
            created=created,
            note=lambda step, ok, detail: print(f"[down] {step} {ok} {detail}"),
            network=network,
            critic_network=own_critic_network,
            volume=volume,
            state=state,
            container=impl,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
