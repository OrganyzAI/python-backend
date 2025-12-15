#! /usr/bin/env bash

set -e
set -x

# Let the DB start
python app/backend_pre_start.py

# Run migrations
alembic upgrade head

# Create initial data in DB
# Only run initial data script if it exists and SKIP_INITIAL_DATA is not set to "true".
if [ -f "app/initial_data.py" ] && [ "${SKIP_INITIAL_DATA:-false}" != "true" ]; then
	python app/initial_data.py
else
	echo "Skipping initial data (file missing or SKIP_INITIAL_DATA=true)"
fi
