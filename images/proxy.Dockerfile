# The egress proxy — a sibling on both networks, doing hostname CONNECT
# filtering. Not iptables: --cap-drop ALL removes CAP_NET_ADMIN, and granting
# it would let the untrusted cell rewrite its own firewall (DESIGN.md §5.1).
FROM alpine:3

RUN apk add --no-cache squid
COPY images/squid.conf /etc/squid/squid.conf

EXPOSE 3128
CMD ["squid", "-N", "-f", "/etc/squid/squid.conf"]
