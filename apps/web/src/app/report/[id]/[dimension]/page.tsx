"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { fetchDimensionDetail } from "@/lib/api-client";
import { AppShell } from "@/components/app-shell";
import { ZONA_LABELS } from "@/lib/report-labels";

const DIMENSION_LABELS: Record<string, string> = {
  variety: "Variedade Vocal",
  voice: "Voz e Dicção",
  gesture: "Presença Visual",
  posture: "Postura e Presença",
  fillers: "Clareza Verbal",
  archetypes: "Arquétipos Vocais",
};

const DIMENSION_ICONS: Record<string, string> = {
  posture: "accessibility",
  gesture: "visibility",
  voice: "mic",
  fillers: "chat_bubble",
  variety: "graphic_eq",
  archetypes: "theater_comedy",
};

const METRIC_LABELS: Record<
  string,
  Record<string, { label: string; reference?: string; description?: string }>
> = {
  voice: {
    wpm: {
      label: "Palavras por minuto",
      reference: "Ideal: 130-170",
      description: "Sua cadência de fala. Acima de 180 cansa o ouvinte; abaixo de 120 perde atenção.",
    },
    pitch_mean_hz: {
      label: "Tom médio (Hz)",
      description: "Frequência fundamental média da sua voz. Não é bom nem ruim — é seu ponto de partida pra modular.",
    },
    pitch_range_semitones: {
      label: "Variação de tom (semitons)",
      reference: "10+ = expressivo",
      description: "Distância do seu tom mais grave ao mais agudo. Range maior = mais teclas do piano em uso.",
    },
    intensity_mean_db: {
      label: "Volume médio (dB)",
      description: "Intensidade média. Speakers TEDx ficam em 60-70 dB com picos pra modular ênfase.",
    },
    cv_velocidade: {
      label: "Variação de velocidade",
      reference: "0.05-0.30 = ideal",
      description: "Quanto a cadência muda ao longo da fala. Anytime anything becomes default, it becomes non-functional.",
    },
    monotonia_score: {
      label: "Pontuação anti-monotonia (0-100)",
      reference: "70+ = ótima variação",
      description: "Composto de variação de tom, volume, velocidade e pausas estratégicas.",
    },
    pitch_accent_per_minute: {
      label: "Ênfases por minuto",
      reference: "TEDx ~50-80/min",
      description: "Picos proeminentes em F0 que marcam palavras-chave. Quantidade de ênfases.",
    },
    pitch_accent_mean_prominence_st: {
      label: "Proeminência média (semitons)",
      reference: "10+ = ênfase dramática",
      description: "Quão DRAMÁTICA é cada ênfase. Distingue modulação intencional de tremor.",
    },
    pitch_accent_strong_per_minute: {
      label: "Ênfases fortes por minuto",
      reference: "≥8 semitons de proeminência",
      description: "Saltos melódicos significativos. Mentores TEDx têm 25-35/min.",
    },
  },
  fillers: {
    fillers_per_minute: {
      label: "Vícios de linguagem por minuto",
      reference: "Meta: < 3/min",
      description: "Quantas vezes 'né', 'tipo', 'sabe', 'então' aparecem por minuto. Substitua por pausas.",
    },
    hesitacoes_per_minute: {
      label: "Hesitações por minuto",
      reference: "< 2/min ideal",
      description: "Frequência de 'ahn', 'eh', 'hum'. Mostra busca de palavra. Pausa silenciosa lê melhor.",
    },
    total_fillers: {
      label: "Total de vícios de linguagem",
      description: "Contagem absoluta no vídeo todo.",
    },
    total_clusters: {
      label: "Problemas de fluência",
      reference: "0 = ideal",
      description: "Trechos com múltiplos vícios em sequência. Sinaliza ansiedade ou falta de preparo.",
    },
    type_token_ratio: {
      label: "Riqueza de vocabulário",
      reference: "0.5+ = bom vocabulário",
      description: "Razão entre palavras únicas e total. Quanto maior, mais variado seu repertório.",
    },
  },
  posture: {
    alignment_score: {
      label: "Alinhamento postural (0-100)",
      description: "Coluna ereta, ombros alinhados. Postura forte = autoridade percebida.",
    },
    open_posture_pct: {
      label: "% postura aberta",
      description: "Tempo com peito aberto vs braços cruzados/fechado. Aberto convida conexão.",
    },
    ombros_nivelados_pct: {
      label: "% ombros nivelados",
      description: "Estabilidade lateral. Ombros tortos sinalizam tensão ou desbalanceio.",
    },
    grounding_score: {
      label: "Estabilidade corporal (0-100)",
      reference: "Base firme = força",
      description: "Pés firmes no chão, sem balanço lateral. Base sólida = presença sólida.",
    },
    proposital_score: {
      label: "Movimento proposital (0-100)",
      description: "Cada movimento tem intenção (não é tique nervoso). Be as big as the room — mas com propósito.",
    },
    padrao_movimento: {
      label: "Padrão de movimento",
      description: "Categoria detectada: estático, oscilante, intencional, etc.",
    },
    // shoulder_to_ear_ratio e shoulder_relax_score: experimentais — não exibir
    // ate calibrar com video studio-grade (mobile MediaPipe Pose 2D nao tem
    // resolucao pra discriminar tensao muscular real).
    shoulder_relax_score: {
      label: "Soltura de ombros (0-100)",
      reference: "85+ = relaxado",
      description: "Score derivado da distância orelha→ombro. Tensão = ansiedade percebida.",
    },
  },
  gesture: {
    eye_contact_pct: {
      label: "% contato visual",
      reference: "Selfie ideal: 70-100%",
      description: "Tempo olhando pra câmera. Em selfie, foco alto é engajamento (não fixação).",
    },
    olhar_baixo_pct: {
      label: "% olhar para baixo",
      reference: "< 10% ideal",
      description: "Olhar pra notas/chão diminui conexão. Ensaie até dispensar slides.",
    },
    gesticulation_pct: {
      label: "% tempo gesticulando",
      reference: "Zona ideal: 40-85%",
      description: "Mãos visíveis e ativas. Mentor TEDx engajado fica naturalmente em 70-90%. Acima de 95% pode distrair.",
    },
    gesto_zona: {
      label: "Zona de gesticulação",
      description: "Faixa vertical onde os gestos acontecem. Peitoral é a zona de poder.",
    },
    duas_maos_pct: {
      label: "% gestos com duas mãos",
      reference: "30%+ = mais expressivo",
      description: "Duas mãos amplificam ideias grandes. Uma mão sozinha limita o palco.",
    },
    vocabulario_gestos: {
      label: "Vocabulário de gestos",
      reference: "6+ posições = variado",
      description: "Quantas regiões diferentes você ocupa. Mais posições = mais 'paleta' visual.",
    },
    distribuicao_olhar: {
      label: "Variação natural do olhar",
      reference: "Selfie ideal: 0.10-0.30",
      description: "Em selfie, foco na câmera é o IDEAL. Valor baixo (0.10-0.30) = engajado natural com micro-variações. Valor alto = olhar disperso (perdendo conexão).",
    },
  },
  variety: {
    diagnostico_geral: {
      label: "Diagnóstico geral",
      description: "Resumo qualitativo da sua variação prosódica.",
    },
    pct_tempo_monotono: {
      label: "% tempo monótono",
      reference: "< 20% ideal",
      description: "Tempo em que volume, tom ou velocidade ficaram estáveis demais. Cérebro desliga em previsão.",
    },
  },
  facial: {
    smile_frequency_percent: {
      label: "% tempo sorrindo",
      reference: "30-60% = caloroso natural",
      description: "Quanto do tempo aparece um sorriso. Calor humano sem cair em sorriso forçado.",
    },
    brow_raises_per_minute: {
      label: "Sobrancelhas (movimentos claros) /min",
      reference: "1-5/min = expressivo",
      description: "Movimentos marcantes de sobrancelha — surpresa, ênfase, dúvida.",
    },
    brow_subtle_per_minute: {
      label: "Sobrancelhas (sutis) /min",
      reference: "complementa os claros",
      description: "Microelevações que captam expressões discretas.",
    },
    brow_combined_per_minute: {
      label: "Sobrancelhas combinadas /min",
      reference: "claros + sutis × 0.5",
      description: "Score combinado usado pra diagnóstico (claros valem 1.0, sutis 0.5).",
    },
    smile_variability: {
      label: "Variabilidade do sorriso",
      reference: ">0.05 = expressivo",
      description: "Quanto seu sorriso muda de intensidade. Sorriso estático = inautêntico.",
    },
    eye_openness_stddev: {
      label: "Variação abertura dos olhos",
      reference: ">0.03 = expressivo",
      description: "Olhos arregalando vs apertando. Captura surpresa, foco, ênfase emocional.",
    },
    detection_pct: {
      label: "% rosto detectado",
      reference: "90+ = bom enquadramento",
      description: "Quanto do tempo o rosto está visível pelo MediaPipe.",
    },
    diagnostico: {
      label: "Diagnóstico",
      description: "Classificação qualitativa: rosto_estatico, expressivo, exagerado, neutro.",
    },
    feedback: {
      label: "Feedback do sistema",
      description: "Recomendação automática baseada no padrão detectado.",
    },
  },
  tonality: {
    diagnostico: {
      label: "Diagnóstico de tonalidade",
      description: "Classificação emocional via VAD (arousal/valence/dominance).",
    },
    textura_dominante: {
      label: "Textura dominante",
      description: "Padrão emocional mais frequente na fala (alegre, neutro, tenso, etc).",
    },
    n_texturas_usadas: {
      label: "Texturas distintas usadas",
      reference: "3+ = variação",
      description: "Quantas categorias emocionais aparecem ao longo do vídeo.",
    },
  },
  archetypes: {
    arquetipo_dominante: {
      label: "Arquétipo dominante",
      description: "Coach (diretivo), Educador (estruturado), Motivador (aspiracional) ou Amigo (caloroso).",
    },
    pct_dominante: {
      label: "% no arquétipo dominante",
      reference: "< 50% = equilibrado",
      description: "Se um arquétipo passa de 50%, você travou nele. Cycling cria contraste.",
    },
    num_arquetipos_usados: {
      label: "Arquétipos usados",
      reference: "4 = ideal",
      description: "Quantos dos 4 arquétipos apareceram. Faltar um = faltar uma cor.",
    },
    trocas_por_minuto: {
      label: "Trocas por minuto",
      reference: "2-5 = ideal",
      description: "Frequência de mudança entre arquétipos. Pouca = monotonia. Muita = caos.",
    },
    lock_in: {
      label: "Lock-in detectado",
      reference: "false = bom",
      description: "Quando você fica preso num único arquétipo. Default = não-funcional.",
    },
  },
  storytelling: {
    diagnostico: {
      label: "Diagnóstico narrativo",
      description: "Estrutura detectada: narrativa_basica, com_bridge, completa, etc.",
    },
  },
  identity: {
    diagnostico: {
      label: "Diagnóstico de identidade",
      description: "Coerência da persona ao longo do vídeo.",
    },
  },
  opening: {
    type: {
      label: "Tipo de abertura",
      description: "Categoria de hook detectada (pergunta, dado, vulnerabilidade, etc).",
    },
    strength: {
      label: "Força do hook",
      description: "Avaliação qualitativa: weak, moderate, strong.",
    },
  },
  congruence: {
    diagnostico: {
      label: "Congruência verbal-vocal-visual",
      description: "Quão alinhado está o que você diz com tom de voz e linguagem corporal.",
    },
  },
};

const SUB_SCORE_LABELS: Record<string, string> = {
  wpm_score: "Palavras por Minuto",
  wpm: "Palavras por Minuto",
  pausa_score: "Pausa",
  pausa: "Pausa",
  pitch_score: "Variação de Tom",
  pitch: "Variação de Tom",
  volume_score: "Variação de Volume",
  volume: "Variação de Volume",
  velocidade_score: "Variação de Velocidade",
  velocidade: "Variação de Velocidade",
  grounding: "Estabilidade Corporal",
  alinhamento: "Alinhamento",
  postura_aberta: "Postura Aberta",
  movimento_proposital: "Movimento Proposital",
  // ombros_relaxados removido do UI ate calibracao studio-grade
  zona: "Zona",
  duas_maos: "Duas Mãos",
  gesticulacao: "Gesticulação",
  contato_visual: "Contato Visual",
  distribuicao_olhar: "Distribuição do Olhar",
  cycling: "Alternância",
  anti_lockin: "Anti Lock-in",
  diversidade: "Diversidade",
};

const SUB_SCORE_DESC: Record<string, string> = {
  wpm_score: "Cadência ideal: 130-170 palavras/min. Acima cansa, abaixo perde.",
  wpm: "Cadência ideal: 130-170 palavras/min. Acima cansa, abaixo perde.",
  pausa_score: "Pausas estratégicas (pré conteúdo) puxam atenção; hesitação dispersa.",
  pausa: "Pausas estratégicas (pré conteúdo) puxam atenção; hesitação dispersa.",
  pitch_score: "Range total entre seu tom mais grave e mais agudo. 15+ semitons = TEDx.",
  pitch: "Range total entre seu tom mais grave e mais agudo. 15+ semitons = TEDx.",
  volume_score: "Quanto seu volume modula ao longo da fala. Variar = peaks and troughs.",
  volume: "Quanto seu volume modula ao longo da fala. Variar = peaks and troughs.",
  velocidade_score: "Quanto sua cadência muda. Não é só rápido vs devagar — é o ritmo mudar.",
  velocidade: "Quanto sua cadência muda. Não é só rápido vs devagar — é o ritmo mudar.",
  grounding: "Pés firmes, corpo estável. Base solida = presença sólida.",
  alinhamento: "Coluna ereta, ombros alinhados. Postura forte vende autoridade.",
  postura_aberta: "Peito aberto vs fechado. Aberto convida conexão.",
  movimento_proposital: "Cada movimento com intenção, não tique nervoso.",
  ombros_relaxados: "Distância orelha→ombro. Ombros encolhidos = tensão = ansiedade percebida.",
  zona: "Faixa vertical onde gesticula. Peitoral é zona de poder.",
  duas_maos: "Gesticular com 2 mãos amplifica ideias grandes.",
  gesticulacao: "Tempo com mãos visíveis e ativas. Mãos paradas = energia parada.",
  contato_visual: "Tempo olhando pra câmera. Audiência precisa sentir presença.",
  distribuicao_olhar: "Quão equilibradamente você varre o enquadramento.",
  cycling: "Frequência de troca entre os 4 arquétipos.",
  anti_lockin: "Você não trava num único arquétipo. Default = não-funcional.",
  diversidade: "Quantos dos 4 arquétipos você usou no vídeo.",
};

const ARCHETYPE_LABELS: Record<string, string> = {
  educador: "Educador",
  coach: "Coach",
  motivador: "Motivador",
  amigo: "Amigo",
};

function getScoreTone(score: number) {
  if (score >= 70)
    return { text: "text-secondary", bar: "bg-secondary" };
  if (score >= 40)
    return { text: "text-tertiary", bar: "bg-tertiary" };
  return { text: "text-error", bar: "bg-error" };
}

export default function DimensionDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;
  const dimension = params.dimension as string;
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDimensionDetail(id, dimension)
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [id, dimension]);

  if (loading) {
    return (
      <AppShell maxWidth="lg" showBack backHref={`/report/${id}`}>
        <div className="min-h-[50vh] flex items-center justify-center">
          <p className="text-on-surface-variant text-sm">Carregando...</p>
        </div>
      </AppShell>
    );
  }

  if (!data) {
    return (
      <AppShell maxWidth="lg" showBack backHref={`/report/${id}`}>
        <div className="min-h-[40vh] flex items-center justify-center">
          <p className="text-error">Dimensão não encontrada</p>
        </div>
      </AppShell>
    );
  }

  const tone = getScoreTone(data.score);
  const metricDefs = METRIC_LABELS[dimension] || {};
  const feedback = data.feedback || {};
  const metrics = data.metrics || {};
  const icon = DIMENSION_ICONS[dimension] || "analytics";

  return (
    <AppShell maxWidth="lg" showBack backHref={`/report/${id}`} backLabel="Relatório">
      <div className="space-y-8">
        {/* Hero */}
        <section className="rounded-3xl bg-surface-container-low p-6 md:p-8 stage-ambient relative overflow-hidden">
          <div className="flex items-start justify-between gap-6">
            <div>
              <span
                className={`material-symbols-outlined text-3xl mb-3 block ${tone.text}`}
              >
                {icon}
              </span>
              <span className="font-label text-xs uppercase tracking-[0.3em] text-on-surface-variant">
                Dimensão
              </span>
              <h1 className="font-headline text-2xl md:text-4xl font-extrabold tracking-tight mt-1">
                {DIMENSION_LABELS[dimension] || dimension}
              </h1>
              {(feedback.label || feedback.score_label) && (
                <p className="mt-3 text-sm text-on-surface-variant">
                  {feedback.label || feedback.score_label}
                </p>
              )}
            </div>
            <div className="shrink-0 flex items-baseline gap-1">
              <span
                className={`font-headline text-5xl md:text-7xl font-extrabold ${tone.text}`}
              >
                {data.score}
              </span>
              <span className="text-on-surface-variant">/100</span>
            </div>
          </div>
          <div className="absolute bottom-0 left-0 right-0 fluency-wave opacity-50" />
        </section>

        {data.confidence === "low" && (
          <div className="rounded-2xl bg-tertiary/10 p-4 text-sm text-tertiary ghost-border flex items-start gap-3">
            <span className="material-symbols-outlined">info</span>
            <span>
              Confiança baixa — qualidade do vídeo pode ter afetado a análise.
            </span>
          </div>
        )}

        {/* Métricas */}
        {Object.keys(metrics).length > 0 && (
          <section className="space-y-3">
            <h2 className="font-label text-xs uppercase tracking-[0.3em] text-secondary">
              Métricas
            </h2>
            <div className="grid md:grid-cols-2 gap-3">
              {Object.entries(metrics).map(([key, value]) => {
                const def = metricDefs[key];
                if (!def) return null;

                let displayValue: string;
                if (typeof value === "boolean") {
                  displayValue = value ? "Sim" : "Não";
                } else if (typeof value === "number") {
                  displayValue = String(Math.round(value * 100) / 100);
                } else {
                  // Story 7.1 AC-4 fix QA — traduzir gesto_zona via ZONA_LABELS
                  if (key === "gesto_zona" && typeof value === "string") {
                    displayValue =
                      ZONA_LABELS[value as keyof typeof ZONA_LABELS] ?? String(value);
                  } else {
                    displayValue = String(value);
                  }
                }

                return (
                  <div
                    key={key}
                    className="flex items-center justify-between rounded-xl bg-surface-container-low p-4 ghost-border gap-4"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-on-surface">
                        {def.label}
                      </p>
                      {def.reference && (
                        <p className="text-xs text-secondary/80 mt-0.5">
                          {def.reference}
                        </p>
                      )}
                      {def.description && (
                        <p className="text-[11px] text-on-surface-variant/80 mt-1.5 leading-snug">
                          {def.description}
                        </p>
                      )}
                    </div>
                    <span className="font-headline text-lg font-bold text-secondary shrink-0">
                      {displayValue}
                    </span>
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {/* Sub-scores */}
        {metrics.sub_scores && (
          <section className="space-y-3">
            <h2 className="font-label text-xs uppercase tracking-[0.3em] text-secondary">
              Pontuações
            </h2>
            <div className="rounded-2xl bg-surface-container-low p-5 ghost-border space-y-3">
              {Object.entries(
                metrics.sub_scores as Record<string, number>
              ).map(([key, value]) => {
                const subTone = getScoreTone(value);
                return (
                  <div key={key} className="space-y-1.5">
                    <div className="flex justify-between text-sm">
                      <span className="text-on-surface">
                        {SUB_SCORE_LABELS[key] || key.replace(/_/g, " ")}
                      </span>
                      <span className={`font-mono font-bold ${subTone.text}`}>
                        {value}
                      </span>
                    </div>
                    <div className="h-1.5 rounded-full bg-surface-container-highest overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all ${subTone.bar}`}
                        style={{ width: `${Math.min(100, value)}%` }}
                      />
                    </div>
                    {SUB_SCORE_DESC[key] && (
                      <p className="text-[11px] text-on-surface-variant/80 leading-snug pt-0.5">
                        {SUB_SCORE_DESC[key]}
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {/* Distribuição de arquétipos */}
        {dimension === "archetypes" && metrics.distribuicao && (
          <section className="space-y-3">
            <h2 className="font-label text-xs uppercase tracking-[0.3em] text-secondary">
              Distribuição de Arquétipos
            </h2>
            <div className="rounded-2xl bg-surface-container-low p-5 ghost-border space-y-3">
              {Object.entries(metrics.distribuicao as Record<string, number>)
                .sort(([, a], [, b]) => b - a)
                .map(([arq, pct]) => (
                  <div key={arq} className="space-y-1.5">
                    <div className="flex justify-between text-sm">
                      <span className="text-on-surface">
                        {ARCHETYPE_LABELS[arq] || arq}
                      </span>
                      <span className="font-mono font-bold text-secondary">
                        {pct}%
                      </span>
                    </div>
                    <div className="h-2 rounded-full bg-surface-container-highest overflow-hidden">
                      <div
                        className="h-full rounded-full bg-ai-pulse transition-all"
                        style={{ width: `${Math.min(100, pct)}%` }}
                      />
                    </div>
                  </div>
                ))}
            </div>
            {metrics.acessiveis && (
              <p className="text-xs text-secondary">
                Acessíveis:{" "}
                {(metrics.acessiveis as string[])
                  .map((a) => ARCHETYPE_LABELS[a] || a)
                  .join(", ")}
              </p>
            )}
            {metrics.ausentes &&
              (metrics.ausentes as string[]).length > 0 && (
                <p className="text-xs text-tertiary">
                  Ausentes:{" "}
                  {(metrics.ausentes as string[])
                    .map((a) => ARCHETYPE_LABELS[a] || a)
                    .join(", ")}
                </p>
              )}
          </section>
        )}

        {/* Variedade — dimensões detalhadas */}
        {dimension === "variety" && metrics.dimensoes && (
          <section className="space-y-3">
            <h2 className="font-label text-xs uppercase tracking-[0.3em] text-secondary">
              Variação por Dimensão
            </h2>
            <div className="grid md:grid-cols-2 gap-3">
              {Object.entries(metrics.dimensoes as Record<string, any>).map(
                ([key, dim]: [string, any]) => {
                  const dimTone = getScoreTone(dim.score);
                  return (
                    <div
                      key={key}
                      className="rounded-xl bg-surface-container-low p-4 ghost-border space-y-2"
                    >
                      <div className="flex justify-between items-center">
                        <span className="font-medium text-on-surface capitalize">
                          {key}
                        </span>
                        <span
                          className={`font-headline text-xl font-bold ${dimTone.text}`}
                        >
                          {dim.score}
                        </span>
                      </div>
                      <p className="text-xs text-on-surface-variant capitalize">
                        {dim.diagnostico?.replace(/_/g, " ")}
                      </p>
                      <div className="h-1.5 rounded-full bg-surface-container-highest overflow-hidden">
                        <div
                          className={`h-full rounded-full ${dimTone.bar}`}
                          style={{ width: `${Math.min(100, dim.score)}%` }}
                        />
                      </div>
                    </div>
                  );
                }
              )}
            </div>
          </section>
        )}

        {/* Defaults detectados (variety) */}
        {dimension === "variety" &&
          metrics.defaults_detectados &&
          (metrics.defaults_detectados as string[]).length > 0 && (
            <section className="rounded-2xl bg-tertiary/10 p-5 ghost-border">
              <p className="font-headline text-base font-bold text-tertiary">
                Padrões detectados
              </p>
              <p className="mt-2 text-sm text-on-surface-variant">
                Pilares travados:{" "}
                <strong>
                  {(metrics.defaults_detectados as string[]).join(", ")}
                </strong>
              </p>
              <p className="mt-3 text-xs text-tertiary italic">
                &ldquo;Sempre que algo se torna padrão, se torna
                não-funcional.&rdquo;
              </p>
            </section>
          )}

        {/* Feedback v2 */}
        {feedback.feedback && (
          <section className="space-y-3">
            <div className="rounded-2xl bg-surface-container-low p-5 ghost-border">
              <p className="text-sm text-on-surface leading-relaxed">
                {feedback.feedback}
              </p>
            </div>
            {feedback.dica && (
              <div className="rounded-2xl bg-surface-container-high p-5 ghost-border">
                <p className="font-label text-[10px] uppercase tracking-[0.2em] text-secondary mb-2">
                  Dica prática
                </p>
                <p className="text-sm text-on-surface leading-relaxed">
                  {feedback.dica}
                </p>
              </div>
            )}
          </section>
        )}

        {/* Feedback v1 (retrocompat) */}
        {!feedback.feedback && feedback.strengths && (
          <section className="space-y-4">
            <div className="rounded-2xl bg-surface-container-low p-5 ghost-border">
              <p className="font-label text-[10px] uppercase tracking-[0.2em] text-secondary mb-3">
                Pontos fortes
              </p>
              <ul className="space-y-2">
                {feedback.strengths.map((s: string, i: number) => (
                  <li
                    key={i}
                    className="flex items-start gap-2 text-sm text-on-surface-variant"
                  >
                    <span className="material-symbols-outlined text-secondary text-base mt-0.5">
                      check
                    </span>
                    {s}
                  </li>
                ))}
              </ul>
            </div>

            <div className="rounded-2xl bg-surface-container-low p-5 ghost-border">
              <p className="font-label text-[10px] uppercase tracking-[0.2em] text-tertiary mb-3">
                Melhorias
              </p>
              <ul className="space-y-2">
                {feedback.improvements?.map((s: string, i: number) => (
                  <li
                    key={i}
                    className="flex items-start gap-2 text-sm text-on-surface-variant"
                  >
                    <span className="material-symbols-outlined text-tertiary text-base mt-0.5">
                      arrow_forward
                    </span>
                    {s}
                  </li>
                ))}
              </ul>
            </div>

            {feedback.tip && (
              <div className="rounded-2xl bg-surface-container-high p-5 ghost-border">
                <p className="font-label text-[10px] uppercase tracking-[0.2em] text-secondary mb-2">
                  Dica
                </p>
                <p className="text-sm text-on-surface leading-relaxed">
                  {feedback.tip}
                </p>
              </div>
            )}
          </section>
        )}

        {/* Top fillers */}
        {dimension === "fillers" && metrics.top_fillers && (
          <section className="space-y-3">
            <h2 className="font-label text-xs uppercase tracking-[0.3em] text-secondary">
              Principais vícios
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
              {(metrics.top_fillers as any[]).map((f: any, i: number) => (
                <div
                  key={i}
                  className="flex items-center justify-between rounded-xl bg-surface-container-low px-4 py-3 ghost-border"
                >
                  <span className="text-sm text-on-surface italic">
                    &ldquo;{f.word}&rdquo;
                  </span>
                  <span className="font-headline font-bold text-tertiary">
                    {f.count}x
                  </span>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Clusters (fillers) */}
        {dimension === "fillers" &&
          metrics.clusters &&
          (metrics.clusters as any[]).length > 0 && (
            <section className="rounded-2xl bg-error-container/20 p-5 ghost-border">
              <p className="font-headline text-base font-bold text-error">
                Problemas de fluência ({(metrics.clusters as any[]).length})
              </p>
              <p className="text-xs text-on-surface-variant mt-1">
                Momentos com 3+ vícios em sequência rápida.
              </p>
            </section>
          )}

        {/* Pausas (voice) */}
        {dimension === "voice" && metrics.pausas && (
          <section className="space-y-3">
            <h2 className="font-label text-xs uppercase tracking-[0.3em] text-secondary">
              Pausas
            </h2>
            <div className="grid grid-cols-3 gap-3">
              <div className="rounded-2xl bg-surface-container-low p-4 text-center ghost-border">
                <p className="font-headline text-2xl font-bold text-secondary">
                  {metrics.pausas.qtd_estrategicas}
                </p>
                <p className="text-xs text-on-surface-variant mt-1">
                  Estratégicas
                </p>
              </div>
              <div className="rounded-2xl bg-surface-container-low p-4 text-center ghost-border">
                <p className="font-headline text-2xl font-bold text-tertiary">
                  {metrics.pausas.qtd_hesitacao}
                </p>
                <p className="text-xs text-on-surface-variant mt-1">
                  Hesitação
                </p>
              </div>
              <div className="rounded-2xl bg-surface-container-low p-4 text-center ghost-border">
                <p className="font-headline text-2xl font-bold text-on-surface-variant">
                  {metrics.pausas.qtd_respiracao}
                </p>
                <p className="text-xs text-on-surface-variant mt-1">
                  Respiração
                </p>
              </div>
            </div>
          </section>
        )}
      </div>
    </AppShell>
  );
}
