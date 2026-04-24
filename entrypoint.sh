#!/bin/sh
# Run as root long enough to normalise ownership on the bind-mounted
# volume (the host directory may have been created by another container or
# by a different host user), then drop to appuser (uid 1000) for the real
# workload. Keeps the scraper, API, and sidecar all writing as the same uid
# so files one creates are writable by the others.
set -e

mkdir -p /app/out
chown -R appuser:appuser /app/out

exec su-exec appuser "$@"
