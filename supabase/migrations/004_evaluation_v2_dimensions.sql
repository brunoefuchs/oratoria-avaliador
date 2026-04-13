-- Migração v2: Expandir sistema de avaliação de 4 para 6 dimensões
-- Novas dimensões: variety (variedade vocal), archetypes (arquétipos vocais)
-- Novos campos no report: forças, melhorias 80/20, plano 12 semanas, mensagem final

-- 1. Expandir CHECK constraint em analysis_results para incluir novas dimensões
ALTER TABLE analysis_results
    DROP CONSTRAINT IF EXISTS analysis_results_dimension_check;

ALTER TABLE analysis_results
    ADD CONSTRAINT analysis_results_dimension_check
    CHECK (dimension IN ('posture', 'gesture', 'voice', 'fillers', 'variety', 'archetypes'));

-- 2. Adicionar colunas novas na tabela reports
ALTER TABLE reports ADD COLUMN IF NOT EXISTS forcas JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS melhorias JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS plano_12_semanas JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS mensagem_final TEXT NOT NULL DEFAULT '';
