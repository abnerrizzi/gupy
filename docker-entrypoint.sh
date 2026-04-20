#!/bin/sh
set -e

# Use provided PUID/PGID or default to 1000
PUID=${PUID:-1000}
PGID=${PGID:-1000}

# Create a group and user if they don't exist with the desired IDs
if ! getent group "$PGID" >/dev/null; then
    addgroup -g "$PGID" appgroup
fi

if ! getent passwd "$PUID" >/dev/null; then
    adduser -u "$PUID" -G "$(getent group "$PGID" | cut -d: -f1)" -D appuser
fi

# Get the actual username for su-exec
APP_USER=$(getent passwd "$PUID" | cut -d: -f1)

# Ensure the output directory exists and is owned by the target user
mkdir -p /app/out
chown -R "$PUID:$PGID" /app/out

# Switch to the user and execute the command
exec su-exec "$APP_USER" "$@"
