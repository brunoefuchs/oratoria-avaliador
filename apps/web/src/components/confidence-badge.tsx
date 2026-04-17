/**
 * Story 9.1 (Epic 9 — State of the Art) — Confidence badge por dimensão.
 *
 * Exibe emoji + label + tooltip indicando nível de confiança da medição.
 * Rende null se `confidence` undefined (payload v0.6.0 ou flag OFF).
 *
 * Uso:
 *   <ConfidenceBadge confidence={report.dimension_confidence?.voice} />
 */

import { CONFIDENCE_BADGES, type ConfidenceLevel } from "@/lib/report-labels";

interface Props {
  confidence?: ConfidenceLevel;
  compact?: boolean;
}

export function ConfidenceBadge({ confidence, compact = false }: Props) {
  if (!confidence) return null;

  const badge = CONFIDENCE_BADGES[confidence];

  return (
    <span
      title={badge.tooltip}
      aria-label={`${badge.label}: ${badge.tooltip}`}
      className={
        compact
          ? "inline-flex items-center gap-1 text-xs opacity-70"
          : "inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-xs text-white/80"
      }
    >
      <span aria-hidden>{badge.emoji}</span>
      {!compact && <span>{badge.label}</span>}
    </span>
  );
}
