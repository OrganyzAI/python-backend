#! /usr/bin/env bash

set -e
set -x

# Generate the OpenAPI spec JSON for the backend.
# Previously this script generated a frontend client; frontend has been removed.
cd backend
python -c "import app.main; import json; print(json.dumps(app.main.app.openapi()))" > ../openapi.json

echo "Generated openapi.json at project root."
