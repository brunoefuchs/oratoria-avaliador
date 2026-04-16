-- Story 8.1 (Truth Contract — Fundacao) T4
-- Data: 2026-04-15
-- Autor: dev (Dex)
--
-- Principio: "Um dado no banco so pode existir se for rastreavel ate
-- sua fonte de verdade."
--
-- Esta migration adiciona em analysis_results:
--   * dimension_status TEXT NOT NULL DEFAULT 'ok' — estado rastreavel
--     (valida via CHECK contra os 5 estados canonicos do Pydantic
--      DimensionStatus)
--   * failure_reason TEXT NULL — contexto de falha quando status != 'ok'
--
-- analysis_results.score ja eh NULLABLE desde 002_analysis_tables.sql
-- (nao precisa DROP NOT NULL).
--
-- Pos-migration:
--   * Novos rows de workers com Truth Contract usam WorkerSuccess/WorkerFailure
--     (ver contracts/worker_result.py)
--   * Linhas legacy sao backfilled com dimension_status='ok' quando score
--     IS NOT NULL, ou 'failed' quando confidence='failed'
--
-- Veto T4.1: migration tem rollback testado (012_truth_contract_fundacao_rollback.sql)
-- Veto T4.2: backfill preserva 100% das rows (nada apagado — apenas ADD COLUMN)
-- Veto T4.3: SEM DROP COLUMN — so adicao

BEGIN;

-- ============================================================================
-- 1. Colunas novas
-- ============================================================================

ALTER TABLE analysis_results
    ADD COLUMN IF NOT EXISTS dimension_status TEXT NOT NULL DEFAULT 'ok',
    ADD COLUMN IF NOT EXISTS failure_reason TEXT NULL;

-- CHECK constraint alinhado com Pydantic DimensionStatus enum
-- (ml-worker/contracts/worker_result.py).
ALTER TABLE analysis_results
    DROP CONSTRAINT IF EXISTS analysis_results_dimension_status_check;

ALTER TABLE analysis_results
    ADD CONSTRAINT analysis_results_dimension_status_check
    CHECK (dimension_status IN (
        'ok',
        'failed',
        'skipped',
        'insufficient_data',
        'crashed'
    ));

-- Coherencia logica: failure_reason obrigatorio sempre que status != 'ok'.
-- (Success nunca tem reason; Failure sempre tem.)
ALTER TABLE analysis_results
    DROP CONSTRAINT IF EXISTS analysis_results_failure_coherence_check;

ALTER TABLE analysis_results
    ADD CONSTRAINT analysis_results_failure_coherence_check
    CHECK (
        (dimension_status = 'ok' AND failure_reason IS NULL)
        OR
        (dimension_status <> 'ok' AND failure_reason IS NOT NULL)
    )
    NOT VALID;  -- NOT VALID = nao valida rows existentes (backfill abaixo trata)

-- ============================================================================
-- 2. Backfill das linhas legacy
-- ============================================================================
-- Regras de mapeamento dict-legacy → Truth Contract:
--   confidence='failed'  → dimension_status='failed', reason='legacy_failed_flag'
--   score IS NULL        → dimension_status='skipped', reason='legacy_null_score'
--   otherwise            → dimension_status='ok', reason=NULL (ja eh default)

UPDATE analysis_results
SET
    dimension_status = 'failed',
    failure_reason = 'legacy_failed_flag (confidence=failed pre-truth-contract)'
WHERE confidence = 'failed'
  AND dimension_status = 'ok';

UPDATE analysis_results
SET
    dimension_status = 'skipped',
    failure_reason = 'legacy_null_score (score IS NULL pre-truth-contract)'
WHERE score IS NULL
  AND confidence <> 'failed'
  AND dimension_status = 'ok';

-- Validar constraint depois do backfill
ALTER TABLE analysis_results
    VALIDATE CONSTRAINT analysis_results_failure_coherence_check;

-- ============================================================================
-- 3. Index parcial — performance em queries que filtram por falha
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_analysis_results_dimension_status
    ON analysis_results (dimension_status)
    WHERE dimension_status <> 'ok';

COMMIT;

-- ============================================================================
-- Verificacao pos-migration (rodar manualmente apos apply)
-- ============================================================================
-- Counts por status:
--   SELECT dimension_status, COUNT(*) FROM analysis_results GROUP BY 1;
--
-- Veto T4.2 — preservacao total de rows:
--   SELECT COUNT(*) FROM analysis_results;  -- deve bater com pre-migration
--
-- Veto Pedro (zero mentira):
--   SELECT COUNT(*) FROM analysis_results
--   WHERE score = 0 AND dimension_status = 'ok' AND confidence <> 'failed';
--   -- ideal: proximo de 0 apos migracao dos workers; legacy pode ter casos
--   -- reais de score=0 honesto.
