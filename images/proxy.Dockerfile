# The egress proxy — a sibling on both networks, doing hostname CONNECT
# filtering. Not iptables: --cap-drop ALL removes CAP_NET_ADMIN, and granting
# it would let the untrusted cell rewrite its own firewall (DESIGN.md §5.1).
#
# A host with no registry passes a Debian or Ubuntu base (§5.1.2).
ARG BASE_IMAGE=alpine:3
FROM ${BASE_IMAGE}

# Either package manager, since the base is an argument. squid is run, not
# located: a present-and-unrunnable binary reads as a working one (principle 39).
RUN set -eu; \
    if command -v apk >/dev/null; then apk add --no-cache squid; \
    elif command -v apt-get >/dev/null; then \
      apt-get update && apt-get install -y --no-install-recommends squid \
      && rm -rf /var/lib/apt/lists/*; \
    else echo "no apk or apt-get in ${BASE_IMAGE}" >&2; exit 1; fi; \
    squid --version | grep -qi squid \
      || { echo "squid reported no version" >&2; exit 1; }

# The host runs this as squid:squid (--cap-drop ALL leaves nothing to drop
# privilege with), and Debian's package names that user `proxy` — measured.
RUN set -eu; \
    if ! getent group squid >/dev/null; then \
      addgroup --system squid 2>/dev/null || addgroup -S squid; fi; \
    if ! getent passwd squid >/dev/null; then \
      adduser --system --no-create-home --ingroup squid squid 2>/dev/null \
        || adduser -S -H -G squid squid; fi; \
    mkdir -p /var/cache/squid /var/log/squid; \
    chown -R squid:squid /var/cache/squid /var/log/squid

COPY images/squid.conf /etc/squid/squid.conf

# Versions the tools printed, one substitution per step as the cell base explains.
RUN set -eu; \
    base=$(. /etc/os-release && echo "$ID ${VERSION_ID:-}"); \
    sq=$(squid --version 2>&1); \
    sq=$(printf '%s\n' "$sq" | head -n 1); \
    printf 'base=%s\nsquid=%s\n' "$base" "$sq" > /etc/squid/provenance; \
    if grep -q '=$' /etc/squid/provenance; then \
      echo "a tool printed no version:" >&2; cat /etc/squid/provenance >&2; exit 1; fi

EXPOSE 3128
CMD ["squid", "-N", "-f", "/etc/squid/squid.conf"]
