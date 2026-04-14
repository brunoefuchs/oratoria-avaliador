"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { fetchDimensionDetail } from "@/lib/api-client";
import { AppShell } from "@/components/app-shell";

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
  Record<string, { label: string; reference?: string }>
> = {
  voice: {
    wpm: { label: "Palavras por minuto", reference: "Ideal: 130-170" },
    pitch_mean_hz: { label: "Tom médio (Hz)" },
    pitch_range_semitones: {
      label: "Variação de tom (semitons)",
      reference: "10+ = expressivo",
    },
    intensity_mean_db: { label: "Volume médio (dB)" },
    cv_velocidade: {
      label: "Variação de velocidade",
      reference: "0.08-0.30 = ideal",
    },
    monotonia_score: {
      label: "Pontuação anti-monotonia (0-100)",
      reference: "70+ = ótima variação",
    },
  },
  fillers: {
    fillers_per_minute: {
      label: "Vícios de linguagem por minuto",
      reference: "Meta: < 3/min",
    },
    hesitacoes_per_minute: {
      label: "Hesitações por minuto",
      reference: "< 2/min ideal",
    },
    total_fillers: { label: "Total de vícios de linguagem" },
    total_clusters: { label: "Problemas de fluência", reference: "0 = ideal" },
    type_token_ratio: {
      label: "Riqueza de vocabulário",
      reference: "0.5+ = bom vocabulário",
    },
  },
  posture: {
    alignment_score: { label: "Alinhamento postural (0-100)" },
    open_posture_pct: { label: "% postura aberta" },
    ombros_nivelados_pct: { label: "% ombros nivelados" },
    grounding_score: {
      label: "Estabilidade corporal (0-100)",
      reference: "Base firme = força",
    },
    proposital_score: { label: "Movimento proposital (0-100)" },
    padrao_movimento: { label: "Padrão de movimento" },
  },
  gesture: {
    eye_contact_pct: { label: "% contato visual" },
    olhar_baixo_pct: { label: "% olhar para baixo", reference: "< 10% ideal" },
    gesticulation_pct: { label: "% tempo gesticulando" },
    duas_maos_pct: {
      label: "% gestos com duas mãos",
      reference: "30%+ = mais expressivo",
    },
    vocabulario_gestos: {
      label: "Vocabulário de gestos",
      reference: "6+ posições = variado",
    },
    distribuicao_olhar: {
      label: "Distribuição do olhar",
      reference: "1.0 = bem distribuído",
    },
  },
  variety: {
    diagnostico_geral: { label: "Diagnóstico geral" },
    pct_tempo_monotono: { label: "% tempo monótono", reference: "< 20% ideal" },
  },
  archetypes: {
    arquetipo_dominante: { label: "Arquétipo dominante" },
    pct_dominante: {
      label: "% no arquétipo dominante",
      reference: "< 50% = equilibrado",
    },
    num_arquetipos_usados: {
      label: "Arquétipos usados",
      reference: "4 = ideal",
    },
    trocas_por_minuto: { label: "Trocas por minuto", reference: "2-5 = ideal" },
    lock_in: { label: "Lock-in detectado", reference: "false = bom" },
  },
};

const SUB_SCORE_LABELS: Record<string, string> = {
  wpm_score: "Palavras por Minuto",
  wpm: "Palavras por Minuto",
  pausa_score: "Pausa",
  pausa: "Pausa",
  pitch_score: "Tom",
  pitch: "Tom",
  volume_score: "Volume",
  volume: "Volume",
  velocidade_score: "Velocidade",
  velocidade: "Velocidade",
  grounding: "Estabilidade Corporal",
  alinhamento: "Alinhamento",
  postura_aberta: "Postura Aberta",
  movimento_proposital: "Movimento Proposital",
  zona: "Zona",
  duas_maos: "Duas Mãos",
  gesticulacao: "Gesticulação",
  contato_visual: "Contato Visual",
  distribuicao_olhar: "Distribuição do Olhar",
  cycling: "Alternância",
  anti_lockin: "Anti Lock-in",
  diversidade: "Diversidade",
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
                  displayValue = String(value);
                }

                return (
                  <div
                    key={key}
                    className="flex items-center justify-between rounded-xl bg-surface-container-low p-4 ghost-border gap-4"
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-on-surface">
                        {def.label}
                      </p>
                      {def.reference && (
                        <p className="text-xs text-on-surface-variant mt-0.5">
                          {def.reference}
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
