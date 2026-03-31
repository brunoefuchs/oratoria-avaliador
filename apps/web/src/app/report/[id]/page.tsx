"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ScoreCard } from "@/components/score-card";
import { StarRating } from "@/components/star-rating";
import { fetchReport, submitRating } from "@/lib/api-client";

const DIMENSION_LABELS: Record<string, string> = {
  posture: "Postura",
  gesture: "Gestual",
  voice: "Tom de Voz",
  fillers: "Vicios de Linguagem",
};

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

  return (
    <main className="mx-auto max-w-2xl p-6 space-y-8">
      {/* Overall Score */}
      <div className="text-center space-y-2">
        <h1 className="text-2xl font-bold">Seu Relatorio de Oratoria</h1>
        <div className={`text-6xl font-bold ${overallColor}`}>
          {data.overall_score}
        </div>
        <p className="text-sm text-gray-500">Score geral (0-100)</p>
      </div>

      {/* Summary */}
      {data.report?.summary && (
        <div className="rounded-xl bg-gray-50 p-5">
          <p className="text-sm text-gray-700 leading-relaxed">
            {data.report.summary}
          </p>
        </div>
      )}

      {/* Dimension Cards */}
      <div className="grid grid-cols-2 gap-4">
        {Object.entries(data.dimension_scores || {}).map(
          ([dimension, score]) => {
            const feedback =
              data.report?.dimension_feedback?.[dimension];
            return (
              <ScoreCard
                key={dimension}
                title={DIMENSION_LABELS[dimension] || dimension}
                score={score as number}
                summary={feedback?.tip}
                onClick={() => router.push(`/report/${id}/${dimension}`)}
              />
            );
          }
        )}
      </div>

      {/* Incomplete dimensions warning */}
      {data.incomplete_dimensions?.length > 0 && (
        <div className="rounded-lg bg-yellow-50 p-4 text-sm text-yellow-700">
          Algumas dimensoes nao puderam ser analisadas:{" "}
          {data.incomplete_dimensions
            .map((d: string) => DIMENSION_LABELS[d] || d)
            .join(", ")}
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
