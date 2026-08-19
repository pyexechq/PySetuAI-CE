#!/bin/sh
# Resolve the endpoint-agent package regardless of the caller's working directory,
# select a Python 3.11+ interpreter, then run the daemon. Used by launchd/systemd.
DIR="$(cd "$(dirname "$0")" && pwd)"
export PYTHONPATH="$DIR${PYTHONPATH:+:$PYTHONPATH}"

PYTHON=""
for candidate in /usr/local/bin/python3 /opt/homebrew/bin/python3 /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 python3; do
  if command -v "$candidate" >/dev/null 2>&1; then
    if "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
      PYTHON="$candidate"
      break
    fi
  fi
done

if [ -z "$PYTHON" ]; then
  echo "No Python 3.11+ interpreter found" >&2
  exit 1
fi

exec "$PYTHON" -m pysetu_agent "$@"
