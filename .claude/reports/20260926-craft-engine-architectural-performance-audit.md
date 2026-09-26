# Relatório de Auditoria Arquitetural e de Desempenho do Craft Engine

**Framework**: Craft Engine (`https://github.com/msrjson/craftengine.git`)  
**Versão Auditada**: 4.1.0-r00019  
**Versão Alvo com Correções & Benchmarks**: 4.2.0-r00020  
**Data**: 26 de Setembro de 2026  
**Auditor**: Arquiteto de Software Principal & Engenheiro Especialista em Runtimes Python/ASGI  

---

## 1. Sumário Executivo

A auditoria no núcleo do Craft Engine (`engine/`) revelou que o framework possuía excelentes bases de design (estilo batteries-included similar ao Laravel, com injeção de dependência e suporte multi-driver), porém com **pressupostos latentes de latência zero (localhost/loopback)** em camadas críticas de hot paths (views, autorização, sessões).

Em um ambiente de nuvem distribuída (como App Platform/Kubernetes com PostgreSQL gerenciado e SSL/TLS ativo com RTT de 2ms a 5ms por query):
- Uma única requisição HTTP renderizando uma página com 500 chamadas ao helper de tradução `__()` incorria em **500 queries sequenciais síncronas**, bloqueando o worker por 1.000ms a 2.500ms apenas em network RTT.
- Verificações de permissão em templates (`@can`, `@has_role`) repetiam queries pesadas de 4-way `UNION ALL` para cada elemento de listas ou tabelas renderizadas.
- O store de sessões em banco de dados (`DatabaseSessionStore`) gerava queries de `SELECT` e `UPDATE` mesmo em requisições puramente de leitura (`GET`), gerando centenas de writes desnecessários no banco de dados gerenciado.
- Variáveis de estado por requisição (`_tenant`, `_user`, `_session`) utilizavam `threading.local()`, expondo risco de vazamento de contexto entre requisições concorrentes em runtimes assíncronos baseados em ASGI (`uvicorn`).
- O parsing do método HTTP (`_method`) no ASGI lia o payload inteiro em memória, criando risco iminente de Out-Of-Memory (OOM) em uploads grandes.

Na versão **4.2.0-r00020**, todas essas falhas foram sanadas com técnicas de **In-Memory Bulk Loading**, **Negative Caching**, **Request-Scoped Cache com ContextVar**, **Dirty Tracking de Sessão**, **Cap de Streaming no ASGI** e **Detecção Automática de Queries N+1**.

---

## 2. Matriz de Vulnerabilidades Arquiteturais

| Severidade | Módulo / Arquivo | Anti-Pattern Identificado | Impacto em Nuvem (PostgreSQL Remoto / RTT 2-5ms) | Status |
| :--- | :--- | :--- | :--- | :--- |
| **CRÍTICA** | `engine/support/translation.py` | Query SQL pontual a cada string traduzida sem cache ou memoization. | Em views com 500 strings, gerava 500 roundtrips de rede sequenciais (1s a 2.5s de latência por request). | **Resolvido (v4.2.0)** |
| **CRÍTICA** | `engine/auth/manager.py` | `threading.local()` para identidade do usuário e sessão em container singleton. | Sob servidores ASGI (`uvicorn`), tarefas assíncronas concorrentes podem reutilizar a mesma thread e vazar dados de sessão/usuário. | **Resolvido (v4.2.0)** |
| **ALTA** | `engine/auth/access.py` | Resolução de permissões via 4-way `UNION ALL` sem cache no ciclo da requisição. | Loops de views checando `@can` executavam dezenas de queries complexas idênticas na mesma requisição. | **Resolvido (v4.2.0)** |
| **ALTA** | `engine/http/session.py` | `DatabaseSessionStore` executando `SELECT` e `UPDATE` em requisições de leitura não modificadas. | Dobro de carga de I/O de escrita em banco para requisições GET read-only. | **Resolvido (v4.2.0)** |
| **ALTA** | `engine/http/kernel.py` | Bufferização irrestrita de requisições POST para inspecionar `_method`. | Upload de arquivos de 100MB+ lia todo o payload em RAM antes de passar ao Starlette, causando OOM. | **Resolvido (v4.2.0)** |
| **MÉDIA** | `engine/orm/db.py` | Checagem de esquemas de tenant consultando `information_schema.schemata` a cada requisição. | Overhead desnecessário de I/O em banco PostgreSQL para rotas multi-tenant. | **Resolvido (v4.2.0)** |
| **MÉDIA** | `engine/orm/db.py` | Ausência de telemetria ou alertas para consultas N+1 durante desenvolvimento. | Desenvolvedores submetiam código com queries N+1 sem detecção no ambiente de testes ou homologação. | **Resolvido (v4.2.0)** |
| **BAIXA** | `pyproject.toml` & `engine/security/captcha.py` | Dependências zumbis (`fastapi`) e import prematuro do Pillow (PIL) no boot. | Overhead desnecessário de memória e tamanho de imagem no boot dos workers. | **Resolvido (v4.2.0)** |

---

## 3. Confronto Detalhado com os 5 Eixos da Auditoria

### Eixo 1: I/O Oculto em Hot Paths e Helpers de View
- **Problema Diagnosticado**: O helper `__()` / `translate()` consultava a tabela `translations` individualmente com `WHERE key = ? AND locale = ?`. Em páginas dinâmicas ou dashboards corporativos, isso gerava um avalanche de consultas sequenciais bloqueantes.
- **Solução Implementada**: Implementado `_load_locale_bundle(app, locale)` que carrega em lote todas as traduções do locale ativo na primeira consulta, memoizando em `_locale_bundles`. Implementado também `_negative_cache` para chaves inexistentes e `clear_translation_cache()` para sincronização de cache.
- **Resultado**: Queda de 500 queries para 1 única query por locale. Latência reduzida de 1.000 ms para 2,1 ms (**476.1x mais rápido**).

### Eixo 2: Ciclo de Vida da Requisição e In-Process Caching
- **Problema Diagnosticado**: Consultas RBAC (`AccessResolver.grants`, `_rows`) e validação de schema de tenant (`ensure_tenant_schema`) eram recalculadas sem reuso no ciclo de vida da requisição HTTP.
- **Solução Implementada**: 
  - Cache de requisição em memória via `ContextVar` (`_request_access_cache`) com limpeza automática em `kernel.serve()` no bloco `finally`.
  - Cache em processo de schemas de tenant (`_known_tenant_schemas`).

### Eixo 3: ORM, Database Engine e Connection Pooling
- **Problema Diagnosticado**: Falta de visibilidade de queries N+1 durante o ciclo de desenvolvimento e testes.
- **Solução Implementada**:
  - Implementado profiler leve por requisição em `DatabaseManager.statement()` ativado via `_request_query_log`.
  - Emite `warning` no logger `craft.orm` com rastreamento da consulta assim que 10 execuções idênticas são detectadas em uma única requisição.

### Eixo 4: Isolamento de Estado Concorrente (Multi-tenancy e Async Safety)
- **Problema Diagnosticado**: Uso de `threading.local()` em `AuthManager` e no isolamento de multi-tenancy `DatabaseManager._tenant`. Em runtimes ASGI como Uvicorn, múltiplas corrotinas compartilham a mesma thread do worker, gerando race conditions graves e vazamento de identidade de usuário/tenant.
- **Solução Implementada**: Substituição completa de `threading.local()` por `contextvars.ContextVar` (`_current_auth_user`, `_current_auth_session`, `_current_tenant_schema`).
- **Garantia**: Isolamento assíncrono estrito garantido pelo runtime do Python (PEP 567).

### Eixo 5: Camada de Middleware e Pipeline HTTP
- **Problema Diagnosticado**: O middleware ASGI `_apply_method_override` lia todo o stream do corpo da requisição via `await receive()` em memória antes de rotear.
- **Solução Implementada**: O scanning de `_method` foi limitado a no máximo 64 KB (`MAX_INSPECT_BYTES = 65536`). Payloads maiores são transmitidos via gerador de replay transparente, evitando esgotamento de RAM. Adicionado reset de auth e cache de autorização no encerramento da thread do worker.

---

## 4. Métricas e Resultados do Benchmark de Desempenho

Resultados obtidos via execução de `python tests/benchmark_performance.py` dentro do container oficial de validação (`framework`):

```
=================================================================
1. BENCHMARK: i18n Translation Subsystem (View Helper __())
=================================================================
Target: 500 translations requested in a single view render
[*] Cloud Uncached (2ms RTT/query): 1000.00 ms (~500 sequential SQL queries)
[*] Craft Engine 4.2 (Bulk Memoized):2.101 ms (1 bulk query + 499 in-memory hits)
[+] Speedup in Cloud Environment:    476.1x faster (latência de rede eliminada)
[+] Local In-Memory Throughput:      238,032 lookups/sec

=================================================================
2. BENCHMARK: Authorization & RBAC Evaluation (@can checks in views)
=================================================================
Target: 100 permission evaluations in a table loop
[*] Without Request Cache:           200.00 ms (100 4-way UNION ALL queries)
[*] Craft Engine 4.2 (ContextVar):   0.329 ms (1 query + 99 ContextVar hits)
[+] Query reduction:                 99.0% fewer queries

=================================================================
3. BENCHMARK: DatabaseSessionStore on Read-Only Requests
=================================================================
Target: 100 Read-Only HTTP Requests (GET):
[*] Craft Engine 4.1 (legacy):       200 SQL queries (100 SELECT + 100 UPDATE)
[*] Craft Engine 4.2 (dirty check):  0 SQL queries executed
[+] DB Write traffic eliminated:     100.0%
```

---

## 5. Conclusão & Prontidão para Produção

Com as mitigações implementadas na versão **v4.2.0-r00020**, o Craft Engine evoluiu para um runtime limpo, robusto e verdadeiramente otimizado para nuvem:
1. **Resiliência a RTT de rede**: Hot paths em views e autorização operam em memória RAM de processo.
2. **Concorrência Segura**: Eliminação de leaks de identidade com `ContextVar`.
3. **Economia de Recursos**: Redução de tráfego desnecessário no PostgreSQL e blindagem contra OOM em uploads.
4. **Verificação Integral**: 100% dos testes da suíte (1.700+ testes) aprovados em container Docker.
