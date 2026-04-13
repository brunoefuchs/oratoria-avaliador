"use client";

import { useSearchParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { fetchSharedReport } from "@/lib/api-client";
import { ScoreCard } from "@/components/score-card";

const DIMENSION_LABELS: Record<string, string> = {
  variety: "Variedade Vocal",
  voice: "Voz e Diccao",
  gesture: "Presenca Visual",
  posture: "Postura e Presenca",
  fillers: "Clareza Verbal",
};

const DIMENSION_ORDER = ["variety", "voice", "gesture", "posture", "fillers"];

export default function SharedReportPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      setError("Link invalido — token ausente");
      setLoading(false);
      return;
    }
    fetchSharedReport(token)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [token]);

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <p className="text-gray-500">Carregando relatorio compartilhado...</p>
      </main>
    );
  }

  if (error || !data) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-8">
        <p className="text-red-600">{error || "Relatorio nao encontrado ou link expirado"}</p>
        <button
          onClick={() => router.push("/")}
          className="rounded-lg bg-blue-600 px-6 py-2 text-white"
        >
          Ir para inicio
        </button>
      </main>
    );
  }

  const overallColor =
    data.overall_score >= 70
      ? "text-green-600"
      : data.overall_score >= 40
        ? "text-yellow-600"
        : "text-red-600";

  const report = data.report || {};
  const resumo = report.resumo || report.summary || "";
  const forcas = report.forcas || [];
  const melhorias = report.melhorias_80_20 || [];
  const dimensoes = report.dimensoes || {};
  const plano = report.plano_12_semanas || [];
  const mensagemFinal = report.mensagem_final || "";

  const sortedDimensions = DIMENSION_ORDER.filter(
    (d) => d in (data.dimension_scores || {})
  );

  return (
    <main className="mx-auto max-w-2xl p-6 space-y-8">
      <div className="rounded-lg bg-blue-50 p-3 text-center text-xs text-blue-700">
        Relatorio compartilhado — modo somente leitura
      </div>

      {/* Score Geral */}
      <div className="text-center space-y-2">
        <h1 className="text-2xl font-bold">Relatorio de Oratoria</h1>
        <div className={`text-6xl font-bold ${overallColor}`}>
          {data.overall_score}
        </div>
        <p className="text-sm text-gray-500">Pontuacao geral (0-100)</p>
      </div>

      {/* Resumo */}
      {resumo && (
        <div className="rounded-xl bg-gray-50 p-5">
          <p className="text-sm text-gray-700 leading-relaxed">{resumo}</p>
        </div>
      )}

      {/* Forcas */}
      {forcas.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold text-green-700">Pontos Fortes</h2>
          <div className="space-y-2">
            {forcas.map((forca: any, i: number) => (
              <div key={i} className="rounded-xl bg-green-50 p-4 ring-1 ring-green-200">
                <p className="text-sm font-semibold text-green-800">
                  {forca.titulo}
                </p>
                <p className="mt-1 text-sm text-green-700">{forca.descricao}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Dimension Cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        {sortedDimensions.map((dimension) => {
          const score = data.dimension_scores[dimension] as number;
          const feedback = dimensoes[dimension];
          return (
            <ScoreCard
              key={dimension}
              title={DIMENSION_LABELS[dimension] || dimension}
              dimensionKey={dimension}
              score={score}
              summary={feedback?.dica}
            />
          );
        })}
      </div>

      {/* Melhorias 80/20 */}
      {melhorias.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold text-amber-700">Top Melhorias</h2>
          <div className="space-y-3">
            {melhorias.map((melhoria: any, i: number) => (
              <div key={i} className="rounded-xl bg-amber-50 p-4 ring-1 ring-amber-200">
                <p className="text-sm font-semibold text-amber-800">
                  {i + 1}. {melhoria.titulo}
                </p>
                <p className="mt-1 text-sm text-amber-700">{melhoria.descricao}</p>
                {melhoria.exercicio && (
                  <p className="mt-2 text-xs text-amber-600 italic">
                    Exercicio: {melhoria.exercicio}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Plano 12 semanas */}
      {plano.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold text-blue-700">Plano de 12 Semanas</h2>
          <div className="space-y-2">
            {plano.map((item: any, i: number) => (
              <div key={i} className="rounded-xl bg-blue-50 p-4 ring-1 ring-blue-200">
                <p className="text-sm font-semibold text-blue-800">
                  Semana {item.semana}: {item.foco}
                </p>
                <p className="mt-1 text-xs text-blue-700">{item.exercicio}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Mensagem Final */}
      {mensagemFinal && (
        <div className="rounded-xl bg-gradient-to-r from-purple-50 to-blue-50 p-6 ring-1 ring-purple-200">
          <p className="text-sm leading-relaxed text-gray-700 italic">
            &ldquo;{mensagemFinal}&rdquo;
          </p>
        </div>
      )}
    </main>
  );
}
