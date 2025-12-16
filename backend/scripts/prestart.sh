#! /usr/bin/env bash

set -e
set -x

# 1) Run migrations first so all tables exist
alembic upgrade head

# 2) Let the DB start and ensure initial data like the admin user
python app/backend_pre_start.py

# 3) Optionally run extra initial data script
# Only run initial data script if it exists and SKIP_INITIAL_DATA is not set to "true".
if [ -f "app/initial_data.py" ] && [ "${SKIP_INITIAL_DATA:-false}" != "true" ]; then
  python app/initial_data.py
else
  echo "Skipping initial data (file missing or SKIP_INITIAL_DATA=true)"
fi
