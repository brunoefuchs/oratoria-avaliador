"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { fetchDimensionDetail } from "@/lib/api-client";

const DIMENSION_LABELS: Record<string, string> = {
  variety: "Variedade Vocal",
  voice: "Voz e Diccao",
  gesture: "Presenca Visual",
  posture: "Postura e Presenca",
  fillers: "Clareza Verbal",
  archetypes: "Arquetipos Vocais",
};

const METRIC_LABELS: Record<string, Record<string, { label: string; reference?: string }>> = {
  voice: {
    wpm: { label: "Palavras por minuto", reference: "Ideal: 130-170" },
    pitch_mean_hz: { label: "Tom medio (Hz)" },
    pitch_range_semitones: { label: "Variacao de tom (semitons)", reference: "10+ = expressivo" },
    intensity_mean_db: { label: "Volume medio (dB)" },
    cv_velocidade: { label: "Variacao de velocidade", reference: "0.08-0.30 = ideal" },
    monotonia_score: { label: "Pontuacao anti-monotonia (0-100)", reference: "70+ = otima variacao" },
  },
  fillers: {
    fillers_per_minute: { label: "Vicios de linguagem por minuto", reference: "Meta: < 3/min" },
    hesitacoes_per_minute: { label: "Hesitacoes por minuto", reference: "< 2/min ideal" },
    total_fillers: { label: "Total de vicios de linguagem" },
    total_clusters: { label: "Problemas de fluencia", reference: "0 = ideal" },
    type_token_ratio: { label: "Riqueza de vocabulario", reference: "0.5+ = bom vocabulario" },
  },
  posture: {
    alignment_score: { label: "Alinhamento postural (0-100)" },
    open_posture_pct: { label: "% postura aberta" },
    ombros_nivelados_pct: { label: "% ombros nivelados" },
    grounding_score: { label: "Estabilidade corporal (0-100)", reference: "Base firme = forca" },
    proposital_score: { label: "Movimento proposital (0-100)" },
    padrao_movimento: { label: "Padrao de movimento" },
  },
  gesture: {
    eye_contact_pct: { label: "% contato visual" },
    olhar_baixo_pct: { label: "% olhar para baixo", reference: "< 10% ideal" },
    gesticulation_pct: { label: "% tempo gesticulando" },
    duas_maos_pct: { label: "% gestos com duas maos", reference: "30%+ = mais expressivo" },
    vocabulario_gestos: { label: "Vocabulario de gestos", reference: "6+ posicoes = variado" },
    distribuicao_olhar: { label: "Distribuicao do olhar", reference: "1.0 = bem distribuido" },
  },
  variety: {
    diagnostico_geral: { label: "Diagnostico geral" },
    pct_tempo_monotono: { label: "% tempo monotono", reference: "< 20% ideal" },
  },
  archetypes: {
    arquetipo_dominante: { label: "Arquetipo dominante" },
    pct_dominante: { label: "% no arquetipo dominante", reference: "< 50% = equilibrado" },
    num_arquetipos_usados: { label: "Arquetipos usados", reference: "4 = ideal" },
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
  duas_maos: "Duas Maos",
  gesticulacao: "Gesticulacao",
  contato_visual: "Contato Visual",
  distribuicao_olhar: "Distribuicao do Olhar",
  cycling: "Alternancia",
  anti_lockin: "Anti Lock-in",
  diversidade: "Diversidade",
};

const ARCHETYPE_LABELS: Record<string, string> = {
  educador: "Educador",
  coach: "Coach",
  motivador: "Motivador",
  amigo: "Amigo",
};

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
      <main className="flex min-h-screen items-center justify-center">
        <p className="text-gray-500">Carregando...</p>
      </main>
    );
  }

  if (!data) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <p className="text-red-600">Dimensao nao encontrada</p>
      </main>
    );
  }

  const scoreColor =
    data.score >= 70 ? "text-green-600" : data.score >= 40 ? "text-yellow-600" : "text-red-600";
  const metricDefs = METRIC_LABELS[dimension] || {};
  const feedback = data.feedback || {};
  const metrics = data.metrics || {};

  return (
    <main className="mx-auto max-w-xl p-6 space-y-6">
      <button
        onClick={() => router.push(`/report/${id}`)}
        className="text-sm text-blue-600 hover:underline"
      >
        ← Voltar ao dashboard
      </button>

      <div className="text-center space-y-2">
        <h1 className="text-xl font-bold">
          {DIMENSION_LABELS[dimension] || dimension}
        </h1>
        <div className={`text-5xl font-bold ${scoreColor}`}>{data.score}</div>
        {feedback.label && (
          <p className="text-sm text-gray-500">{feedback.label}</p>
        )}
        {feedback.score_label && (
          <p className="text-sm text-gray-500">{feedback.score_label}</p>
        )}
      </div>

      {data.confidence === "low" && (
        <div className="rounded-lg bg-yellow-50 p-3 text-sm text-yellow-700">
          Confianca baixa — qualidade do video pode ter afetado a analise.
        </div>
      )}

      {/* Metricas */}
      <div className="space-y-3">
        <h2 className="text-sm font-semibold text-gray-500 uppercase">Metricas</h2>
        {Object.entries(metrics).map(([key, value]) => {
          const def = metricDefs[key];
          if (!def) return null;

          let displayValue: string;
          if (typeof value === "boolean") {
            displayValue = value ? "Sim" : "Nao";
          } else if (typeof value === "number") {
            displayValue = String(Math.round(value * 100) / 100);
          } else {
            displayValue = String(value);
          }

          return (
            <div key={key} className="flex items-center justify-between rounded-lg bg-gray-50 p-3">
              <div>
                <p className="text-sm font-medium">{def.label}</p>
                {def.reference && (
                  <p className="text-xs text-gray-400">{def.reference}</p>
                )}
              </div>
              <span className="text-lg font-semibold">{displayValue}</span>
            </div>
          );
        })}
      </div>

      {/* Sub-scores */}
      {metrics.sub_scores && (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-gray-500 uppercase">Pontuacoes</h2>
          <div className="space-y-2">
            {Object.entries(metrics.sub_scores as Record<string, number>).map(([key, value]) => (
              <div key={key} className="space-y-1">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600 capitalize">
                    {SUB_SCORE_LABELS[key] || key.replace(/_/g, " ")}
                  </span>
                  <span className="font-medium">{value}</span>
                </div>
                <div className="h-2 rounded-full bg-gray-200">
                  <div
                    className={`h-2 rounded-full transition-all ${
                      value >= 70 ? "bg-green-500" : value >= 40 ? "bg-yellow-500" : "bg-red-500"
                    }`}
                    style={{ width: `${Math.min(100, value)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Distribuicao de arquetipos */}
      {dimension === "archetypes" && metrics.distribuicao && (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-gray-500 uppercase">
            Distribuicao de Arquetipos
          </h2>
          <div className="space-y-2">
            {Object.entries(metrics.distribuicao as Record<string, number>)
              .sort(([, a], [, b]) => b - a)
              .map(([arq, pct]) => (
                <div key={arq} className="space-y-1">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">
                      {ARCHETYPE_LABELS[arq] || arq}
                    </span>
                    <span className="font-medium">{pct}%</span>
                  </div>
                  <div className="h-3 rounded-full bg-gray-200">
                    <div
                      className="h-3 rounded-full bg-purple-500 transition-all"
                      style={{ width: `${Math.min(100, pct)}%` }}
                    />
                  </div>
                </div>
              ))}
          </div>
          {metrics.acessiveis && (
            <p className="text-xs text-green-600">
              Acessiveis: {(metrics.acessiveis as string[]).map(a => ARCHETYPE_LABELS[a] || a).join(", ")}
            </p>
          )}
          {metrics.ausentes && (metrics.ausentes as string[]).length > 0 && (
            <p className="text-xs text-amber-600">
              Ausentes: {(metrics.ausentes as string[]).map(a => ARCHETYPE_LABELS[a] || a).join(", ")}
            </p>
          )}
        </div>
      )}

      {/* Variedade — dimensoes detalhadas */}
      {dimension === "variety" && metrics.dimensoes && (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-gray-500 uppercase">
            Variacao por Dimensao
          </h2>
          {Object.entries(metrics.dimensoes as Record<string, any>).map(([key, dim]: [string, any]) => (
            <div key={key} className="rounded-lg bg-gray-50 p-3 space-y-1">
              <div className="flex justify-between text-sm">
                <span className="font-medium capitalize">{key}</span>
                <span className={`font-semibold ${
                  dim.score >= 70 ? "text-green-600" : dim.score >= 40 ? "text-yellow-600" : "text-red-600"
                }`}>
                  {dim.score}
                </span>
              </div>
              <p className="text-xs text-gray-500 capitalize">
                {dim.diagnostico?.replace(/_/g, " ")}
              </p>
              <div className="h-2 rounded-full bg-gray-200">
                <div
                  className={`h-2 rounded-full ${
                    dim.score >= 70 ? "bg-green-500" : dim.score >= 40 ? "bg-yellow-500" : "bg-red-500"
                  }`}
                  style={{ width: `${Math.min(100, dim.score)}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Defaults detectados */}
      {dimension === "variety" && metrics.defaults_detectados && (metrics.defaults_detectados as string[]).length > 0 && (
        <div className="rounded-lg bg-amber-50 p-4 ring-1 ring-amber-200">
          <p className="text-sm font-semibold text-amber-800">Padroes detectados</p>
          <p className="mt-1 text-sm text-amber-700">
            Pilares travados: {(metrics.defaults_detectados as string[]).join(", ")}
          </p>
          <p className="mt-1 text-xs text-amber-600 italic">
            &ldquo;Sempre que algo se torna padrao, se torna nao-funcional.&rdquo;
          </p>
        </div>
      )}

      {/* Feedback v2 (label + feedback + dica) */}
      {feedback.feedback && (
        <div className="space-y-3">
          <div className="rounded-xl bg-gray-50 p-4">
            <p className="text-sm text-gray-700 leading-relaxed">{feedback.feedback}</p>
          </div>
          {feedback.dica && (
            <div className="rounded-lg bg-blue-50 p-4">
              <p className="text-sm font-medium text-blue-800">Dica pratica</p>
              <p className="mt-1 text-sm text-blue-700">{feedback.dica}</p>
            </div>
          )}
        </div>
      )}

      {/* Feedback v1 retrocompativel (strengths + improvements + tip) */}
      {!feedback.feedback && feedback.strengths && (
        <div className="space-y-3">
          <div>
            <h2 className="text-sm font-semibold text-green-600">Pontos Fortes</h2>
            <ul className="mt-1 space-y-1">
              {feedback.strengths.map((s: string, i: number) => (
                <li key={i} className="text-sm text-gray-700">✓ {s}</li>
              ))}
            </ul>
          </div>

          <div>
            <h2 className="text-sm font-semibold text-yellow-600">Melhorias</h2>
            <ul className="mt-1 space-y-1">
              {feedback.improvements?.map((s: string, i: number) => (
                <li key={i} className="text-sm text-gray-700">→ {s}</li>
              ))}
            </ul>
          </div>

          {feedback.tip && (
            <div className="rounded-lg bg-blue-50 p-4">
              <p className="text-sm font-medium text-blue-800">Dica</p>
              <p className="mt-1 text-sm text-blue-700">{feedback.tip}</p>
            </div>
          )}
        </div>
      )}

      {/* Top fillers (dimensao fillers) */}
      {dimension === "fillers" && metrics.top_fillers && (
        <div>
          <h2 className="text-sm font-semibold text-gray-500 uppercase">Principais Vicios de Linguagem</h2>
          <div className="mt-2 space-y-1">
            {(metrics.top_fillers as any[]).map((f: any, i: number) => (
              <div key={i} className="flex justify-between rounded bg-gray-50 px-3 py-2 text-sm">
                <span>&ldquo;{f.word}&rdquo;</span>
                <span className="font-medium">{f.count}x</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Clusters de fillers */}
      {dimension === "fillers" && metrics.clusters && (metrics.clusters as any[]).length > 0 && (
        <div className="rounded-lg bg-red-50 p-4 ring-1 ring-red-200">
          <p className="text-sm font-semibold text-red-800">
            Problemas de fluencia detectados ({(metrics.clusters as any[]).length})
          </p>
          <p className="text-xs text-red-600 mt-1">
            Momentos com 3+ vicios de linguagem em sequencia rapida
          </p>
        </div>
      )}

      {/* Pausas (dimensao voice) */}
      {dimension === "voice" && metrics.pausas && (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-gray-500 uppercase">Pausas</h2>
          <div className="grid grid-cols-3 gap-2">
            <div className="rounded-lg bg-green-50 p-3 text-center">
              <p className="text-lg font-bold text-green-700">{metrics.pausas.qtd_estrategicas}</p>
              <p className="text-xs text-green-600">Estrategicas</p>
            </div>
            <div className="rounded-lg bg-amber-50 p-3 text-center">
              <p className="text-lg font-bold text-amber-700">{metrics.pausas.qtd_hesitacao}</p>
              <p className="text-xs text-amber-600">Hesitacao</p>
            </div>
            <div className="rounded-lg bg-gray-50 p-3 text-center">
              <p className="text-lg font-bold text-gray-700">{metrics.pausas.qtd_respiracao}</p>
              <p className="text-xs text-gray-600">Respiracao</p>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
