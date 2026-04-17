/**
 * Story 7.2 — Types do relatorio (cards Identidade, Abertura, Pesos).
 * Reflete output dos workers identity_analyzer.py, opening_analyzer.py, aggregator.py.
 */

export interface IdentityData {
  score: number;
  diagnostico: string;
  vicio_dominante?: string | null;
  total_vicios: number;
  autoridade_count: number;
  vitima_count: number;
  autoridade_ratio: number;
  exemplos: Array<{
    tipo: string;
    texto: string;
    timestamp?: number;
  }>;
  vicios_emocionais?: Record<string, number>;
}

export interface OpeningTechnique {
  tecnica: string;
  label: string;
  descricao?: string;
  exemplo?: string;
  qualidade?: "boa" | "fraca";
}

export interface OpeningAusente {
  tecnica: string;
  sugestao: string;
}

export interface OpeningData {
  disponivel: boolean;
  score: number;
  diagnostico: string;
  feedback: string;
  tecnicas_detectadas: OpeningTechnique[];
  tecnicas_ausentes: OpeningAusente[];
  opening_text: string;
  opening_duration_seconds: number;
}

export type DimensionKey = "variety" | "voice" | "gesture" | "posture" | "fillers";

/**
 * Story 9.1 (Epic 9) — Confidence map por dimensão.
 * Populado apenas quando backend roda com STATE_OF_ART_ENABLED=true.
 * Source of truth: ml-worker/contracts/dimensions.py::DIMENSION_CONFIDENCE
 */
export type DimensionConfidence = Record<string, "alta" | "media" | "baixa">;

export interface DimensionWeights {
  variety: number;
  voice: number;
  gesture: number;
  posture: number;
  fillers: number;
}

export interface ScoreBreakdownItem {
  key: DimensionKey;
  label: string;
  value: number;
  weight: number;
  contribution: number;
}

// Story 7.3 — Storytelling Analyzer
export interface BridgeSentence {
  detected: boolean;
  count: number;
  excerpts: string[];
}

export interface OpeningHook {
  type: "question" | "story" | "stat" | "vulnerability" | "challenge" | "magic_trick" | "none";
  strength: "weak" | "medium" | "strong";
}

export interface CTAData {
  detected: boolean;
  excerpt: string | null;
}

export interface ChemicalDetection {
  detected: boolean;
  examples: string[];
}

export interface CortisolRisk {
  detected: boolean;
  reason: string;
}

export interface StorytellingChemicals {
  dopamine: ChemicalDetection;
  oxytocin: ChemicalDetection;
  endorphins: "not_yet_implemented";
  cortisol_risk: CortisolRisk;
}

export interface StorytellingData {
  disponivel: boolean;
  score: number;
  diagnostico: string;
  bridge_sentence: BridgeSentence;
  opening_hook: OpeningHook;
  cta: CTAData;
  chemicals: StorytellingChemicals;
  suggestions: string[];
}

// Story 7.5 — Tonality VAD Prosody
export interface TonalityVADAvg {
  valence: number;
  arousal: number;
  dominance: number;
}

export interface TonalityVADTemporal {
  start: number;
  end: number;
  v: number;
  a: number;
  d: number;
  textura: string;
}

export type TexturaKey =
  | "neutro"
  | "entusiasmado"
  | "confiante"
  | "apatico"
  | "tenso"
  | "hesitante";

export type TexturaDistribuicao = Record<TexturaKey, number>;

export interface TonalityData {
  disponivel: boolean;
  score: number;
  diagnostico: string;
  vad_medio: TonalityVADAvg;
  vad_temporal: TonalityVADTemporal[];
  textura_distribuicao: TexturaDistribuicao;
  textura_dominante: string;
  feedback: string;
  warnings: string[];
}

// Story 7.4 — Facial Expression Analyzer
export interface FacialEmocionalTexture {
  neutro_percent: number;
  positivo_percent: number;
  tenso_percent: number;
}

export interface FacialData {
  disponivel: boolean;
  score: number;
  diagnostico: string;
  smile_frequency_percent: number;
  smile_variability: number;
  brow_raises_per_minute: number;
  eye_openness_stddev: number;
  emocional_texture: FacialEmocionalTexture;
  feedback: string;
  detection_pct: number;
  warnings: string[];
}
