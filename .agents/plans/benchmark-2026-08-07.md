# Benchmark visual — Craft vs. líderes de mercado (2026-08-07)

Gráfico salvo em [`benchmark-2026-08-07.html`](benchmark-2026-08-07.html) — abra
direto no navegador, funciona offline (sem dependências externas). Também
publicado como Artifact: https://claude.ai/code/artifact/0ce4f99f-dd96-4d3f-a254-01c1451127e4

## O que é

Grade de calor comparando Craft contra 6 padrões de mercado (Django, Laravel,
Rails, Spring Boot, ASP.NET Core, Node.js) em 6 dimensões independentes de
linguagem: Segurança, Performance, Admin UI, CI/CD, Ecossistema, Pronto-para-IA.

**A linha do Craft é medida** (auditoria de código desta sessão + teste de
carga real contra o container). **As demais são estimativa de posicionamento
de mercado** — não foram re-benchmarcadas nesta sessão. Isso está marcado
explicitamente no próprio gráfico (tag "Medido" vs. "Estimativa de mercado"),
não é letra miúda.

## Onde vem a pontuação

Relatório completo, com file:line de cada achado: [`.agents/docs/benchmark-2026-08-07.md`](../../.agents/docs/benchmark-2026-08-07.md)
(4 auditorias especializadas + stress test real). Correções já aplicadas no
commit `7d7562c` — a nota de Segurança do Craft no gráfico (7/10) já reflete
essas correções, não o estado pré-correção.

## Achado que este gráfico não esconde

Craft lidera sozinho em "Pronto p/ IA" (9/10) e fica isolado no fundo em
Performance (2/10 — o teto de ~30 req/s medido, ainda não corrigido; ver
"Não fixed — deliberately deferred" no CHANGELOG). Esse é o próximo alvo
de maior impacto no roadmap.
