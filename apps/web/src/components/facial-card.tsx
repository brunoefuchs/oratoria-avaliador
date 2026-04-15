"use client";

import type { FacialData } from "@/lib/types/report";

interface FacialCardProps {
  data: FacialData | null | undefined;
}

function getFacialTone(score: number) {
  if (score >= 70) return { accent: "text-secondary", bar: "bg-secondary" };
  if (score >= 40) return { accent: "text-tertiary", bar: "bg-tertiary" };
  return { accent: "text-error", bar: "bg-error" };
}

const DIAGNOSTICO_ICONS: Record<string, string> = {
  expressao_equilibrada: "sentiment_satisfied",
  expressao_travada: "sentiment_neutral",
  rosto_estatico: "face",
  expressao_monotona: "sentiment_neutral",
  expressao_exagerada: "sentiment_very_satisfied",
  indisponivel: "face_retouching_off",
};

export function FacialCard({ data }: FacialCardProps) {
  if (!data || !data.disponivel) return null;
  const tone = getFacialTone(data.score);
  const icon = DIAGNOSTICO_ICONS[data.diagnostico] ?? "face";

  return (
    <section className="rounded-2xl bg-surface-container-low p-6 ghost-border">
      <div className="flex items-start justify-between gap-4 mb-4">
        <div className="flex items-center gap-3">
          <span
            className={`material-symbols-outlined text-3xl ${tone.accent}`}
            aria-hidden
          >
            {icon}
          </span>
          <div>
            <span className="font-label text-xs uppercase tracking-[0.25em] text-on-surface-variant">
              Sub-dimensão
            </span>
            <h2 className="font-headline text-2xl font-bold mt-1">
              Expressão Facial
            </h2>
          </div>
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

      <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-xs">
        <div className="rounded-lg bg-surface-container px-3 py-2">
          <span className="block text-on-surface-variant">% sorriso ativo</span>
          <span className="font-headline text-lg font-bold text-on-surface">
            {data.smile_frequency_percent.toFixed(0)}%
          </span>
        </div>
        <div className="rounded-lg bg-surface-container px-3 py-2">
          <span className="block text-on-surface-variant">Sobrancelhas/min</span>
          <span className="font-headline text-lg font-bold text-on-surface">
            {data.brow_raises_per_minute.toFixed(1)}
          </span>
        </div>
        <div className="rounded-lg bg-surface-container px-3 py-2 col-span-2 md:col-span-1">
          <span className="block text-on-surface-variant">Variação ocular</span>
          <span className="font-headline text-lg font-bold text-on-surface">
            {(data.eye_openness_stddev * 1000).toFixed(0)}
          </span>
        </div>
      </div>

      {data.detection_pct < 80 && (
        <p className="mt-3 text-[10px] italic text-on-surface-variant">
          Rosto detectado em {data.detection_pct.toFixed(0)}% dos frames — análise pode ser parcial.
        </p>
      )}
    </section>
  );
}
