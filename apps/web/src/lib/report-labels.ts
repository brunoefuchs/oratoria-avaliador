/**
 * Story 7.1 AC-5 — Source-of-truth dos labels do relatório em PT-BR.
 *
 * Por que existe: evitar grep-replace disperso ao adicionar novas dimensões.
 * Importe destes objetos em `app/report/[id]/page.tsx`, `[dimension]/page.tsx`,
 * `shared/page.tsx` e novos componentes (cards de Identidade, Abertura, etc).
 *
 * Stories que dependem deste arquivo:
 * - 7.2 — UI Cards (Identidade, Abertura, Pesos)
 * - 7.3 — Storytelling card
 * - 7.4 — Facial card
 * - 7.5 — Tonality (sub-score em Voz e Dicção)
 */

export const DIMENSIONS = {
  variety: "Variedade Vocal",
  voice: "Voz e Dicção",
  gesture: "Presença Visual",
  posture: "Postura e Presença",
  fillers: "Clareza Verbal",
  archetypes: "Arquétipos Vocais",
  // Sub-dimensões qualitativas (não entram no overall_score)
  identity: "Sua Identidade",
  opening: "Sua Abertura",
  narrative: "Narrativa",
  facial: "Expressão Facial",
  congruence: "Congruência",
} as const;

export const METRICS = {
  // Voz e Dicção
  pitch: "Tom",
  pitch_variation: "Variação de Tom",
  wpm: "Palavras por Minuto",
  volume: "Volume",
  volume_mean_db: "Volume médio (dB)",
  cv_velocidade: "Variação de velocidade",
  monotonia_score: "Variação Global da Voz",
  // Vícios de Linguagem
  vicios_por_minuto: "Vícios de Linguagem por Minuto",
  fillers_per_minute: "Vícios de Linguagem por Minuto", // alias compat
  hesitacoes_per_minute: "Hesitações por Minuto",
  total_fillers: "Total de Vícios de Linguagem",
  total_clusters: "Problemas de Fluência",
  type_token_ratio: "Riqueza de Vocabulário",
  // Presença Visual
  eye_contact_pct: "% Contato Visual",
  olhar_baixo_pct: "% Olhar para Baixo",
  gesticulation_pct: "% Tempo Gesticulando",
  gesto_zona: "Zona de Gesticulação",
  duas_maos_pct: "% Gestos com Duas Mãos",
  vocabulario_gestos: "Vocabulário de Gestos",
  distribuicao_olhar: "Distribuição do Olhar",
  // Postura
  alignment_score: "Alinhamento Postural",
  open_posture_pct: "% Postura Aberta",
  ombros_nivelados_pct: "% Ombros Nivelados",
  grounding_score: "Estabilidade Corporal",
  proposital_score: "Movimento Proposital",
  // Variedade
  defaults_detectados: "Padrões Detectados",
  pilares_travados: "Pilares Travados",
  pct_tempo_monotono: "% Tempo Monótono",
} as const;

export const REFERENCES = {
  eye_contact_ideal: "Zona ideal: 70-90%",
  gesticulation_ideal: "Zona ideal: 40-70%",
  vicios_meta: "Meta: < 3/min",
  hesitacoes_meta: "< 2/min ideal",
  type_token_meta: "0.5+ = bom vocabulário",
  duas_maos_meta: "30%+ = mais expressivo",
  vocabulario_meta: "6+ posições = variado",
  pitch_ideal: "Ideal: 130-170 Hz",
  wpm_ideal: "Ideal: 130-170",
} as const;

export const ZONA_LABELS = {
  // Story 7.1 AC-4 — gesto_zona
  ideal: "Ideal",
  pouca_variacao: "Pouca variação",
  excesso: "Excesso / Distrai",
} as const;

export const SCORE_TERMS = {
  pontuacao: "Pontuação",
  pontuacoes: "Pontuações",
  diagnostico: "Diagnóstico",
  feedback: "Feedback",
  forcas: "Pontos Fortes",
  melhorias: "Top Melhorias",
} as const;

export type DimensionKey = keyof typeof DIMENSIONS;
export type MetricKey = keyof typeof METRICS;

/**
 * Story 9.1 (Epic 9) — Confidence badges por dimensão.
 * Source of truth: ml-worker/contracts/dimensions.py::DIMENSION_CONFIDENCE
 * Sempre espelhar mudanças backend aqui.
 */
export type ConfidenceLevel = "alta" | "media" | "baixa";

export const CONFIDENCE_BADGES: Record<ConfidenceLevel, {
  emoji: string;
  label: string;
  tooltip: string;
}> = {
  alta: {
    emoji: "🟢",
    label: "Alta confiança",
    tooltip: "Medição ML validada com confiança >85%. Use este score com segurança.",
  },
  media: {
    emoji: "🟡",
    label: "Média confiança",
    tooltip: "Heurística sobre features confiáveis. Trate como indicativo, não veredito.",
  },
  baixa: {
    emoji: "🔴",
    label: "Análise complementar",
    tooltip: "Análise qualitativa em calibração com mentor humano. Use como sugestão.",
  },
} as const;

export const SECONDARY_DIMENSION_BANNER =
  "Análise complementar — em calibração com mentor especialista";
