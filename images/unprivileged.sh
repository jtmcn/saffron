#!/bin/bash
# Drops one command to the unprivileged account: closes every descriptor
# above 2, then execs setpriv with no capability kept (DESIGN.md §5.5).
{
  [ "$#" -eq 1 ] || exit 64
  for fd in /proc/$$/fd/*; do
    n=${fd##*/}
    case $n in
      0 | 1 | 2) continue ;;
    esac
    eval "exec $n>&-" 2>/dev/null
  done
  exec /usr/bin/setpriv --reuid=unprivileged --regid=unprivileged \
    --clear-groups --no-new-privs --inh-caps=-all \
    /usr/bin/env -u CLAUDE_CODE_OAUTH_TOKEN HOME=/home/unprivileged \
    /bin/bash -c "$1" < /dev/null
}
