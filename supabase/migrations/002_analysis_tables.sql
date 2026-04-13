-- Analysis results per dimension
CREATE TABLE IF NOT EXISTS analysis_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    evaluation_id UUID NOT NULL REFERENCES evaluations(id) ON DELETE CASCADE,
    dimension TEXT NOT NULL
        CHECK (dimension IN ('posture', 'gesture', 'voice', 'fillers')),
    score INTEGER CHECK (score >= 0 AND score <= 100),
    metrics JSONB NOT NULL DEFAULT '{}',
    confidence TEXT NOT NULL DEFAULT 'high'
        CHECK (confidence IN ('high', 'medium', 'low', 'failed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (evaluation_id, dimension)
);

-- Transcriptions with word-level timestamps
CREATE TABLE IF NOT EXISTS transcriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    evaluation_id UUID NOT NULL REFERENCES evaluations(id) ON DELETE CASCADE UNIQUE,
    full_text TEXT NOT NULL,
    words JSONB NOT NULL DEFAULT '[]',
    language TEXT NOT NULL DEFAULT 'pt-BR',
    model TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Aggregated metrics from all dimensions
CREATE TABLE IF NOT EXISTS aggregated_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    evaluation_id UUID NOT NULL REFERENCES evaluations(id) ON DELETE CASCADE UNIQUE,
    overall_score INTEGER NOT NULL CHECK (overall_score >= 0 AND overall_score <= 100),
    dimension_scores JSONB NOT NULL,
    detailed_metrics JSONB NOT NULL,
    incomplete_dimensions JSONB NOT NULL DEFAULT '[]',
    video_metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_analysis_results_eval ON analysis_results(evaluation_id);
CREATE INDEX IF NOT EXISTS idx_transcriptions_eval ON transcriptions(evaluation_id);
