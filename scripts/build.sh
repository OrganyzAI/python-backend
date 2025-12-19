#! /usr/bin/env sh

# Exit in case of error
set -e

build
build
TAG=${TAG?Variable not set} \
docker-compose \
-f docker-compose.test-dev.yml \
-f docker-compose.override.test-dev.yml \
build
