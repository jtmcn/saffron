#!/usr/bin/env sh
# Build a base image for a host that cannot reach a container registry.
#
# `images/cell-base.python.Dockerfile` is `FROM python:3.12-slim-bookworm` and
# that is the base this project is built and measured against. A host whose
# egress policy refuses every registry cannot pull it — measured on a Claude
# Code cloud runner, where docker.io, quay.io, public.ecr.aws and ghcr.io are
# all 403 at the blob CDN (docs/evidence/2026-09-11-podman-as-a-second-cell-runtime.md).
# Nothing in the base needs a registry: an apt mirror and pypi supply all of it.
#
#   ./images/bootstrap-base.sh [tag] [suite] [mirror]
#
# Then build the cell base against it:
#   <runtime> build --build-arg BASE_IMAGE=<tag> -t saffron/cell-base:python \
#     -f images/cell-base.python.Dockerfile .
#
# **This does not produce the same image the default does**, and DESIGN.md §5.1.2
# says what that costs. It is a different distribution, resolved at the moment it
# runs. The image records what it actually contains so two hosts can be compared
# rather than assumed equal; that record is the thing to read before trusting a
# gate result from one host against a gate result from another.
set -eu

TAG=${1:-saffron/bootstrap-base:local}
SUITE=${2:-noble}
MIRROR=${3:-http://archive.ubuntu.com/ubuntu/}
RUNTIME=${SAFFRON_CELL_RUNTIME_BIN:-podman}

command -v debootstrap >/dev/null || {
	echo "debootstrap is not installed (apt-get install debootstrap)" >&2
	exit 2
}
command -v "$RUNTIME" >/dev/null || {
	echo "$RUNTIME is not on PATH; set SAFFRON_CELL_RUNTIME_BIN" >&2
	exit 2
}

root=$(mktemp -d)
trap 'rm -rf "$root"' EXIT

# --force-check-gpg: with no archive keyring debootstrap only warns and installs
# unverified, and this base ends up holding the agent's token.
echo "debootstrap $SUITE -> $root/rootfs"
debootstrap --force-check-gpg --variant=minbase --include=ca-certificates \
	"$SUITE" "$root/rootfs" "$MIRROR" >/dev/null
# --variant=minbase leaves `universe` disabled, and python3-pip lives there.
# Without it `apt-get install` aborts the whole transaction on one missing
# candidate and the other packages silently do not arrive either. Measured.
# -updates and -security too, or every image built on this ships release day's.
printf 'deb %s %s main universe\n' "$MIRROR" "$SUITE" "$MIRROR" "$SUITE-updates" \
	"$MIRROR" "$SUITE-security" >"$root/rootfs/etc/apt/sources.list"

tar -C "$root/rootfs" -cf "$root/rootfs.tar" .
"$RUNTIME" import -q "$root/rootfs.tar" "$TAG" >/dev/null

# Run it, do not merely build it: an import that produced an unusable rootfs
# reads identically to a working one until the first cell fails (principle 39).
"$RUNTIME" run --rm "$TAG" /bin/sh -c 'exit 0' ||
	{ echo "the imported base does not run" >&2; exit 1; }

echo "built $TAG — pass it as --build-arg BASE_IMAGE=$TAG"
