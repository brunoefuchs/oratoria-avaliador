"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { fetchReport } from "@/lib/api-client";
import type { OpeningData } from "@/lib/types/report";

function getTone(score: number) {
  if (score >= 70) return { accent: "text-secondary", bar: "bg-secondary" };
  if (score >= 40) return { accent: "text-tertiary", bar: "bg-tertiary" };
  return { accent: "text-error", bar: "bg-error" };
}

export default function OpeningDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const [data, setData] = useState<OpeningData | null | undefined>(undefined);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchReport(id)
      .then((report) => setData(report?.detailed_metrics?.opening ?? null))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <AppShell maxWidth="lg" showBack backHref={`/report/${id}`} backLabel="Voltar ao relatório">
        <div className="min-h-[40vh] flex items-center justify-center">
          <p className="text-on-surface-variant text-sm">Carregando...</p>
        </div>
      </AppShell>
    );
  }

  if (!data || !data.disponivel) {
    return (
      <AppShell maxWidth="lg" showBack backHref={`/report/${id}`} backLabel="Voltar ao relatório">
        <div className="min-h-[40vh] flex items-center justify-center text-center">
          <div>
            <p className="text-on-surface mb-2">Análise de abertura indisponível</p>
            <p className="text-xs text-on-surface-variant">
              O vídeo pode ser muito curto ou não ter sinais suficientes nos primeiros 20%.
            </p>
          </div>
        </div>
      </AppShell>
    );
  }

  const tone = getTone(data.score);

  return (
    <AppShell maxWidth="lg" showBack backHref={`/report/${id}`} backLabel="Voltar ao relatório">
      <div className="space-y-8">
        <header className="flex items-start justify-between gap-6">
          <div>
            <span className="font-label text-xs uppercase tracking-[0.3em] text-on-surface-variant">
              Primeiros {Math.round(data.opening_duration_seconds)}s · Análise completa
            </span>
            <h1 className="font-headline text-3xl md:text-4xl font-extrabold mt-2">
              Sua Abertura
            </h1>
          </div>
          <div className="text-right">
            <span className={`font-headline text-5xl md:text-6xl font-extrabold ${tone.accent}`}>
              {data.score}
            </span>
            <span className="text-on-surface-variant text-xl">/100</span>
          </div>
        </header>

        <div className="h-2 w-full rounded-full bg-surface-container overflow-hidden">
          <div
            className={`h-full rounded-full ${tone.bar} transition-all`}
            style={{ width: `${Math.min(100, Math.max(0, data.score))}%` }}
          />
        </div>

        <section className="rounded-2xl bg-surface-container-low p-6 ghost-border">
          <h2 className="font-headline text-lg font-bold mb-3">Diagnóstico</h2>
          <p className="text-sm text-on-surface leading-relaxed">{data.feedback}</p>
        </section>

        {data.opening_text && (
          <section>
            <h2 className="font-headline text-lg font-bold mb-3">
              Como você abriu
            </h2>
            <blockquote className="rounded-2xl bg-surface-container-low p-5 ghost-border border-l-4 border-secondary">
              <p className="text-sm italic text-on-surface leading-relaxed">
                &ldquo;{data.opening_text}&rdquo;
              </p>
            </blockquote>
          </section>
        )}

        {data.tecnicas_detectadas && data.tecnicas_detectadas.length > 0 && (
          <section>
            <h2 className="font-headline text-lg font-bold mb-3">
              Técnicas detectadas
            </h2>
            <ul className="space-y-3">
              {data.tecnicas_detectadas.map((t, i) => (
                <li
                  key={i}
                  className="rounded-2xl bg-secondary/10 p-4 ghost-border"
                >
                  <div className="flex items-start gap-3 mb-2">
                    <span
                      className="material-symbols-outlined text-secondary text-xl shrink-0"
                      aria-hidden
                    >
                      check_circle
                    </span>
                    <div className="flex-1">
                      <p className="font-headline text-sm font-bold text-on-surface">
                        {t.label}
                      </p>
                      {t.descricao && (
                        <p className="text-xs text-on-surface-variant mt-1">
                          {t.descricao}
                        </p>
                      )}
                    </div>
                    {t.qualidade && (
                      <span
                        className={`text-[10px] font-label uppercase tracking-wider px-2 py-0.5 rounded-full ${
                          t.qualidade === "boa"
                            ? "bg-secondary/20 text-secondary"
                            : "bg-tertiary/20 text-tertiary"
                        }`}
                      >
                        {t.qualidade}
                      </span>
                    )}
                  </div>
                  {t.exemplo && (
                    <p className="text-xs italic text-on-surface-variant mt-2 pl-8">
                      &ldquo;{t.exemplo}&rdquo;
                    </p>
                  )}
                </li>
              ))}
            </ul>
          </section>
        )}

        {data.tecnicas_ausentes && data.tecnicas_ausentes.length > 0 && (
          <section>
            <h2 className="font-headline text-lg font-bold mb-3">
              Sugestões para próxima vez
            </h2>
            <ul className="space-y-3">
              {data.tecnicas_ausentes.map((t, i) => (
                <li
                  key={i}
                  className="rounded-2xl bg-surface-container-low p-4 ghost-border"
                >
                  <div className="flex items-start gap-3">
                    <span
                      className="material-symbols-outlined text-on-surface-variant text-xl shrink-0"
                      aria-hidden
                    >
                      lightbulb
                    </span>
                    <p className="text-sm text-on-surface italic">{t.sugestao}</p>
                  </div>
                </li>
              ))}
            </ul>
          </section>
        )}
      </div>
    </AppShell>
  );
}
