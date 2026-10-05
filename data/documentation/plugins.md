# Plugins

A plugin is an extension of kind `plugin`: a cross-cutting capability - an
audit trail, pricing rules, a payment gateway - that other extensions use
through events, filters and the internal proxy, and that can be removed
without breaking them. Everything about creating, installing, activating and
isolating one is in [extensions.md](extensions.md):

```bash
python dev.py make plugin member_pricing
python dev.py extension install member_pricing
python dev.py extension activate member_pricing
```

```python
# app/plugins/member_pricing/provider.py
def register(context):
    context.filter("catalog.price_cents", lambda price_cents, sku: price_cents * 9 // 10)
```

## Legacy plugins (deprecated)

Before the extension model, a plugin was a directory `plugins/<slug>/` with a
`plugin.py` exposing a `PLUGIN` dict (`slug`, `name`, `version`,
`description`) and `register(app)`, managed with `dev.py plugin
list|enable|disable|sync`. That loader still runs for one release so existing
projects keep working, with its limits:

- a disabled legacy plugin keeps its hooks until the process restarts;
- it has no manifest, version range, dependencies, migrations, views or
  translations;
- its hooks are isolated only when triggered through `trigger_hook`.

Move a legacy plugin by adding an `extension.toml` (`kind = "plugin"`) under
`app/plugins/<slug>/`, renaming `register(app)` to `register(context)` and
replacing `app.make("plugin").add_hook(name, callback)` with
`context.listen(name, callback)`.
