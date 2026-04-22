#!/bin/sh
set -e

export API_URL=${API_URL:-http://api:5000}

envsubst '${API_URL}' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf

exec nginx -g "daemon off;"