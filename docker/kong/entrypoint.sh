#!/bin/sh
set -e

apt-get update -qq && apt-get install -y -qq gettext-base > /dev/null 2>&1
envsubst < /kong/kong.yml > /tmp/kong.rendered.yml
export KONG_DATABASE=off
export KONG_DECLARATIVE_CONFIG=/tmp/kong.rendered.yml
exec /docker-entrypoint.sh kong docker-start
