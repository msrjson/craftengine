# Extension fixtures

Extensions used by `tests/test_extensions_*.py` to prove the extension model
(ADR 0004) end to end. They are test fixtures, never shipped with an
application:

| Slug | Kind | Proves |
|---|---|---|
| `catalog` | module | routes, a namespaced view, assets, migrations, a catalog, a proxy exposure |
| `ordering` | module | a dependency on `catalog`, reached only through the internal proxy |
| `member_pricing` | plugin | a filter on another module's value, without importing it |
| `sunrise` | theme | a view override of `catalog::products.show` |
| `flaky` | module | a failing route and listener that trip only their own circuit breaker |
| `broken` | module | a provider raising at load: marked failed, the rest keeps serving |
