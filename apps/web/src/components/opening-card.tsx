"use client";

import Link from "next/link";
import type { OpeningData } from "@/lib/types/report";

interface OpeningCardProps {
  data: OpeningData | null | undefined;
  evaluationId: string;
}

function getOpeningTone(score: number) {
  if (score >= 70) return { accent: "text-secondary", bar: "bg-secondary" };
  if (score >= 40) return { accent: "text-tertiary", bar: "bg-tertiary" };
  return { accent: "text-error", bar: "bg-error" };
}

export function OpeningCard({ data, evaluationId }: OpeningCardProps) {
  if (!data || !data.disponivel) return null;
  const tone = getOpeningTone(data.score);

  return (
    <section className="rounded-2xl bg-surface-container-low p-6 ghost-border">
      <div className="flex items-start justify-between gap-4 mb-4">
        <div>
          <span className="font-label text-xs uppercase tracking-[0.25em] text-on-surface-variant">
            Primeiros segundos
          </span>
          <h2 className="font-headline text-2xl font-bold mt-1">Sua Abertura</h2>
        </div>
        <div className="shrink-0 text-right">
          <span className={`font-headline text-4xl font-extrabold ${tone.accent}`}>
            {data.score}
          </span>
          <span className="text-on-surface-variant text-base">/100</span>
        </div>
      </div>

      <div className="h-1 w-full rounded-full bg-surface-container-highest overflow-hidden mb-4">
        <div
          className={`h-full rounded-full ${tone.bar} transition-all`}
          style={{ width: `${Math.min(100, Math.max(0, data.score))}%` }}
        />
      </div>

      <p className="text-sm text-on-surface leading-relaxed mb-4">{data.feedback}</p>

      {data.tecnicas_detectadas && data.tecnicas_detectadas.length > 0 && (
        <div className="mb-3">
          <p className="text-xs font-label uppercase tracking-wider text-on-surface-variant mb-2">
            Técnicas usadas
          </p>
          <ul className="space-y-1.5">
            {data.tecnicas_detectadas.slice(0, 4).map((t, i) => (
              <li key={i} className="flex items-start gap-2 text-xs">
                <span className="material-symbols-outlined text-secondary text-base shrink-0" aria-hidden>
                  check_circle
                </span>
                <span className="text-on-surface">{t.label}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {data.tecnicas_ausentes && data.tecnicas_ausentes.length > 0 && (
        <div className="mb-4">
          <p className="text-xs font-label uppercase tracking-wider text-on-surface-variant mb-2">
            Sugestões para próxima
          </p>
          <ul className="space-y-1.5">
            {data.tecnicas_ausentes.slice(0, 2).map((t, i) => (
              <li key={i} className="flex items-start gap-2 text-xs">
                <span className="material-symbols-outlined text-on-surface-variant text-base shrink-0" aria-hidden>
                  lightbulb
                </span>
                <span className="text-on-surface-variant italic">{t.sugestao}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <Link
        href={`/report/${evaluationId}/opening`}
        className="inline-flex items-center gap-1 text-xs font-label uppercase tracking-wider text-secondary hover:underline"
      >
        Ver abertura completa
        <span className="material-symbols-outlined text-sm" aria-hidden>
          arrow_forward
        </span>
      </Link>
    </section>
  );
}
