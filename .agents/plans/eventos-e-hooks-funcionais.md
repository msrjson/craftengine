# Fatia — Event bus e plugin hooks funcionais

**Data:** 2026-08-08 · **Estado antes:** motores prontos, nunca invocados.

## Diagnóstico

Verificado no código, não na documentação:

- `EventDispatcher` é completo e testado (`listen`/`dispatch`/`until`/halt/wildcard/
  `subscribe`), mas **nada no framework nem no app dispara evento algum**. O único
  `Event.listen(...)` existente (`app/Providers/EventServiceProvider.py:17`) registra
  um listener para `PostPublished`, que jamais é emitido.
- `PluginManager` tem descoberta em disco, persistência em banco e sistema de hooks,
  mas `trigger_hook` só aparece em **testes**. O framework nunca dispara hook durante
  o ciclo de request, e `plugins/` está vazio.

Ou seja: dois motores corretos e sem interruptor. A fatia liga o interruptor.

## Decisão de arquitetura

**Um único caminho de disparo, duas APIs.** O dispatcher já casa listeners por
string (`dispatcher.py:74-75` — `registered == getattr(event, "name", None)`).
Logo os hooks de plugin **não ganham um segundo mecanismo de disparo**: o
`PluginManager` entra como *listener wildcard* no barramento e reencaminha cada
evento para os hooks registrados sob aquele nome.

Consequência: um ponto de disparo por ponto do ciclo de vida. Quem escreve um
listener tipado e quem escreve um hook de plugin escutam o mesmo evento, sem
duplicação de código de emissão.

Alternativa rejeitada: emitir evento *e* chamar `trigger_hook` em cada call site —
dobra os pontos de manutenção e deixa os dois sistemas divergirem com o tempo.

## Contrato

### Eventos de ciclo de vida (`engine/events/lifecycle.py`, novo)

| Classe | `name` | Carrega |
|---|---|---|
| `ModelCreated` | `model.created` | `model`, `table` |
| `ModelUpdated` | `model.updated` | `model`, `table` |
| `ModelDeleted` | `model.deleted` | `model`, `table` |
| `UserAuthenticated` | `auth.login` | `user` |
| `UserLoginFailed` | `auth.failed` | `email` (nunca a senha) |
| `UserLoggedOut` | `auth.logout` | `user` |

### Pontos de disparo

- `Model.force_create` → `ModelCreated` (cobre `create()`, que afunila aqui)
- `Model.save` no caminho de UPDATE → `ModelUpdated`
- `Model.delete` → `ModelDeleted`
- `AuthManager.attempt` → `UserAuthenticated` / `UserLoginFailed`
- `AuthManager.logout` → `UserLoggedOut`

### Regras duras

1. **Emitir nunca quebra a operação.** Um listener defeituoso não pode derrubar um
   INSERT. Falha de listener em evento de ciclo de vida é **logada, não engolida** —
   mesmo contrato que `trigger_hook` já adota (`plugins/manager.py:96-104`).
2. **Sem container, sem evento.** Model é usado em teste unitário sem app booted;
   o helper `fire()` vira no-op silencioso se não houver dispatcher ligado.
3. **Senha nunca entra em evento.** `UserLoginFailed` carrega só o e-mail.
4. **Recursão:** um plugin que grava no banco dentro de `model.created` dispara
   `model.created` de novo. O plugin de auditoria ignora a própria tabela — trap
   documentada no código.

## Plugin real de exemplo

`plugins/audit-log/plugin.py` — grava criação/alteração/exclusão de modelos e
login/logout em `system_logs`, usando o model `SystemLog` que já existe. Escolhido
por ser lógica real e útil (trilha de auditoria), não um "hello world", e por
exercitar os 6 eventos de uma vez.

## Verificação

- Teste de que cada evento é realmente emitido no seu ponto de ciclo de vida.
- Teste da ponte: hook de plugin registrado por nome recebe o evento.
- Teste de que listener que explode **não** quebra o INSERT.
- Teste do plugin de auditoria fim-a-fim, incluindo não-recursão.
- Suíte completa verde.
