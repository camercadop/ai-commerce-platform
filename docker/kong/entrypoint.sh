#!/bin/sh
set -e

apt-get update -qq && apt-get install -y -qq gettext-base > /dev/null 2>&1

# envsubst cannot handle multiline values (e.g. PEM keys) — substitute
# AUTH_JWT_PUBLIC_KEY separately via awk, then envsubst the rest.
INDENT="        "
FORMATTED_KEY=$(echo "$AUTH_JWT_PUBLIC_KEY" | awk -v indent="$INDENT" 'NR==1{print $0} NR>1{print indent $0}')
export FORMATTED_KEY
awk '{gsub(/\$\{AUTH_JWT_PUBLIC_KEY\}/, ENVIRON["FORMATTED_KEY"]); print}' /kong/kong.yml \
  | envsubst > /tmp/kong.rendered.yml

export KONG_DATABASE=off
export KONG_DECLARATIVE_CONFIG=/tmp/kong.rendered.yml
exec /docker-entrypoint.sh kong docker-start
