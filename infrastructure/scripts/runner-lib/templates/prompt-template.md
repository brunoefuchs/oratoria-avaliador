# Prompt Template

Read source files FIRST, then write artifacts.

## Contexto

- Runner: `__RUNNER_NAME__`
- Squad: `__SQUAD_SLUG__`
- Phase: `__PHASE_ID__`
- Target: `__TARGET_SLUG__`

## Regras

1. Não referenciar paths protegidos.
2. Usar somente o contexto necessário para a fase atual.
3. Se houver prior context, registrar quando ele foi truncado.

## Prior Context

`truncate_prior_context()` pode reduzir o contexto anterior para manter o prompt pequeno.

## Entrega

Gerar apenas o artefato solicitado para esta fase.
