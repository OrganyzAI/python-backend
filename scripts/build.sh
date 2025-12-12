#! /usr/bin/env sh

# Exit in case of error
set -e

build
TAG=${TAG?Variable not set} \
FRONTEND_ENV=${FRONTEND_ENV-production} \
docker-compose \
-f docker-compose.test-dev.yml \
-f docker-compose.override.test-dev.yml \
build
