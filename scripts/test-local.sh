#! /usr/bin/env bash

# Exit in case of error
set -e

docker-compose -f docker-compose.test-dev.yml -f docker-compose.override.test-dev.yml down -v --remove-orphans # Remove possibly previous broken stacks left hanging after an error

if [ $(uname -s) = "Linux" ]; then
    echo "Remove __pycache__ files"
    sudo find . -type d -name __pycache__ -exec rm -r {} \+
fi

docker-compose -f docker-compose.test-dev.yml -f docker-compose.override.test-dev.yml build
docker-compose -f docker-compose.test-dev.yml -f docker-compose.override.test-dev.yml up -d
docker-compose -f docker-compose.test-dev.yml -f docker-compose.override.test-dev.yml exec -T backend bash scripts/tests-start.sh "$@"
