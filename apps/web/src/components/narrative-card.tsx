"use client";

import type { StorytellingData } from "@/lib/types/report";

interface NarrativeCardProps {
  data: StorytellingData | null | undefined;
}

// Story 7.3 fix QA — labels neutros (storytelling.type e generico).
// OpeningCard ja diferencia "Pergunta Reflexiva" de "Pergunta Casual" via tecnicas_detectadas.
// Aqui mantemos label generico + strength para evitar contradicao cross-card.
const HOOK_LABELS: Record<string, string> = {
  question: "Pergunta",
  story: "Gancho com história",
  stat: "Dado/estatística",
  vulnerability: "Vulnerabilidade",
  challenge: "Desafio à audiência",
  magic_trick: "Surpresa/magia",
  none: "Sem hook detectado",
};

const STRENGTH_LABELS: Record<string, string> = {
  weak: "fraco",
  medium: "médio",
  strong: "forte",
};

const STRENGTH_COLORS: Record<string, string> = {
  weak: "bg-error/20 text-error",
  medium: "bg-tertiary/20 text-tertiary",
  strong: "bg-secondary/20 text-secondary",
};

const DIAGNOSTICO_LABELS: Record<string, string> = {
  narrativa_excepcional: "Narrativa excepcional",
  narrativa_solida: "Narrativa sólida",
  narrativa_basica: "Narrativa básica",
  narrativa_ausente: "Narrativa ausente",
  indisponivel: "Indisponível",
};

function getNarrativeTone(score: number) {
  if (score >= 70) return { accent: "text-secondary", bar: "bg-secondary" };
  if (score >= 40) return { accent: "text-tertiary", bar: "bg-tertiary" };
  return { accent: "text-error", bar: "bg-error" };
}

export function NarrativeCard({ data }: NarrativeCardProps) {
  if (!data || !data.disponivel) return null;
  const tone = getNarrativeTone(data.score);
  const diagnosticoLabel = DIAGNOSTICO_LABELS[data.diagnostico] ?? data.diagnostico;

  return (
    <section className="rounded-2xl bg-surface-container-low p-6 ghost-border">
      <div className="flex items-start justify-between gap-4 mb-4">
        <div className="flex items-center gap-3">
          <span
            className={`material-symbols-outlined text-3xl ${tone.accent}`}
            aria-hidden
          >
            menu_book
          </span>
          <div>
            <span className="font-label text-xs uppercase tracking-[0.25em] text-on-surface-variant">
              Arquitetura da mensagem
            </span>
            <h2 className="font-headline text-2xl font-bold mt-1">Narrativa</h2>
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

      <p className="text-sm text-on-surface mb-4">
        Diagnóstico: <strong>{diagnosticoLabel}</strong>
      </p>

      {/* 4 elementos chave */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs mb-4">
        {/* Bridge */}
        <div className="rounded-lg bg-surface-container px-3 py-2 flex items-center gap-2">
          <span
            className={`material-symbols-outlined text-base ${
              data.bridge_sentence.detected ? "text-secondary" : "text-on-surface-variant"
            }`}
            aria-hidden
          >
            {data.bridge_sentence.detected ? "check_circle" : "cancel"}
          </span>
          <div className="flex-1 min-w-0">
            <span className="block text-on-surface font-semibold">Bridge sentence</span>
            <span className="text-on-surface-variant">
              {data.bridge_sentence.detected
                ? `${data.bridge_sentence.count} detectada${data.bridge_sentence.count > 1 ? "s" : ""}`
                : "não detectada"}
            </span>
          </div>
        </div>

        {/* Hook */}
        <div className="rounded-lg bg-surface-container px-3 py-2 flex items-center gap-2">
          <span
            className={`material-symbols-outlined text-base ${
              data.opening_hook.type !== "none" ? "text-secondary" : "text-on-surface-variant"
            }`}
            aria-hidden
          >
            {data.opening_hook.type !== "none" ? "rocket_launch" : "remove"}
          </span>
          <div className="flex-1 min-w-0">
            <span className="block text-on-surface font-semibold">Opening hook</span>
            <span className="text-on-surface-variant flex items-center gap-1">
              {HOOK_LABELS[data.opening_hook.type]}
              {data.opening_hook.type !== "none" && (
                <span
                  className={`text-[10px] px-1.5 py-0.5 rounded-full ${
                    STRENGTH_COLORS[data.opening_hook.strength]
                  }`}
                >
                  {STRENGTH_LABELS[data.opening_hook.strength]}
                </span>
              )}
            </span>
          </div>
        </div>

        {/* CTA */}
        <div className="rounded-lg bg-surface-container px-3 py-2 flex items-center gap-2">
          <span
            className={`material-symbols-outlined text-base ${
              data.cta.detected ? "text-secondary" : "text-on-surface-variant"
            }`}
            aria-hidden
          >
            {data.cta.detected ? "check_circle" : "cancel"}
          </span>
          <div className="flex-1 min-w-0">
            <span className="block text-on-surface font-semibold">Call to action</span>
            <span className="text-on-surface-variant">
              {data.cta.detected ? "presente no fechamento" : "ausente"}
            </span>
          </div>
        </div>

        {/* Chemicals */}
        <div className="rounded-lg bg-surface-container px-3 py-2">
          <span className="block text-on-surface font-semibold mb-1">Chemicals</span>
          <div className="flex flex-wrap gap-1">
            {data.chemicals.dopamine.detected && (
              <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-secondary/20 text-secondary">
                dopamina
              </span>
            )}
            {data.chemicals.oxytocin.detected && (
              <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-secondary/20 text-secondary">
                oxitocina
              </span>
            )}
            {data.chemicals.cortisol_risk.detected && (
              <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-error/20 text-error">
                ⚠ cortisol
              </span>
            )}
            {!data.chemicals.dopamine.detected &&
              !data.chemicals.oxytocin.detected &&
              !data.chemicals.cortisol_risk.detected && (
                <span className="text-on-surface-variant">nenhum acionado</span>
              )}
          </div>
        </div>
      </div>

      {/* Sugestões se score baixo */}
      {data.suggestions && data.suggestions.length > 0 && (
        <div>
          <p className="text-xs font-label uppercase tracking-wider text-on-surface-variant mb-2">
            Sugestões para próxima vez
          </p>
          <ul className="space-y-1.5">
            {data.suggestions.map((s, i) => (
              <li key={i} className="flex items-start gap-2 text-xs">
                <span
                  className="material-symbols-outlined text-on-surface-variant text-base shrink-0"
                  aria-hidden
                >
                  lightbulb
                </span>
                <span className="text-on-surface-variant italic">{s}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
