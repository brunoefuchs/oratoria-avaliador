-- Migration 014 — Expand analysis_results.dimension CHECK constraint
-- Date: 2026-04-17
-- Hotfix N7: secondary dims (facial, tonality, opening, storytelling, temporal,
-- congruence) estavam falhando no INSERT com violação de check constraint.
-- Constraint antiga só permitia scoring dims pre-Epic 9.

-- Drop old constraint (nome auto-gerado pelo Postgres na migration original)
ALTER TABLE analysis_results
  DROP CONSTRAINT IF EXISTS analysis_results_dimension_check;

-- New constraint com todas as 13 dimensions do Epic 9 + 1 experimental
ALTER TABLE analysis_results
  ADD CONSTRAINT analysis_results_dimension_check
  CHECK (dimension IN (
    -- Scoring dims (6 — Epic 9 canonical)
    'posture', 'gesture', 'voice', 'fillers', 'variety', 'facial',
    -- Secondary/augmentation dims (7)
    'archetypes', 'tonality', 'opening', 'identity',
    'storytelling', 'temporal', 'congruence',
    -- Story 9.6 (opt-in)
    'gesture_semantic'
  ));

COMMENT ON CONSTRAINT analysis_results_dimension_check ON analysis_results IS
  'Epic 9 (Story 9.1 + N7 fix): permite todas as 13 dims canonical + gesture_semantic (9.6)';
