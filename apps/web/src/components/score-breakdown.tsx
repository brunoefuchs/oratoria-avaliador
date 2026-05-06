"use client";

import { useEffect, useRef, useState } from "react";
import { DIMENSIONS } from "@/lib/report-labels";
import type {
  DimensionKey,
  DimensionWeights,
  ScoreBreakdownItem,
} from "@/lib/types/report";

interface ScoreBreakdownProps {
  overallScore: number;
  dimensionScores: Partial<Record<DimensionKey, number>>;
  weights?: DimensionWeights | null;
  contexto?: string | null;
}

const DEFAULT_WEIGHTS: DimensionWeights = {
  variety: 0.29,
  voice: 0.24,
  gesture: 0.18,
  posture: 0.18,
  fillers: 0.11,
};

export function ScoreBreakdown({
  overallScore,
  dimensionScores,
  weights,
  contexto,
}: ScoreBreakdownProps) {
  const [open, setOpen] = useState(false);
  const popoverRef = useRef<HTMLDivElement>(null);

  // Story 7.2 QA fix — click outside e ESC fecham o popover
  useEffect(() => {
    if (!open) return;
    function handleClickOutside(event: MouseEvent) {
      if (popoverRef.current && !popoverRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [open]);

  const activeWeights = weights ?? DEFAULT_WEIGHTS;
  const usingDefault = !weights;

  const breakdown: ScoreBreakdownItem[] = (
    Object.keys(activeWeights) as DimensionKey[]
  )
    .filter((k) => dimensionScores[k] != null)
    .map((k) => ({
      key: k,
      label: DIMENSIONS[k] ?? k,
      value: dimensionScores[k] ?? 0,
      weight: activeWeights[k],
      contribution: Math.round((dimensionScores[k] ?? 0) * activeWeights[k] * 10) / 10,
    }));

  return (
    <div className="relative inline-block" ref={popoverRef}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="group flex items-baseline gap-2 hover:opacity-90 active:scale-[0.98] transition-all"
        aria-expanded={open}
        aria-label="Ver breakdown da pontuação"
      >
        <span className="font-headline text-6xl md:text-8xl font-extrabold">
          {overallScore}
        </span>
        <span className="text-on-surface-variant text-2xl">/100</span>
        <span
          className="material-symbols-outlined text-base text-on-surface-variant opacity-50 group-hover:opacity-100 transition-opacity"
          aria-hidden
        >
          {open ? "expand_less" : "expand_more"}
        </span>
      </button>

      {open && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm"
            onClick={() => setOpen(false)}
            aria-hidden
          />
          <div
            className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-[min(92vw,28rem)] max-h-[80vh] overflow-y-auto rounded-2xl bg-surface-container-high shadow-2xl ghost-border p-5"
            role="dialog"
            aria-label="Detalhamento da pontuação"
          >
          <div className="flex items-start justify-between mb-3">
            <h3 className="font-headline text-base font-bold">
              Como sua pontuação foi calculada
            </h3>
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="material-symbols-outlined text-on-surface-variant text-lg hover:text-on-surface"
              aria-label="Fechar"
            >
              close
            </button>
          </div>

          {contexto && (
            <p className="text-xs text-on-surface-variant mb-3">
              Avaliado para:{" "}
              <span className="font-semibold text-secondary">{contexto}</span>
            </p>
          )}

          {usingDefault && (
            <p className="text-xs italic text-on-surface-variant mb-3">
              Usando pesos padrão (contexto não informado).
            </p>
          )}

          <ul className="space-y-2 mb-3">
            {breakdown.map((item) => (
              <li
                key={item.key}
                className="flex items-baseline justify-between text-xs"
              >
                <span className="text-on-surface">
                  {item.label}{" "}
                  <span className="text-on-surface-variant">
                    (peso {Math.round(item.weight * 100)}%)
                  </span>
                </span>
                <span className="font-mono text-on-surface-variant tabular-nums">
                  {item.value} × {item.weight.toFixed(2)} ={" "}
                  <strong className="text-on-surface">{item.contribution}</strong>
                </span>
              </li>
            ))}
          </ul>

          <p className="text-[10px] text-on-surface-variant border-t border-on-surface-variant/20 pt-2 italic">
            Fórmula: Pontuação = Σ(dimensão × peso contextual)
          </p>
          </div>
        </>
      )}
    </div>
  );
}
