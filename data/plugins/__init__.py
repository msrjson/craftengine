"""Official Craft Engine plugins.

Each subdirectory is a plugin the framework ships: a `plugin.py` exposing a
`PLUGIN` descriptor and a `register(app)` hook, discovered by
`engine.plugins.manager.PluginManager` (`plugins/<slug>/plugin.py`). They are
capability plugins — pure logic an application binds through the container — not
extension-model modules.
"""
