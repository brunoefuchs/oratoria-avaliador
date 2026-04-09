-- User token para agrupar avaliacoes do mesmo usuario (sem auth)
ALTER TABLE evaluations ADD COLUMN IF NOT EXISTS user_token UUID;
CREATE INDEX IF NOT EXISTS idx_evaluations_user ON evaluations(user_token);
