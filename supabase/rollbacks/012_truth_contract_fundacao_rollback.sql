-- Rollback da migration 012_truth_contract_fundacao.sql
-- Story 8.1 (Truth Contract — Fundacao) T4
--
-- Reverte todas as mudancas estruturais. Dados legacy originais
-- (score/confidence) ficam intactos — a migration original nao apagou nada.
--
-- Veto T4.1: rollback testado antes de apply em prod. Antes de rodar em
-- prod, executar este script em staging e verificar:
--   1. Apos 012 apply: SELECT COUNT(*) FROM analysis_results → snapshot
--   2. Apos 012 rollback: SELECT COUNT(*) FROM analysis_results → deve
--      ser igual ao snapshot
--   3. Apos 012 rollback: \d analysis_results → nao deve ter as colunas
--      dimension_status / failure_reason
--
-- Notas:
--   * Se workers ja estao gravando com Truth Contract quando rollback
--     rodar: colunas somem mas os valores que elas tinham se perdem.
--     Por isso: rollback eh JANELA (minutos apos deploy se algo quebrar).
--   * Nao tenta reverter o backfill em confidence — deixa como estava.

BEGIN;

-- 1. Remover index parcial (depende das colunas)
DROP INDEX IF EXISTS idx_analysis_results_dimension_status;

-- 2. Remover constraints (devem sair antes das colunas)
ALTER TABLE analysis_results
    DROP CONSTRAINT IF EXISTS analysis_results_failure_coherence_check;

ALTER TABLE analysis_results
    DROP CONSTRAINT IF EXISTS analysis_results_dimension_status_check;

-- 3. Remover colunas
ALTER TABLE analysis_results
    DROP COLUMN IF EXISTS failure_reason,
    DROP COLUMN IF EXISTS dimension_status;

COMMIT;

-- ============================================================================
-- Verificacao pos-rollback
-- ============================================================================
-- Estrutura:
--   \d analysis_results
--   -- (nao deve listar dimension_status, failure_reason)
--
-- Integridade:
--   SELECT COUNT(*) FROM analysis_results;
--   -- deve bater com snapshot pre-apply da 012
