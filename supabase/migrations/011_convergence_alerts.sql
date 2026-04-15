-- Story 7.6 AC-6: convergence_alerts table
-- Logs disagreements (r < target) for triage.

CREATE TABLE IF NOT EXISTS convergence_alerts (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  video_id      uuid NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
  dimensao      text,  -- NULL = overall; otherwise dimension name or "pontos_fortes"/"pontos_fracos"
  r_calculado   numeric NOT NULL,
  r_esperado    numeric NOT NULL,
  severidade    text NOT NULL CHECK (severidade IN ('warning', 'critical')),
  detalhes      jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at    timestamptz NOT NULL DEFAULT now(),
  resolvido     boolean NOT NULL DEFAULT false,
  resolvido_em  timestamptz
);

CREATE INDEX IF NOT EXISTS idx_convergence_alerts_resolvido
  ON convergence_alerts(resolvido) WHERE resolvido = false;
CREATE INDEX IF NOT EXISTS idx_convergence_alerts_video_id
  ON convergence_alerts(video_id);

ALTER TABLE convergence_alerts ENABLE ROW LEVEL SECURITY;

CREATE POLICY convergence_alerts_service_role_all ON convergence_alerts
  FOR ALL
  USING (auth.role() = 'service_role')
  WITH CHECK (auth.role() = 'service_role');
