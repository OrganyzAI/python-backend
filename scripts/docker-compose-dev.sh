#!/usr/bin/env zsh
# Wrapper to run `docker compose` using the generated `dockercompose-dev.yml` file
# Usage:
#   ./scripts/docker-compose-dev.sh up -d
#   ./scripts/docker-compose-dev.sh ps

export COMPOSE_FILE="dockercompose-dev.yml"

if [ "$#" -eq 0 ]; then
  docker compose help
else
  docker compose "$@"
fi
