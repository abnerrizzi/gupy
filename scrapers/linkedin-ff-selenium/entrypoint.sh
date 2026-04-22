#!/bin/sh
chown -R appuser:appuser /app/out /app/logs
exec gosu appuser "$@"
