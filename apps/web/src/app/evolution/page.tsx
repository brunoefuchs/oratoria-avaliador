"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { fetchEvolution } from "@/lib/api-client";

const DIMENSION_LABELS: Record<string, string> = {
  variety: "Variedade Vocal",
  voice: "Voz e Diccao",
  gesture: "Presenca Visual",
  posture: "Postura e Presenca",
  fillers: "Clareza Verbal",
};

function getScoreColor(score: number) {
  if (score >= 70) return "text-green-600";
  if (score >= 40) return "text-yellow-600";
  return "text-red-600";
}

function getDeltaDisplay(delta: number) {
  if (delta > 0) return { text: `+${delta}%`, color: "text-green-600" };
  if (delta < 0) return { text: `${delta}%`, color: "text-red-600" };
  return { text: "0%", color: "text-gray-400" };
}

export default function EvolutionPage() {
  const router = useRouter();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const userToken = localStorage.getItem("oratoria_user_token");
    if (!userToken) {
      setLoading(false);
      return;
    }
    fetchEvolution(userToken)
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <p className="text-gray-500">Carregando evolucao...</p>
      </main>
    );
  }

  const evaluations = data?.evaluations || [];

  if (evaluations.length === 0) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-8">
        <h1 className="text-2xl font-bold">Sua Evolucao</h1>
        <p className="text-gray-500">
          Voce ainda nao tem avaliacoes concluidas. Envie seu primeiro video!
        </p>
        <button
          onClick={() => router.push("/")}
          className="rounded-lg bg-blue-600 px-6 py-2 text-white"
        >
          Comecar avaliacao
        </button>
      </main>
    );
  }

  const first = evaluations[0];
  const last = evaluations[evaluations.length - 1];
  const overallDelta =
    evaluations.length > 1
      ? Math.round(((last.overall_score - first.overall_score) / Math.max(1, first.overall_score)) * 100)
      : 0;

  return (
    <main className="mx-auto max-w-2xl p-6 space-y-8">
      <button
        onClick={() => router.push("/")}
        className="text-sm text-blue-600 hover:underline"
      >
        ← Voltar
      </button>

      <div className="text-center space-y-2">
        <h1 className="text-2xl font-bold">Sua Evolucao</h1>
        <p className="text-sm text-gray-500">
          {evaluations.length} avaliacao{evaluations.length > 1 ? "es" : ""} concluida{evaluations.length > 1 ? "s" : ""}
        </p>
      </div>

      {/* Score geral ao longo do tempo */}
      {evaluations.length > 1 && (
        <div className="rounded-xl bg-gradient-to-r from-blue-50 to-green-50 p-6 text-center space-y-2">
          <p className="text-sm text-gray-600">Pontuacao geral</p>
          <div className="flex items-center justify-center gap-3 text-3xl font-bold">
            <span className="text-gray-400">{first.overall_score}</span>
            <span className="text-gray-300">→</span>
            {evaluations.length > 2 &&
              evaluations.slice(1, -1).map((ev: any, i: number) => (
                <span key={i} className="text-gray-400 text-xl">
                  {ev.overall_score} →
                </span>
              ))}
            <span className={getScoreColor(last.overall_score)}>
              {last.overall_score}
            </span>
          </div>
          <p className={`text-lg font-semibold ${overallDelta >= 0 ? "text-green-600" : "text-red-600"}`}>
            {overallDelta >= 0 ? "+" : ""}
            {overallDelta}% de evolucao
          </p>
        </div>
      )}

      {/* Dimensoes — delta entre primeira e ultima */}
      {evaluations.length > 1 && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold">Evolucao por Dimensao</h2>
          <div className="space-y-2">
            {Object.entries(DIMENSION_LABELS).map(([key, label]) => {
              const firstScore = first.dimension_scores?.[key] || 0;
              const lastScore = last.dimension_scores?.[key] || 0;
              const delta = lastScore - firstScore;
              const d = getDeltaDisplay(delta);
              return (
                <div key={key} className="flex items-center justify-between rounded-lg bg-gray-50 p-3">
                  <span className="text-sm font-medium">{label}</span>
                  <div className="flex items-center gap-3">
                    <span className="text-sm text-gray-400">{firstScore}</span>
                    <span className="text-gray-300">→</span>
                    <span className={`text-sm font-semibold ${getScoreColor(lastScore)}`}>
                      {lastScore}
                    </span>
                    <span className={`text-xs font-medium ${d.color}`}>{d.text}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Lista de avaliacoes */}
      <div className="space-y-3">
        <h2 className="text-lg font-semibold">Historico</h2>
        <div className="space-y-2">
          {evaluations.map((ev: any, i: number) => (
            <button
              key={ev.id}
              onClick={() => router.push(`/report/${ev.id}`)}
              className="w-full flex items-center justify-between rounded-lg bg-gray-50 p-4 hover:bg-gray-100 transition-colors"
            >
              <div className="text-left">
                <p className="text-sm font-medium">Avaliacao {i + 1}</p>
                <p className="text-xs text-gray-400">
                  {new Date(ev.created_at).toLocaleDateString("pt-BR")}
                </p>
              </div>
              <span className={`text-xl font-bold ${getScoreColor(ev.overall_score)}`}>
                {ev.overall_score}
              </span>
            </button>
          ))}
        </div>
      </div>
    </main>
  );
}
