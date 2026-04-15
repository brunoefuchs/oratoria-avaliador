"use client";

import Link from "next/link";
import type { IdentityData } from "@/lib/types/report";

interface IdentityCardProps {
  data: IdentityData | null | undefined;
  evaluationId: string;
}

function getIdentityTone(score: number) {
  if (score >= 70) return { accent: "text-secondary", bar: "bg-secondary" };
  if (score >= 40) return { accent: "text-tertiary", bar: "bg-tertiary" };
  return { accent: "text-error", bar: "bg-error" };
}

const VICIO_LABELS: Record<string, string> = {
  vitimizacao: "Vitimização",
  rejeicao: "Rejeição",
  inseguranca: "Insegurança",
  validacao: "Busca por validação",
  comparacao: "Comparação",
};

export function IdentityCard({ data, evaluationId }: IdentityCardProps) {
  if (!data) return null;
  const tone = getIdentityTone(data.score);

  return (
    <section className="rounded-2xl bg-surface-container-low p-6 ghost-border">
      <div className="flex items-start justify-between gap-4 mb-4">
        <div>
          <span className="font-label text-xs uppercase tracking-[0.25em] text-on-surface-variant">
            Sub-dimensão
          </span>
          <h2 className="font-headline text-2xl font-bold mt-1">Sua Identidade</h2>
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

      <p className="text-sm text-on-surface leading-relaxed mb-4">{data.diagnostico}</p>

      <div className="grid grid-cols-2 gap-3 text-xs mb-4">
        <div className="rounded-lg bg-surface-container px-3 py-2">
          <span className="block text-on-surface-variant">Frases de autoridade</span>
          <span className="font-headline text-lg font-bold text-secondary">
            {data.autoridade_count}
          </span>
        </div>
        <div className="rounded-lg bg-surface-container px-3 py-2">
          <span className="block text-on-surface-variant">Vícios emocionais</span>
          <span className="font-headline text-lg font-bold text-tertiary">
            {data.total_vicios}
          </span>
        </div>
      </div>

      {data.vicio_dominante && (
        <p className="text-xs text-on-surface-variant mb-3">
          Vício dominante:{" "}
          <span className="font-semibold text-on-surface">
            {VICIO_LABELS[data.vicio_dominante] ?? data.vicio_dominante}
          </span>
        </p>
      )}

      {data.exemplos && data.exemplos.length > 0 && (
        <ul className="space-y-1.5 mb-4">
          {data.exemplos.slice(0, 3).map((ex, i) => (
            <li
              key={i}
              className="text-xs italic text-on-surface-variant border-l-2 border-on-surface-variant/30 pl-3"
            >
              &ldquo;{ex.texto}&rdquo;
            </li>
          ))}
        </ul>
      )}

      <Link
        href={`/report/${evaluationId}/identity`}
        className="inline-flex items-center gap-1 text-xs font-label uppercase tracking-wider text-secondary hover:underline"
      >
        Ver análise completa
        <span className="material-symbols-outlined text-sm" aria-hidden>
          arrow_forward
        </span>
      </Link>
    </section>
  );
}
