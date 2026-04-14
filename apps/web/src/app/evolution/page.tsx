"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { fetchEvolution } from "@/lib/api-client";
import { AppShell } from "@/components/app-shell";

const DIMENSION_LABELS: Record<string, string> = {
  variety: "Variedade Vocal",
  voice: "Voz e Dicção",
  gesture: "Presença Visual",
  posture: "Postura e Presença",
  fillers: "Clareza Verbal",
};

function getScoreTone(score: number) {
  if (score >= 70) return "text-secondary";
  if (score >= 40) return "text-tertiary";
  return "text-error";
}

function getDeltaDisplay(delta: number) {
  if (delta > 0) return { text: `+${delta}%`, color: "text-secondary" };
  if (delta < 0) return { text: `${delta}%`, color: "text-error" };
  return { text: "0%", color: "text-on-surface-variant" };
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
      <AppShell maxWidth="lg" showBack backHref="/" backLabel="Início">
        <div className="min-h-[50vh] flex items-center justify-center">
          <p className="text-on-surface-variant text-sm">
            Carregando evolução...
          </p>
        </div>
      </AppShell>
    );
  }

  const evaluations = data?.evaluations || [];

  if (evaluations.length === 0) {
    return (
      <AppShell maxWidth="md" showBack backHref="/" backLabel="Início">
        <div className="min-h-[50vh] flex flex-col items-center justify-center gap-5 text-center">
          <div className="w-16 h-16 rounded-full bg-surface-container-high flex items-center justify-center ghost-border">
            <span className="material-symbols-outlined text-on-surface-variant text-3xl">
              timeline
            </span>
          </div>
          <div className="space-y-2">
            <h1 className="font-headline text-2xl md:text-3xl font-extrabold tracking-tight">
              Sua Evolução
            </h1>
            <p className="text-on-surface-variant">
              Você ainda não tem avaliações concluídas.
              <br />
              Envie seu primeiro vídeo!
            </p>
          </div>
          <button
            onClick={() => router.push("/")}
            className="bg-ai-pulse text-on-primary font-bold px-6 py-3 rounded-full shadow-cta-glow active:scale-95 transition"
          >
            Começar avaliação
          </button>
        </div>
      </AppShell>
    );
  }

  const first = evaluations[0];
  const last = evaluations[evaluations.length - 1];
  const overallDelta =
    evaluations.length > 1
      ? Math.round(
          ((last.overall_score - first.overall_score) /
            Math.max(1, first.overall_score)) *
            100
        )
      : 0;

  return (
    <AppShell maxWidth="lg" showBack backHref="/" backLabel="Início">
      <div className="space-y-10">
        <header className="space-y-3">
          <span className="font-label text-xs uppercase tracking-[0.3em] text-secondary/80">
            Sua trajetória
          </span>
          <h1 className="font-headline text-3xl md:text-5xl font-extrabold tracking-tight">
            Evolução
          </h1>
          <p className="text-on-surface-variant">
            {evaluations.length} avaliaç{evaluations.length > 1 ? "ões" : "ão"}{" "}
            concluíd{evaluations.length > 1 ? "as" : "a"}
          </p>
        </header>

        {/* Score geral hero */}
        {evaluations.length > 1 && (
          <section className="rounded-3xl bg-surface-container-low p-6 md:p-8 stage-ambient relative overflow-hidden">
            <span className="font-label text-xs uppercase tracking-[0.2em] text-on-surface-variant mb-4 block">
              Pontuação Geral
            </span>
            <div className="flex items-end gap-3 md:gap-5 flex-wrap mb-4">
              <span className="font-headline text-4xl md:text-5xl font-bold text-on-surface-variant/60">
                {first.overall_score}
              </span>
              <span className="text-outline text-xl pb-2">→</span>
              {evaluations.length > 2 &&
                evaluations.slice(1, -1).map((ev: any, i: number) => (
                  <span
                    key={i}
                    className="font-headline text-2xl md:text-3xl font-bold text-on-surface-variant/50"
                  >
                    {ev.overall_score} →
                  </span>
                ))}
              <span
                className={`font-headline text-5xl md:text-7xl font-extrabold ${getScoreTone(
                  last.overall_score
                )}`}
              >
                {last.overall_score}
              </span>
            </div>
            <div
              className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-semibold ghost-border ${
                overallDelta >= 0
                  ? "bg-secondary-container/20 text-secondary"
                  : "bg-error-container/20 text-error"
              }`}
            >
              <span className="material-symbols-outlined text-base">
                {overallDelta >= 0 ? "trending_up" : "trending_down"}
              </span>
              {overallDelta >= 0 ? "+" : ""}
              {overallDelta}% de evolução
            </div>
            <div className="absolute bottom-0 left-0 right-0 fluency-wave opacity-50" />
          </section>
        )}

        {/* Dimensoes delta */}
        {evaluations.length > 1 && (
          <section className="space-y-4">
            <h2 className="font-headline text-xl md:text-2xl font-bold tracking-tight">
              Evolução por Dimensão
            </h2>
            <div className="space-y-2">
              {Object.entries(DIMENSION_LABELS).map(([key, label]) => {
                const firstScore = first.dimension_scores?.[key] || 0;
                const lastScore = last.dimension_scores?.[key] || 0;
                const delta = lastScore - firstScore;
                const d = getDeltaDisplay(delta);
                return (
                  <div
                    key={key}
                    className="flex items-center justify-between rounded-xl bg-surface-container-low p-4 ghost-border"
                  >
                    <span className="text-sm font-medium text-on-surface">
                      {label}
                    </span>
                    <div className="flex items-center gap-3">
                      <span className="text-sm text-on-surface-variant/70 font-mono">
                        {firstScore}
                      </span>
                      <span className="text-outline">→</span>
                      <span
                        className={`text-base font-bold font-mono ${getScoreTone(
                          lastScore
                        )}`}
                      >
                        {lastScore}
                      </span>
                      <span
                        className={`text-xs font-semibold px-2 py-0.5 rounded-md ghost-border ${d.color}`}
                      >
                        {d.text}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {/* Histórico */}
        <section className="space-y-4">
          <h2 className="font-headline text-xl md:text-2xl font-bold tracking-tight">
            Histórico
          </h2>
          <div className="space-y-2">
            {evaluations.map((ev: any, i: number) => (
              <button
                key={ev.id}
                onClick={() => router.push(`/report/${ev.id}`)}
                className="group w-full flex items-center justify-between rounded-2xl bg-surface-container-low p-4 md:p-5 hover:bg-surface-container-high transition-colors ghost-border"
              >
                <div className="flex items-center gap-4 text-left min-w-0">
                  <div className="w-10 h-10 shrink-0 rounded-full bg-surface-container-highest flex items-center justify-center text-sm font-bold text-on-surface-variant ghost-border">
                    {i + 1}
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-on-surface">
                      Avaliação {i + 1}
                    </p>
                    <p className="text-xs text-on-surface-variant">
                      {new Date(ev.created_at).toLocaleDateString("pt-BR")}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span
                    className={`font-headline text-2xl md:text-3xl font-bold ${getScoreTone(
                      ev.overall_score
                    )}`}
                  >
                    {ev.overall_score}
                  </span>
                  <span className="material-symbols-outlined text-on-surface-variant opacity-0 group-hover:opacity-100 transition-opacity">
                    arrow_forward
                  </span>
                </div>
              </button>
            ))}
          </div>
        </section>
      </div>
    </AppShell>
  );
}
