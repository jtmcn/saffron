#!/usr/bin/env sh
# Build a base image from an apt mirror alone, for a host whose egress refuses
# every registry (docs/evidence/2026-09-11-podman-as-a-second-cell-runtime.md).
#
#   ./images/bootstrap-base.sh [tag] [suite] [mirror] [runtime-binary]
#
# Then build the cell base against it:
#   <runtime> build --build-arg BASE_IMAGE=<tag> -t saffron/cell-base:python \
#     -f images/cell-base.python.Dockerfile .
#
# Not the image the default builds: a different distribution, resolved today.
# Compare provenance files before comparing gate results (DESIGN.md §5.1.2).
set -eu

TAG=${1:-saffron/bootstrap-base:local}
SUITE=${2:-noble}
MIRROR=${3:-http://archive.ubuntu.com/ubuntu/}
RUNTIME=${4:-podman}

command -v debootstrap >/dev/null || {
	echo "debootstrap is not installed (apt-get install debootstrap)" >&2
	exit 2
}
command -v "$RUNTIME" >/dev/null || {
	echo "$RUNTIME is not on PATH; name the runtime binary as the fourth argument" >&2
	exit 2
}

root=$(mktemp -d)
trap 'rm -rf "$root"' EXIT

# --force-check-gpg: with no archive keyring debootstrap only warns and installs
# unverified, and this base ends up holding the agent's token.
echo "debootstrap $SUITE -> $root/rootfs"
debootstrap --force-check-gpg --variant=minbase --include=ca-certificates \
	"$SUITE" "$root/rootfs" "$MIRROR" >/dev/null
# minbase leaves `universe` (python3-pip) off, and one missing candidate aborts the
# whole install — measured. -updates and -security, or it ships release day's.
printf 'deb %s %s main universe\n' "$MIRROR" "$SUITE" "$MIRROR" "$SUITE-updates" \
	"$MIRROR" "$SUITE-security" >"$root/rootfs/etc/apt/sources.list"

tar -C "$root/rootfs" -cf "$root/rootfs.tar" .
"$RUNTIME" import -q "$root/rootfs.tar" "$TAG" >/dev/null

# Run it, do not merely build it: an import that produced an unusable rootfs
# reads identically to a working one until the first cell fails (principle 39).
"$RUNTIME" run --rm "$TAG" /bin/sh -c 'exit 0' ||
	{ echo "the imported base does not run" >&2; exit 1; }

echo "built $TAG — pass it as --build-arg BASE_IMAGE=$TAG"
