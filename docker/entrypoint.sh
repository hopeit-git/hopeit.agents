#!/bin/sh
set -e

if [ -n "$VIRTUAL_ENV" ] && [ -d "$VIRTUAL_ENV" ]; then
  # shellcheck disable=SC1090
  . "$VIRTUAL_ENV/bin/activate"
fi

exec hopeit_mcp_server "$@"
