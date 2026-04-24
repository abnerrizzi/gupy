#!/bin/sh
# See ../entrypoint.sh — same chown-then-drop pattern. Kept local to api/
# because the api build context is the repo root, but the COPY paths make
# it simpler to ship a dedicated copy.
set -e

mkdir -p /app/out
chown -R appuser:appuser /app/out

exec su-exec appuser "$@"
