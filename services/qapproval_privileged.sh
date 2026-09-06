#!/usr/bin/env bash
set -euo pipefail

# Fixed PolicyKit entry point.  qapproval_bridge validates the command and
# matches both identifiers against the one currently pending runtime action;
# this helper never accepts an arbitrary executable or argument vector.
exec /usr/bin/python3 /usr/lib/quantic/services/qapproval_bridge.py "$@"
