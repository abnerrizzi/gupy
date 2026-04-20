#!/bin/sh
set -e

# Provide a default if API_URL is not set
export API_URL=${API_URL:-http://api:5000}

# Replace environment variables in the template
envsubst '${API_URL}' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf

exec nginx -g "daemon off;"