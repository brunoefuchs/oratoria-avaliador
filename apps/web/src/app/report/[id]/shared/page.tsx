"use client";

import { useSearchParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { fetchSharedReport } from "@/lib/api-client";
import { ScoreCard } from "@/components/score-card";
import { AppShell } from "@/components/app-shell";

const DIMENSION_LABELS: Record<string, string> = {
  variety: "Variedade Vocal",
  voice: "Voz e Dicção",
  gesture: "Presença Visual",
  posture: "Postura e Presença",
  fillers: "Clareza Verbal",
  facial: "Expressão Facial",
};

const DIMENSION_ORDER = ["variety", "voice", "gesture", "facial", "posture", "fillers"];

function getScoreTone(score: number) {
  if (score >= 70) return "text-secondary";
  if (score >= 40) return "text-tertiary";
  return "text-error";
}

export default function SharedReportPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      setError("Link inválido — token ausente");
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
      <AppShell maxWidth="lg">
        <div className="min-h-[50vh] flex items-center justify-center">
          <p className="text-on-surface-variant text-sm">
            Carregando relatório compartilhado...
          </p>
        </div>
      </AppShell>
    );
  }

  if (error || !data) {
    return (
      <AppShell maxWidth="md">
        <div className="min-h-[40vh] flex flex-col items-center justify-center gap-4 text-center">
          <span className="material-symbols-outlined text-error text-5xl">
            link_off
          </span>
          <p className="text-error">
            {error || "Relatório não encontrado ou link expirado"}
          </p>
          <button
            onClick={() => router.push("/")}
            className="bg-ai-pulse text-on-primary font-bold px-6 py-3 rounded-full shadow-cta-glow active:scale-95 transition"
          >
            Ir para início
          </button>
        </div>
      </AppShell>
    );
  }

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
    <AppShell maxWidth="2xl">
      <div className="space-y-10">
        <div className="rounded-xl bg-surface-container-low p-3 text-center text-xs text-on-surface-variant ghost-border flex items-center justify-center gap-2">
          <span className="material-symbols-outlined text-secondary text-base">
            visibility
          </span>
          Relatório compartilhado — modo somente leitura
        </div>

        {/* Score hero */}
        <section className="rounded-3xl bg-surface-container-low p-6 md:p-10 stage-ambient relative overflow-hidden text-center">
          <span className="font-label text-xs uppercase tracking-[0.3em] text-secondary/80">
            Relatório de oratória
          </span>
          <div className="mt-4 flex items-baseline justify-center gap-2">
            <span
              className={`font-headline text-6xl md:text-8xl font-extrabold ${getScoreTone(
                data.overall_score
              )}`}
            >
              {data.overall_score}
            </span>
            <span className="text-on-surface-variant text-2xl">/100</span>
          </div>
          <p className="mt-2 text-sm text-on-surface-variant">
            Pontuação geral
          </p>
          {resumo && (
            <p className="mt-6 text-on-surface-variant leading-relaxed max-w-2xl mx-auto">
              {resumo}
            </p>
          )}
          <div className="absolute bottom-0 left-0 right-0 fluency-wave opacity-50" />
        </section>

        {/* Forças */}
        {forcas.length > 0 && (
          <section className="space-y-4">
            <div className="flex items-center gap-3">
              <span className="material-symbols-outlined text-secondary text-2xl">
                bolt
              </span>
              <h2 className="font-headline text-2xl md:text-3xl font-bold tracking-tight">
                Pontos Fortes
              </h2>
            </div>
            <div className="grid md:grid-cols-2 gap-3">
              {forcas.map((forca: any, i: number) => (
                <article
                  key={i}
                  className="rounded-2xl bg-surface-container-low p-5 ghost-border"
                >
                  <p className="font-headline text-lg font-bold text-on-surface">
                    {forca.titulo}
                  </p>
                  <p className="mt-2 text-sm text-on-surface-variant leading-relaxed">
                    {forca.descricao}
                  </p>
                </article>
              ))}
            </div>
          </section>
        )}

        {/* Dimensões */}
        <section className="space-y-4">
          <div className="flex items-center gap-3">
            <span className="material-symbols-outlined text-secondary text-2xl">
              analytics
            </span>
            <h2 className="font-headline text-2xl md:text-3xl font-bold tracking-tight">
              Dimensões
            </h2>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 md:gap-4">
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
        </section>

        {/* Melhorias */}
        {melhorias.length > 0 && (
          <section className="space-y-4">
            <div className="flex items-center gap-3">
              <span className="material-symbols-outlined text-tertiary text-2xl">
                target
              </span>
              <h2 className="font-headline text-2xl md:text-3xl font-bold tracking-tight">
                Top Melhorias
              </h2>
            </div>
            <div className="space-y-3">
              {melhorias.map((melhoria: any, i: number) => (
                <article
                  key={i}
                  className="rounded-2xl bg-surface-container-low p-5 ghost-border"
                >
                  <div className="flex items-start gap-4">
                    <div className="w-9 h-9 rounded-xl bg-ai-pulse text-on-primary font-headline font-bold flex items-center justify-center shrink-0 shadow-cta-glow">
                      {i + 1}
                    </div>
                    <div className="flex-1 min-w-0 space-y-2">
                      <p className="font-headline text-lg font-bold text-on-surface">
                        {melhoria.titulo}
                      </p>
                      <p className="text-sm text-on-surface-variant leading-relaxed">
                        {melhoria.descricao}
                      </p>
                      {melhoria.exercicio && (
                        <div className="rounded-xl bg-surface-container-high p-3 ghost-border">
                          <p className="font-label text-[10px] uppercase tracking-[0.2em] text-tertiary">
                            Exercício
                          </p>
                          <p className="mt-1 text-sm text-on-surface leading-relaxed">
                            {melhoria.exercicio}
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                </article>
              ))}
            </div>
          </section>
        )}

        {/* Plano 12 semanas */}
        {plano.length > 0 && (
          <section className="space-y-4">
            <div className="flex items-center gap-3">
              <span className="material-symbols-outlined text-secondary text-2xl">
                event_note
              </span>
              <h2 className="font-headline text-2xl md:text-3xl font-bold tracking-tight">
                Plano de 12 Semanas
              </h2>
            </div>
            <div className="grid md:grid-cols-2 gap-3">
              {plano.map((item: any, i: number) => (
                <div
                  key={i}
                  className="flex gap-4 rounded-2xl bg-surface-container-low p-4 ghost-border"
                >
                  <div className="flex flex-col items-center justify-center min-w-[56px] rounded-xl bg-surface-container-high px-2 py-2 text-xs font-bold text-secondary ghost-border">
                    <span className="font-label uppercase tracking-[0.15em] text-[9px] text-on-surface-variant">
                      Sem
                    </span>
                    <span className="font-headline text-lg">
                      {item.semana}
                    </span>
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-semibold text-on-surface">
                      {item.foco}
                    </p>
                    <p className="mt-1 text-xs text-on-surface-variant leading-relaxed">
                      {item.exercicio}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Mensagem final */}
        {mensagemFinal && (
          <section className="rounded-3xl bg-surface-container-high p-6 md:p-8 ghost-border relative overflow-hidden">
            <span className="material-symbols-outlined text-tertiary text-4xl mb-3 opacity-50">
              format_quote
            </span>
            <p className="font-headline text-lg md:text-xl leading-relaxed text-on-surface italic">
              &ldquo;{mensagemFinal}&rdquo;
            </p>
          </section>
        )}
      </div>
    </AppShell>
  );
}
