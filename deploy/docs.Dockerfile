# version: 1.1.0 | build: 2026-09-18 | update: 2026-09-18
# Builds the documentation served at craftengine.org/docs. DigitalOcean App Platform
# runs this image only to produce files: it copies `/site` (output_dir in
# deploy/do-app.yaml) and serves it as a static site. No database, no server
# runtime. Build context is the repository root.
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build
COPY data/ ./

# docs:check fails the build on a broken link instead of publishing it.
RUN pip install . \
    && python dev.py docs:check \
    && python dev.py docs:build --output /site --base-url https://craftengine.org/docs/
