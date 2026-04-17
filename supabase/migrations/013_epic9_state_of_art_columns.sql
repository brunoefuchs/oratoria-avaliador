-- Migration 013 — Epic 9 State of the Art columns
-- Date: 2026-04-17
-- Hotfix: Story 9.1 assumiu estas colunas existiam em aggregated_metrics, mas nao
-- foram criadas. Supabase dropa silent via pydantic extra=allow.
--
-- Adiciona 5 colunas opcionais:
-- - partial_aggregation: indica se alguma scoring dim falhou
-- - schema_version: 1.1.0 (flag OFF) ou 1.2.0 (flag ON)
-- - dimension_confidence: badges 🟢🟡🔴 por dim (so flag ON)
-- - contexto: contexto resolvido (palco/podcast/vendas/etc)
-- - pesos_utilizados: pesos usados no calculo (pra auditoria)

ALTER TABLE aggregated_metrics
  ADD COLUMN IF NOT EXISTS partial_aggregation BOOLEAN DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS schema_version TEXT,
  ADD COLUMN IF NOT EXISTS dimension_confidence JSONB,
  ADD COLUMN IF NOT EXISTS contexto TEXT,
  ADD COLUMN IF NOT EXISTS pesos_utilizados JSONB;

-- Index em schema_version pra filtros rapidos (consumers detectam formato)
CREATE INDEX IF NOT EXISTS idx_aggregated_metrics_schema_version
  ON aggregated_metrics(schema_version);

COMMENT ON COLUMN aggregated_metrics.partial_aggregation IS
  'Story 9.1: TRUE quando alguma scoring dim falhou (overall_score derivado de subset)';
COMMENT ON COLUMN aggregated_metrics.schema_version IS
  'Story 9.1: 1.1.0 = flag OFF (v0.6.0 legacy), 1.2.0 = flag ON (Epic 9)';
COMMENT ON COLUMN aggregated_metrics.dimension_confidence IS
  'Story 9.1: {dim: alta|media|baixa} — populado apenas quando STATE_OF_ART_ENABLED=true';
COMMENT ON COLUMN aggregated_metrics.contexto IS
  'Story 9.1: contexto resolvido (palco/podcast/vendas/rede_social/reuniao/aula)';
COMMENT ON COLUMN aggregated_metrics.pesos_utilizados IS
  'Story 9.1: pesos aplicados no calculo (rastreabilidade/auditoria)';
