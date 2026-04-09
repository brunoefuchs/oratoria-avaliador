"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ScoreCard } from "@/components/score-card";
import { StarRating } from "@/components/star-rating";
import { fetchReport, submitRating } from "@/lib/api-client";

const DIMENSION_LABELS: Record<string, string> = {
  variety: "Variedade Vocal",
  voice: "Voz e Diccao",
  gesture: "Presenca Visual",
  posture: "Postura e Presenca",
  fillers: "Clareza Verbal",
};

// Ordem de exibicao das dimensoes (archetypes removido — extra a ser desbloqueado)
const DIMENSION_ORDER = ["variety", "voice", "gesture", "posture", "fillers"];

export default function ReportPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchReport(id)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <p className="text-gray-500">Carregando relatorio...</p>
      </main>
    );
  }

  if (error || !data) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-8">
        <p className="text-red-600">{error || "Relatorio nao encontrado"}</p>
        <button
          onClick={() => router.push("/")}
          className="rounded-lg bg-blue-600 px-6 py-2 text-white"
        >
          Voltar
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
  const dimensoes = report.dimensoes || report.dimension_feedback || {};
  const plano = report.plano_12_semanas || [];
  const mensagemFinal = report.mensagem_final || "";

  // Ordenar dimensoes conforme DIMENSION_ORDER
  const sortedDimensions = DIMENSION_ORDER.filter(
    (d) => d in (data.dimension_scores || {})
  );

  return (
    <main className="mx-auto max-w-2xl p-6 space-y-8">
      {/* Score Geral */}
      <div className="text-center space-y-2">
        <h1 className="text-2xl font-bold">Seu Relatorio de Oratoria</h1>
        <div className={`text-6xl font-bold ${overallColor}`}>
          {data.overall_score}
        </div>
        <p className="text-sm text-gray-500">Score geral (0-100)</p>
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
          <h2 className="text-lg font-semibold text-green-700">Seus Pontos Fortes</h2>
          <div className="space-y-2">
            {forcas.map((forca: any, i: number) => (
              <div key={i} className="rounded-xl bg-green-50 p-4 ring-1 ring-green-200">
                <p className="text-sm font-semibold text-green-800">
                  {forca.titulo}
                </p>
                <p className="mt-1 text-sm text-green-700">{forca.descricao}</p>
                {forca.impacto && (
                  <p className="mt-1 text-xs text-green-600 italic">{forca.impacto}</p>
                )}
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
              summary={feedback?.dica || feedback?.tip}
              onClick={() => router.push(`/report/${id}/${dimension}`)}
            />
          );
        })}
      </div>

      {/* Arquetipos Vocais — Extra bloqueado */}
      <div className="rounded-xl bg-gray-100 p-4 flex items-center gap-3 opacity-60">
        <span className="text-2xl">🔒</span>
        <div>
          <p className="text-sm font-semibold text-gray-500">Arquetipos Vocais</p>
          <p className="text-xs text-gray-400">Em breve — recurso avancado a ser desbloqueado</p>
        </div>
      </div>

      {/* Melhorias 80/20 */}
      {melhorias.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold text-amber-700">
            Top Melhorias (Regra 80/20)
          </h2>
          <p className="text-xs text-gray-500">
            As mudancas que vao gerar o maior impacto na sua comunicacao
          </p>
          <div className="space-y-3">
            {melhorias
              .sort((a: any, b: any) => (a.prioridade || 0) - (b.prioridade || 0))
              .map((melhoria: any, i: number) => (
                <details
                  key={i}
                  className="rounded-xl bg-amber-50 ring-1 ring-amber-200 overflow-hidden"
                >
                  <summary className="cursor-pointer p-4 text-sm font-semibold text-amber-800 hover:bg-amber-100">
                    <span className="mr-2 inline-flex h-5 w-5 items-center justify-center rounded-full bg-amber-200 text-xs font-bold text-amber-800">
                      {i + 1}
                    </span>
                    {melhoria.titulo}
                  </summary>
                  <div className="border-t border-amber-200 p-4 space-y-2">
                    <p className="text-sm text-amber-700">{melhoria.descricao}</p>
                    {melhoria.exercicio && (
                      <div className="rounded-lg bg-white p-3">
                        <p className="text-xs font-semibold text-amber-600 uppercase">
                          Exercicio pratico
                        </p>
                        <p className="mt-1 text-sm text-gray-700">
                          {melhoria.exercicio}
                        </p>
                      </div>
                    )}
                  </div>
                </details>
              ))}
          </div>
        </div>
      )}

      {/* Plano de 12 Semanas */}
      {plano.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold text-blue-700">
            Seu Plano de 12 Semanas
          </h2>
          <p className="text-xs text-gray-500">
            Uma habilidade por semana. Grave, revise, ajuste.
          </p>
          <div className="space-y-2">
            {plano.map((item: any, i: number) => (
              <div
                key={i}
                className="flex gap-4 rounded-xl bg-blue-50 p-4 ring-1 ring-blue-200"
              >
                <div className="flex h-10 w-14 shrink-0 items-center justify-center rounded-lg bg-blue-200 text-xs font-bold text-blue-800">
                  Sem {item.semana}
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-blue-800">
                    {item.foco}
                  </p>
                  <p className="mt-1 text-xs text-blue-700 line-clamp-2">
                    {item.exercicio}
                  </p>
                  {item.meta && (
                    <p className="mt-1 text-xs text-blue-500 italic">
                      Meta: {item.meta}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Dimensoes incompletas */}
      {data.incomplete_dimensions?.length > 0 && (
        <div className="rounded-lg bg-yellow-50 p-4 text-sm text-yellow-700">
          Algumas dimensoes nao puderam ser analisadas:{" "}
          {data.incomplete_dimensions
            .map((d: string) => DIMENSION_LABELS[d] || d)
            .join(", ")}
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

      {/* Rating */}
      <div className="border-t pt-6">
        <StarRating
          onSubmit={(rating, comment) => submitRating(id, rating, comment)}
        />
      </div>
    </main>
  );
}
