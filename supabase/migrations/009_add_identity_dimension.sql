-- Adicionar 'identity' ao CHECK constraint de analysis_results.dimension
ALTER TABLE analysis_results
    DROP CONSTRAINT IF EXISTS analysis_results_dimension_check;

ALTER TABLE analysis_results
    ADD CONSTRAINT analysis_results_dimension_check
    CHECK (dimension IN ('posture', 'gesture', 'voice', 'fillers', 'variety', 'archetypes', 'identity'));
