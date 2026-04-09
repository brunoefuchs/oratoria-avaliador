-- Contexto do orador antes da avaliacao
-- Alimenta o LLM para coaching personalizado
CREATE TABLE IF NOT EXISTS evaluation_context (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    evaluation_id UUID NOT NULL REFERENCES evaluations(id) ON DELETE CASCADE,
    sentimento INTEGER CHECK (sentimento BETWEEN 1 AND 5),
    maior_medo TEXT[],
    contexto TEXT CHECK (contexto IN ('vendas', 'palco', 'aula', 'rede_social', 'reuniao', 'podcast', 'outro')),
    avaliado_antes BOOLEAN DEFAULT false,
    objetivo TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(evaluation_id)
);

CREATE INDEX IF NOT EXISTS idx_eval_context_eval ON evaluation_context(evaluation_id);
