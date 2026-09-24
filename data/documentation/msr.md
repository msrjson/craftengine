# MSR JSON manifest

Every Craft application describes itself to software registries and AI agents
with an [MSR JSON](https://msrjson.org) manifest, served natively at:

```text
https://<your-domain>/.well-known/msr.json
```

MSR JSON is an open, vendor-neutral metadata protocol for software, APIs, AI
agents and MCP servers. Registries such as mysoftrank.com, package managers and
AI discovery engines read that file instead of scraping a product page, so
publishing it *is* the listing. There is nothing to install and no route to
write: the framework mounts the endpoint for you.

## What the framework does

| Concern | Behavior |
|---|---|
| Route | `GET`/`HEAD /.well-known/msr.json`, mounted outside the middleware stack like the health probes |
| Headers | `application/json`, `Access-Control-Allow-Origin: *`, `Cache-Control: public, max-age=300` |
| Protocol block | Constant MSR JSON 2.0 block; `canonical_url` derived from your domain |
| Release | `[project].version` from `pyproject.toml`, date from its heading in `CHANGELOG.md` |
| Descriptions | Translation keys `msr.entity.tagline`, `msr.entity.summary`, `msr.entity.text`, one entry per locale |
| Unknown values | Omitted, never guessed |
| Incomplete manifest | `404` and a `msr_manifest_incomplete` log line naming the field |

A manifest is a trust artifact: registries act on it without a human checking.
That is why a required field that cannot be resolved turns the endpoint off
instead of publishing a placeholder. The most common case is development: a
`localhost` URL is not a public domain, so the endpoint answers `404` until
`MSR_DOMAIN` (or `APP_URL`) names one.

## Configuring it

Everything lives in `config/msr.py`, driven by environment variables. Fill in
what only you know; leave the rest empty.

```ini
MSR_DOMAIN=shop.example.com
MSR_TYPE=saas
MSR_DEPLOYMENT=cloud
MSR_LICENSE_TYPE=proprietary
MSR_LICENSE_TERMS=subscription
MSR_VENDOR_NAME="Example Ltd"
MSR_VENDOR_COUNTRY=BR
MSR_SUPPORT_URL=https://shop.example.com/support
MSR_PRICING_MODEL=subscription
MSR_INTEGRATIONS=stripe,postgresql
```

The accepted values of `MSR_TYPE`, `MSR_DEPLOYMENT`, `MSR_LICENSE_TERMS` and
`MSR_PRICING_MODEL` are enums of the schema. `commercial_terms` and the pricing
model are different enums: `usage` is valid only as a pricing model.
`MSR_VENDOR_COUNTRY` is ISO 3166-1 alpha-2 in upper case, where the vendor is
based.

The release is read from the project by default. Override it with
`MSR_VERSION`, `MSR_PUBLISHED_AT` (RFC 3339 with a timezone,
`2026-09-16T00:00:00Z`), `MSR_RELEASE_TYPE` and `MSR_CHANGELOG_URL`.

## Descriptions are translations

The descriptions are user-facing copy, so they live in the translation store
like every other string, in every locale listed in `LOCALES`. A locale without
a `msr.entity.summary` is left out of the manifest. The skeleton ships generic
copy in `en`, `pt-BR` and `es`; replace it with your product's own through the
translation admin or a migration.

## Checking it

```bash
python dev.py msr:show       # print the manifest the endpoint serves
python dev.py msr:validate   # validate it against the canonical schema
```

`msr:validate` fetches `https://msrjson.org/schemas/msr-2.0.json` on every run
and validates with `jsonschema` (`pip install craft[msr]`, included in the
`dev` extra). The schema is never copied into the project: a hand-kept copy
drifts from the published one while claiming the same version.

## Writing it by hand

A file at `public/.well-known/msr.json` wins over the generated manifest and is
served verbatim, with the same headers. Use it only when the configuration
cannot express what you need, and validate it with the command from the
[specification's agent guide](https://github.com/msrjson/specification).

## Turning it on

The manifest is **off until you ask for it**:

```ini
MSR_ENABLED=true
```

Off by default because it states the exact version and release date of this
installation, which is the most useful single input for matching a published
vulnerability to a running instance. Publishing it is a decision about the
product, not a route an application should acquire by existing. Once on, it is
listed by `python dev.py route list`, and an application route on
`/.well-known/msr.json` takes precedence over the built-in one.
