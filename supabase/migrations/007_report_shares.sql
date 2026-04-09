-- Links de compartilhamento de relatorio
CREATE TABLE IF NOT EXISTS report_shares (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    evaluation_id UUID NOT NULL REFERENCES evaluations(id) ON DELETE CASCADE,
    share_token UUID NOT NULL DEFAULT uuid_generate_v4(),
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '30 days'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(share_token)
);

CREATE INDEX IF NOT EXISTS idx_shares_token ON report_shares(share_token);
CREATE INDEX IF NOT EXISTS idx_shares_eval ON report_shares(evaluation_id);
