#!/bin/sh
# Pre-release gate: rehearse the CRM demo against the release candidate in data/.
#
# The demo consumes only published tags, so a framework defect would otherwise
# surface after the release. This builds the candidate from data/ (read-only),
# copies the demo (read-only) into a throwaway container, scaffolds login and
# admin, installs every extension and runs the demo's whole suite, walkthrough
# included - once on SQLite and once on a disposable PostgreSQL 18 server held
# in memory (tmpfs). Nothing is written to data/ or data-demo/, and both
# throwaway containers and their network are removed at the end.
#
#   sh .claude/scripts/rehearse-demo.sh     # exits non-zero when anything fails
set -eu
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
NET=crm-rehearsal-net
cleanup() { docker rm -f crm-rehearsal crm-rehearsal-db >/dev/null 2>&1 || true; docker network rm "$NET" >/dev/null 2>&1 || true; }
trap cleanup EXIT
cleanup
docker network create "$NET" >/dev/null
docker run -d --name crm-rehearsal-db --network "$NET" --tmpfs /var/lib/postgresql \
  -e POSTGRES_USER=rehearsal -e POSTGRES_PASSWORD=rehearsal -e POSTGRES_DB=rehearsal postgres:18-alpine >/dev/null
docker run --rm --name crm-rehearsal --network "$NET" \
  -v "$ROOT/data:/src:ro" -v "$ROOT/data-demo:/demo:ro" \
  python:3.14-slim sh -c '
    set -e
    cp -r /src /tmp/engine && pip install -q --root-user-action=ignore "/tmp/engine[dev]" >/tmp/pip.log 2>&1
    python -c "import engine; print(\"ENGINE\", engine.__version__, engine.__release__)"
    cp -r /demo /tmp/crm && cd /tmp/crm && rm -rf .env .git && cp .env.example .env
    export APP_URL=http://testserver
    python dev.py key:generate >/dev/null
    python dev.py make auth >/dev/null
    python dev.py make admin >/dev/null
    echo "== SQLite"
    python -m pytest tests -q -p no:cacheprovider -rs
    echo "== PostgreSQL"
    for i in $(seq 1 30); do python -c "import psycopg2; psycopg2.connect(host=\"crm-rehearsal-db\", user=\"rehearsal\", password=\"rehearsal\", dbname=\"rehearsal\")" 2>/dev/null && break; sleep 1; done
    CRM_TEST_DB=pgsql DB_CONNECTION=pgsql DB_HOST=crm-rehearsal-db DB_PORT=5432 DB_DATABASE=rehearsal \
      DB_USERNAME=rehearsal DB_PASSWORD=rehearsal DB_SSLMODE=disable \
      python -m pytest tests -q -p no:cacheprovider -rs
  '
