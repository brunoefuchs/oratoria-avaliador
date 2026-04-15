-- Story 7.6 AC-5: convergence_runs table
-- Stores one row per (video_id, llm, prompt_version).

CREATE TABLE IF NOT EXISTS convergence_runs (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  video_id            uuid NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
  llm                 text NOT NULL CHECK (llm IN ('gemini', 'claude', 'gpt')),
  score_geral         numeric NOT NULL CHECK (score_geral >= 0 AND score_geral <= 100),
  scores_por_dimensao jsonb NOT NULL,
  pontos_fortes_top3  text[] NOT NULL,
  pontos_fracos_top3  text[] NOT NULL,
  raw_response        text,
  prompt_version      text NOT NULL,
  model_version       text NOT NULL,
  created_at          timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT convergence_runs_unique UNIQUE (video_id, llm, prompt_version)
);

CREATE INDEX IF NOT EXISTS idx_convergence_runs_video_id
  ON convergence_runs(video_id);
CREATE INDEX IF NOT EXISTS idx_convergence_runs_created_at
  ON convergence_runs(created_at DESC);

ALTER TABLE convergence_runs ENABLE ROW LEVEL SECURITY;

-- Owner-only access (Bruno / service role). Adjust policy when sharing with team.
CREATE POLICY convergence_runs_service_role_all ON convergence_runs
  FOR ALL
  USING (auth.role() = 'service_role')
  WITH CHECK (auth.role() = 'service_role');
