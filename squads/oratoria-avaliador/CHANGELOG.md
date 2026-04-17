# CHANGELOG — squad oratoria-avaliador

## [0.7.0-alpha.1] — 2026-04-17

### Story 9.1 — Aggregator Refactor + Confidence Badges (Epic 9)

**Status:** InReview (feature branch, pre-@qa gate)

#### Added
- `SECONDARY_DIMENSIONS` (7 dims) em `contracts/dimensions.py` — separa análise
  complementar (archetypes, tonality, opening, identity, storytelling, temporal,
  congruence) de scoring core.
- `DIMENSION_CONFIDENCE` mapping hardcoded (5 alta, 4 media, 4 baixa).
- `SCHEMA_VERSION_V060` / `SCHEMA_VERSION_V070` constantes.
- `STATE_OF_ART_ENABLED` feature flag em `config.py` (default false).
- Novo payload field `dimension_confidence: dict[str, str]` (flag ON).
- Novo payload field `schema_version` (1.2.0 flag ON / 1.1.0 flag OFF).
- `ConfidenceBadge` React component + tipos TypeScript.
- Legenda + badges per-card em `report/[id]/page.tsx`.
- Prompt awareness em `report_generator.py` — seção "CONFIANCA DAS MEDICOES"
  com instrução hedge para dims 🔴.

#### Changed
- `SCORING_DIMENSIONS` reduz de 10 → 6 (posture, gesture, voice, fillers,
  variety, facial). facial promovida de "scoring fantasma" para scoring real.
- `PESOS_DEFAULT` reescrito (6 dims, soma 1.00) — valores HEURISTIC_V1.
- `PESOS_POR_CONTEXTO` reescrito para 6 contextos × 6 dims.
- `aggregate_metrics()` flag-aware via `is_state_of_art_enabled()`.
- `AggregatedMetrics` Pydantic ganha fields opcionais dimension_confidence +
  schema_version.

#### Preserved (rollback safety)
- `SCORING_DIMENSIONS_V060` (10 dims) — legacy backup.
- `PESOS_DEFAULT_V060` + `PESOS_POR_CONTEXTO_V060` — pre-Epic 9 preservado.
- `aggregate_metrics_legacy()` intocado (Epic 8 guarantee).
- Flag OFF → comportamento bit-idêntico v0.6.0 garantido por tests.

#### Tests
- 18 novos em `tests/test_dimensions.py` (v0.7.0 topology + confidence + schema)
- 13 novos em `tests/test_aggregator_story_9_1.py` (AC1, 2, 3, 4, 5, 7, 8)
- Fixture `all_success_results` ampliada para ALL_DIMENSIONS (13)
- **Regression:** 240/240 PASS

#### Known followups
- **Story 9.7** (condicional): calibração pesos contextuais pós-Gate 3 com
  ground truth Gui Reginatto. Disparada se Pearson <0.75 ou desvio sistemático
  por contexto detectado.
- **Gate 2 smoke** em 10 vídeos de calibração — docs/qa/gate2-story91-smoke.md
  agendado para @qa executar (replay Supabase, delta ≤15pt, rastreabilidade).

#### Migration notes (consumers)
- Frontend: campo `dimension_confidence` é opcional — verificar via `?.` antes de renderizar.
- Backend consumers: `AggregatedMetrics.schema_version` é opcional, checar `is not None`.
- Nenhuma breaking change com flag OFF.

---

## [0.6.0] — 2026-04-15 (validated)

Baseline pre-Epic 9. Score 9.0/10 no validate-squad.

Ver `docs/validation-report-2026-04-15-v0.6.0.md` para detalhes.
