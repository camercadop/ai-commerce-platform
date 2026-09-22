#!/bin/bash
set -e

for domain_path in /app/*/; do
    domain=$(basename "$domain_path")
    conf="${domain_path}migrations/db.conf"
    if [ -f "$conf" ]; then
        db_name=$(grep '^DB_NAME=' "$conf" | cut -d'=' -f2)
    else
        db_name="commerce_${domain}"
    fi
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
        -c "CREATE DATABASE ${db_name};"
done
