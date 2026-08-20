#!/usr/bin/env bash
# The cell-runtime spike — DESIGN.md Appendix G, "The decision, and when it gets made".
#
# Four assertions against a real cell on an internal network. All four hold under
# apple/container, take it; otherwise fall back to a shared VM (Docker Desktop
# first). Half an hour, and it settles a question eight revisions left open.
#
#   ./spikes/cell-runtime.sh [container|docker|auto]
#
# Three outcomes per assertion, not two, for the reason §5.4 gives: a probe that
# never ran is `error`, never `pass`. The first version of this file reported two
# vacuous passes against a runtime with no kernel configured — principle 34,
# committed inside the spike written to test it.
#
# Delete this file once v0.5 has recorded the answer in saffron/cell/runtime.py.

set -uo pipefail

RUNTIME=${1:-auto}
IMAGE=${IMAGE:-alpine:3}
NET=saffron-spike
SUBNET=10.88.0.0/24
GATEWAY=10.88.0.1
CPUS=2
MEM=1g
PROXY=saffron-spike-proxy
PROXY_PORT=3128
LOOPBACK_PORT=5433 # host listener on 127.0.0.1 — must NOT be reachable (N1)
WILDCARD_PORT=5434 # host listener on 0.0.0.0  — reachability is the hazard

pass=0
fail=0
errored=0
ok() {
	printf '  \033[32mPASS\033[0m   %s\n' "$1"
	pass=$((pass + 1))
}
no() {
	printf '  \033[31mFAIL\033[0m   %s\n' "$1"
	fail=$((fail + 1))
}
er() {
	printf '  \033[33mERROR\033[0m  %s\n' "$1"
	errored=$((errored + 1))
}
note() { printf '         %s\n' "$1"; }
head2() { printf '\n\033[1m%s\033[0m\n' "$1"; }
run() {
	printf '\033[2m  $ %s\033[0m\n' "$*" >&2
	"$@"
}

# ---------------------------------------------------------------- runtime seam
# The whole of saffron/cell/runtime.py, in shell: create a network, run a
# container on it with CPU and memory limits, inspect it, destroy it.

detect() {
	for r in container docker; do command -v "$r" >/dev/null 2>&1 && {
		echo "$r"
		return
	}; done
	echo none
}

net_create() {
	case $RUNTIME in
	docker) run docker network create --internal --subnet "$SUBNET" "$NET" >/dev/null ;;
	container) run container network create --internal --subnet "$SUBNET" "$NET" >/dev/null ;;
	esac
}

# A stand-in for the egress proxy. busybox nc serves one connection and exits, so
# it runs in a loop.
# ponytail: a listener, not a proxy — assertion 3 is about reachability and DNS,
# not about CONNECT filtering. A real squid arrives with v0.5's proxy image.
proxy_start() {
	local listen="while true; do nc -l -p $PROXY_PORT >/dev/null 2>&1; done"
	case $RUNTIME in
	docker) run docker run -d --name "$PROXY" --network "$NET" "$IMAGE" sh -c "$listen" >/dev/null ;;
	container) run container run -d --name "$PROXY" --network "$NET" "$IMAGE" sh -c "$listen" >/dev/null ;;
	esac
}

# ponytail: grep an address out of whatever `inspect` prints, rather than learn
# two JSON shapes. Crude, runtime-agnostic, and it only has to survive this file.
proxy_ip() {
	$RUNTIME inspect "$PROXY" 2>/dev/null |
		grep -oE '10\.88\.0\.[0-9]+' | grep -v "^${GATEWAY}$" | head -1
}

cell() {
	case $RUNTIME in
	docker) docker run --rm --network "$NET" \
		--cpuset-cpus "0-$((CPUS - 1))" --memory "$MEM" \
		--security-opt no-new-privileges --cap-drop ALL \
		"$IMAGE" "$@" 2>/dev/null ;;
	container) container run --rm --network "$NET" \
		--cpus "$CPUS" --memory "$MEM" --cap-drop ALL \
		"$IMAGE" "$@" 2>/dev/null ;;
	esac
}

# Run a probe inside a cell and report the probe's own exit code — or `noran`,
# which is the whole point. A cell that never started makes every negative
# assertion below succeed for the wrong reason.
probe() {
	local out rc
	out=$(cell sh -c "$1"'; echo "__rc=$?"')
	rc=$(printf '%s' "$out" | sed -n 's/.*__rc=\([0-9][0-9]*\).*/\1/p' | tail -1)
	printf '%s' "${rc:-noran}"
}

cleanup() {
	$RUNTIME rm -f "$PROXY" >/dev/null 2>&1
	$RUNTIME network rm "$NET" >/dev/null 2>&1
	[ -n "${LOOPBACK_PID:-}" ] && kill "$LOOPBACK_PID" 2>/dev/null
	[ -n "${WILDCARD_PID:-}" ] && kill "$WILDCARD_PID" 2>/dev/null
	return 0
}

# ------------------------------------------------------------------- the spike

[ "$RUNTIME" = auto ] && RUNTIME=$(detect)

if [ "$RUNTIME" = none ]; then
	cat <<'EOF'
No cell runtime on PATH.

  apple/container   brew install container               (Appendix G's candidate B — try first)
  Docker Desktop    brew install --cask docker-desktop   (candidate A, the fallback)

colima is installed but has no docker CLI to drive it; `brew install docker`
adds one. Colima and Docker Desktop are the same architecture (Appendix G) and
this spike cannot tell them apart — that is the useful result, not a gap.
EOF
	exit 2
fi

command -v "$RUNTIME" >/dev/null || {
	echo "$RUNTIME not on PATH"
	exit 2
}
printf '\033[1mcell-runtime spike — %s\033[0m\n' "$RUNTIME"

trap cleanup EXIT
cleanup

head2 "setup"
net_create || {
	echo "could not create an internal network; nothing below would be meaningful"
	exit 2
}

# The liveness gate. Everything below is a claim about a cell, so a cell has to
# run first — otherwise the two negative assertions pass by absence.
alive=$(cell echo alive | tr -d '[:space:]')
if [ "$alive" != "alive" ]; then
	echo "a cell will not start on $RUNTIME — no assertion below would mean anything"
	[ "$RUNTIME" = container ] &&
		echo "  if this is 'default kernel not configured': container system kernel set --recommended"
	exit 2
fi
note "a cell starts and returns output"

python3 -m http.server "$LOOPBACK_PORT" --bind 127.0.0.1 >/dev/null 2>&1 &
LOOPBACK_PID=$!
python3 -m http.server "$WILDCARD_PORT" --bind 0.0.0.0 >/dev/null 2>&1 &
WILDCARD_PID=$!
note "host listeners up: 127.0.0.1:$LOOPBACK_PORT, 0.0.0.0:$WILDCARD_PORT"
proxy_start || note "proxy stand-in did not start"
sleep 3
PROXY_IP=$(proxy_ip)
note "proxy stand-in at ${PROXY_IP:-<no address found>}"

# 1 — the cell sees only the CPUs it has. §5.1: write the requirement, not the
# flag. What must hold is that the visible count is far below the host's and
# tracks the allocation — that is what stops a thread pool oversubscribing. The
# exact offset is a per-runtime calibration, not a failure:
#   apple/container 1.2.2 gives the guest --cpus + 1 vCPUs, deterministically.
#   docker --cpuset-cpus 0-(N-1) gives exactly N.
head2 "1. the cell sees only the CPUs it has"
case $RUNTIME in
container) OFFSET=1 ;;
*) OFFSET=0 ;;
esac
HOST_CPUS=$(sysctl -n hw.ncpu 2>/dev/null || echo 0)
seen=$(cell nproc | tr -d '[:space:]')
if [ -z "$seen" ]; then
	er "nproc produced no output"
elif [ "$seen" = "$((CPUS + OFFSET))" ]; then
	ok "nproc = $seen for --cpus $CPUS (host has $HOST_CPUS)"
	[ "$OFFSET" -ne 0 ] &&
		note "calibration: this runtime allocates $OFFSET vCPU more than requested — ask for K-$OFFSET"
elif [ "$seen" -ge "$HOST_CPUS" ] 2>/dev/null; then
	no "nproc = $seen against a host of $HOST_CPUS — the cell sees the whole machine"
	note "thread pools size themselves from this; this is §5.1's flaky-gate mode"
else
	no "nproc = $seen, expected $((CPUS + OFFSET)) for --cpus $CPUS"
	note "below the host count, so not the oversubscription mode — but the offset moved; recalibrate"
fi

# 2 — egress to an unlisted host fails.
head2 "2. egress to an unlisted host fails"
rc=$(probe "wget -q -T 5 -O /dev/null https://example.com")
case $rc in
noran) er "the probe never ran — cannot distinguish blocked from absent" ;;
0)
	no "reached example.com from inside the cell"
	note "the network is not internal; N1 does not hold on this runtime as configured"
	;;
*) ok "example.com unreachable (wget exit $rc)" ;;
esac

# 3 — the proxy is reachable, by IP; and by name it is not (internal nets have no DNS).
head2 "3. the proxy is reachable, by IP"
if [ -z "$PROXY_IP" ]; then
	er "no address for the proxy stand-in — it did not start, or inspect's shape is not understood"
else
	rc=$(probe "nc -w 3 $PROXY_IP $PROXY_PORT </dev/null")
	case $rc in
	noran) er "the probe never ran" ;;
	0) ok "$PROXY_IP:$PROXY_PORT reachable" ;;
	*) no "$PROXY_IP:$PROXY_PORT unreachable (nc exit $rc)" ;;
	esac
	rc=$(probe "nc -w 3 $PROXY $PROXY_PORT </dev/null")
	case $rc in
	0) note "NOTE: the name '$PROXY' also resolved — this network HAS DNS, unlike Appendix G's claim" ;;
	noran) note "the name probe never ran" ;;
	*) note "the name '$PROXY' does not resolve, as expected — address the proxy by IP" ;;
	esac
fi

# 4 — a host service is not reachable. Two bindings, because the difference is the point.
head2 "4. host services are not reachable"
LAN_IP=$(ipconfig getifaddr en0 2>/dev/null)
for host_addr in "$GATEWAY" ${LAN_IP:+"$LAN_IP"}; do
	rc=$(probe "nc -w 3 $host_addr $LOOPBACK_PORT </dev/null")
	case $rc in
	noran) er "the 127.0.0.1-bound probe never ran at $host_addr" ;;
	0) no "reached a 127.0.0.1-bound host service at $host_addr:$LOOPBACK_PORT" ;;
	*) ok "127.0.0.1-bound host service unreachable at $host_addr" ;;
	esac
	rc=$(probe "nc -w 3 $host_addr $WILDCARD_PORT </dev/null")
	case $rc in
	0)
		note "HAZARD CONFIRMED: a 0.0.0.0-bound host service IS reachable at $host_addr:$WILDCARD_PORT"
		note "  Appendix G's preflight probe is load-bearing. Bind host services to 127.0.0.1."
		;;
	noran) note "the 0.0.0.0-bound probe never ran at $host_addr" ;;
	*) note "0.0.0.0-bound host service also unreachable at $host_addr" ;;
	esac
done

head2 "verdict"
printf '  %d passed, %d failed, %d errored\n\n' "$pass" "$fail" "$errored"
if [ "$errored" -gt 0 ]; then
	echo "  No verdict: $errored assertion(s) could not be evaluated."
	echo "  An assertion that did not run is not an assertion that passed (§5.4)."
	exit 2
fi
if [ "$fail" -eq 0 ]; then
	echo "  All assertions hold on $RUNTIME."
	[ "$RUNTIME" = container ] &&
		echo "  Appendix G: take it. Better isolation, better memory ceiling, §5.1 gets shorter."
	exit 0
fi
echo "  $RUNTIME does not satisfy the spike as configured."
[ "$RUNTIME" = container ] &&
	echo "  Appendix G: fall back to architecture A, Docker Desktop first."
exit 1
