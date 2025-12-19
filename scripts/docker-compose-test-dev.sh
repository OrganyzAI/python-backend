#!/usr/bin/env zsh
# Wrapper to run `docker compose` using docker-compose.override.test-dev.yml
# This avoids modifying the original compose files. Usage:
#   ./scripts/docker-compose-test-dev.sh up -d
#   ./scripts/docker-compose-test-dev.sh ps

# Compose will read files in the order they are listed. We set COMPOSE_FILE
# so `docker compose` uses `docker-compose.yml` together with
# `docker-compose.override.test-dev.yml` instead of the default override file.
export COMPOSE_FILE="docker-compose.yml:docker-compose.override.test-dev.yml"

# Forward all args to docker compose. If no args provided, show help.
if [ "$#" -eq 0 ]; then
  docker compose help
else
  docker compose "$@"
fi
