"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { fetchDimensionDetail } from "@/lib/api-client";

const DIMENSION_LABELS: Record<string, string> = {
  posture: "Postura",
  gesture: "Gestual",
  voice: "Tom de Voz",
  fillers: "Vicios de Linguagem",
};

const METRIC_LABELS: Record<string, Record<string, { label: string; reference?: string }>> = {
  voice: {
    wpm: { label: "Palavras por minuto", reference: "Ideal: 130-170" },
    pitch_mean_hz: { label: "Pitch medio (Hz)" },
    pitch_range_semitones: { label: "Variacao de pitch (semitons)", reference: "Maior = mais expressivo" },
    intensity_mean_db: { label: "Volume medio (dB)" },
    speech_silence_ratio: { label: "Razao fala/silencio", reference: "0.7-0.85 ideal" },
  },
  fillers: {
    fillers_per_minute: { label: "Fillers por minuto", reference: "Meta: < 3/min" },
    total_fillers: { label: "Total de fillers" },
    type_token_ratio: { label: "Diversidade lexical", reference: "Maior = vocabulario mais variado" },
  },
  posture: {
    alignment_score: { label: "Alinhamento postural (0-100)" },
    open_posture_pct: { label: "% postura aberta" },
    stability_score: { label: "Estabilidade (0-100)" },
  },
  gesture: {
    gesticulation_pct: { label: "% tempo gesticulando" },
    above_waist_pct: { label: "% gestos acima da cintura" },
    eye_contact_pct: { label: "% contato visual" },
  },
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
        {feedback.score_label && (
          <p className="text-sm text-gray-500">{feedback.score_label}</p>
        )}
      </div>

      {data.confidence === "low" && (
        <div className="rounded-lg bg-yellow-50 p-3 text-sm text-yellow-700">
          Confianca baixa — qualidade do video pode ter afetado a analise.
        </div>
      )}

      {/* Metrics */}
      <div className="space-y-3">
        <h2 className="text-sm font-semibold text-gray-500 uppercase">Metricas</h2>
        {Object.entries(data.metrics || {}).map(([key, value]) => {
          const def = metricDefs[key];
          if (!def) return null;
          return (
            <div key={key} className="flex items-center justify-between rounded-lg bg-gray-50 p-3">
              <div>
                <p className="text-sm font-medium">{def.label}</p>
                {def.reference && (
                  <p className="text-xs text-gray-400">{def.reference}</p>
                )}
              </div>
              <span className="text-lg font-semibold">
                {typeof value === "number" ? Math.round(value * 10) / 10 : String(value)}
              </span>
            </div>
          );
        })}
      </div>

      {/* Feedback */}
      {feedback.strengths && (
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
              <p className="text-sm font-medium text-blue-800">💡 Dica</p>
              <p className="mt-1 text-sm text-blue-700">{feedback.tip}</p>
            </div>
          )}
        </div>
      )}

      {/* Top fillers list (fillers dimension only) */}
      {dimension === "fillers" && data.metrics?.top_fillers && (
        <div>
          <h2 className="text-sm font-semibold text-gray-500 uppercase">Top Fillers</h2>
          <div className="mt-2 space-y-1">
            {data.metrics.top_fillers.map((f: any, i: number) => (
              <div key={i} className="flex justify-between rounded bg-gray-50 px-3 py-2 text-sm">
                <span>&ldquo;{f.word}&rdquo;</span>
                <span className="font-medium">{f.count}x</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </main>
  );
}
