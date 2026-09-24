#!/bin/sh
set -e

apt-get update -qq && apt-get install -y -qq gettext-base > /dev/null 2>&1

# AUTH_JWT_PUBLIC_KEY is a multiline PEM — envsubst can't handle it.
# Replace the placeholder with a YAML block scalar using awk, then envsubst the rest.
INDENT="          "
FORMATTED_KEY=$(echo "$AUTH_JWT_PUBLIC_KEY" | awk -v indent="$INDENT" '{print indent $0}')
export FORMATTED_KEY
awk '{gsub(/rsa_public_key: \$\{AUTH_JWT_PUBLIC_KEY\}/, "rsa_public_key: |\n" ENVIRON["FORMATTED_KEY"]); print}' /kong/kong.yml \
  | envsubst > /tmp/kong.rendered.yml

export KONG_DATABASE=off
export KONG_DECLARATIVE_CONFIG=/tmp/kong.rendered.yml
exec /docker-entrypoint.sh kong docker-start
