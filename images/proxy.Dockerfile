# The egress proxy — a sibling on both networks, doing hostname CONNECT
# filtering. Not iptables: --cap-drop ALL removes CAP_NET_ADMIN, and granting
# it would let the untrusted cell rewrite its own firewall (DESIGN.md §5.1).
#
# `BASE_IMAGE` is an argument for the reason `cell-base.python.Dockerfile` gives:
# a host whose egress refuses every registry cannot pull the default and can
# still build every layer below it (DESIGN.md §5.1.2). The default is unchanged.
ARG BASE_IMAGE=alpine:3
FROM ${BASE_IMAGE}

# Either package manager, because the base is an argument now. Asserted by
# running squid, never by finding it: a present-and-unrunnable binary reads
# identically to a working one (principle 39), and this one is only ever
# executed by a container nobody is watching.
RUN set -eu; \
    if command -v apk >/dev/null; then apk add --no-cache squid; \
    elif command -v apt-get >/dev/null; then \
      apt-get update && apt-get install -y --no-install-recommends squid \
      && rm -rf /var/lib/apt/lists/*; \
    else echo "no apk or apt-get in ${BASE_IMAGE}" >&2; exit 1; fi; \
    squid --version | grep -qi squid \
      || { echo "squid reported no version" >&2; exit 1; }

# The host starts this container as `squid:squid` and never as root, because
# dropping privilege needs SETUID/SETGID and `--cap-drop ALL` removes them
# (§5.1). Alpine's package creates that user; Debian's creates `proxy` instead —
# measured — so the image supplies the name the host names rather than core
# learning which distribution built its own proxy image.
RUN set -eu; \
    if ! getent group squid >/dev/null; then \
      addgroup --system squid 2>/dev/null || addgroup -S squid; fi; \
    if ! getent passwd squid >/dev/null; then \
      adduser --system --no-create-home --ingroup squid squid 2>/dev/null \
        || adduser -S -H -G squid squid; fi; \
    mkdir -p /var/cache/squid /var/log/squid; \
    chown -R squid:squid /var/cache/squid /var/log/squid

COPY images/squid.conf /etc/squid/squid.conf

# What this image is, recorded by running the tool rather than restating the
# build argument — the same reason the cell base carries one.
RUN set -eu; \
    { echo "base=$(. /etc/os-release && echo "$ID ${VERSION_ID:-}")"; \
      echo "squid=$(squid --version 2>&1 | head -1)"; \
    } > /etc/squid/provenance

EXPOSE 3128
CMD ["squid", "-N", "-f", "/etc/squid/squid.conf"]
