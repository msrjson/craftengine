#!/bin/sh
# Production entrypoint: synchronize the release, then hand off to the server.
#
# `release:sync` applies the pending migrations and runs the release seeders
# under an advisory lock, and records the release in `release_syncs`. It is
# idempotent, so running it on every boot is safe - and it means a deploy that
# replaces several containers cannot leave the schema half-built, or a screen
# empty for want of a seeder nobody remembered to run.
#
# It refuses to run when the `VERSION` file disagrees with the running code, so
# a stale image fails loudly here instead of migrating a node from code nobody
# can name. That refusal is the point: the container stops and the orchestrator
# keeps the previous one serving.
set -e

if [ "${RELEASE_SYNC_ON_BOOT:-true}" = "true" ]; then
    python dev.py release:sync
else
    echo "release:sync skipped (RELEASE_SYNC_ON_BOOT=${RELEASE_SYNC_ON_BOOT})"
fi

exec "$@"
