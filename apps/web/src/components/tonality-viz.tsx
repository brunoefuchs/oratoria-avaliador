"use client";

import type { TexturaDistribuicao, TexturaKey, TonalityData } from "@/lib/types/report";

interface TonalityVizProps {
  data: TonalityData | null | undefined;
}

const TEXTURA_LABELS: Record<TexturaKey, string> = {
  neutro: "Neutro",
  entusiasmado: "Entusiasmado",
  confiante: "Confiante",
  apatico: "Apático",
  tenso: "Tenso",
  hesitante: "Hesitante",
};

const TEXTURA_COLORS: Record<TexturaKey, string> = {
  entusiasmado: "bg-secondary",
  confiante: "bg-secondary/70",
  neutro: "bg-on-surface-variant/40",
  hesitante: "bg-tertiary/60",
  tenso: "bg-error",
  apatico: "bg-on-surface-variant",
};

const TEXTURA_DESCRIPTIONS: Record<TexturaKey, string> = {
  entusiasmado: "Voz com energia alta, valência positiva e dominância — bom para inspirar",
  confiante: "Tom firme com posicionamento autoral — bom para argumentar",
  neutro: "Sem carga emocional clara — informativo, mas pode soar plano se dominante",
  hesitante: "Sinais de insegurança vocal — costuma vir junto com fillers",
  tenso: "Tensão muscular vocal detectada — respiração + pausas reduzem isso",
  apatico: "Energia baixa — voz pode soar desinteressada da audiência",
};

function getOrderedDistribution(distribuicao: TexturaDistribuicao): Array<[TexturaKey, number]> {
  const order: TexturaKey[] = ["entusiasmado", "confiante", "neutro", "hesitante", "tenso", "apatico"];
  return order
    .map((k) => [k, distribuicao[k]] as [TexturaKey, number])
    .filter(([, v]) => v > 0);
}

export function TonalityViz({ data }: TonalityVizProps) {
  if (!data || !data.disponivel) return null;
  const ordered = getOrderedDistribution(data.textura_distribuicao);
  const dominanteLabel = TEXTURA_LABELS[data.textura_dominante as TexturaKey] ?? data.textura_dominante;

  return (
    <section className="rounded-2xl bg-surface-container-low p-5 ghost-border">
      <div className="flex items-baseline justify-between mb-3">
        <h3 className="font-headline text-base font-bold">Textura Emocional Vocal</h3>
        <span className="text-xs font-label uppercase tracking-wider text-on-surface-variant">
          5ª Vocal Foundation
        </span>
      </div>

      <p className="text-xs text-on-surface-variant mb-4">
        Como sua voz <em>soou</em> (não o que disse). Dominante:{" "}
        <strong className="text-on-surface">{dominanteLabel}</strong>
      </p>

      {/* Stacked bar */}
      <div className="flex h-3 w-full rounded-full overflow-hidden mb-3 bg-surface-container-highest">
        {ordered.map(([textura, pct]) => (
          <div
            key={textura}
            className={`${TEXTURA_COLORS[textura]} transition-all`}
            style={{ width: `${pct}%` }}
            title={`${TEXTURA_LABELS[textura]}: ${pct}%`}
          />
        ))}
      </div>

      {/* Legenda */}
      <ul className="grid grid-cols-2 gap-2 text-xs">
        {ordered.map(([textura, pct]) => (
          <li key={textura} className="flex items-center gap-2">
            <span
              className={`inline-block h-2 w-2 rounded-full shrink-0 ${TEXTURA_COLORS[textura]}`}
              aria-hidden
            />
            <span className="text-on-surface-variant">
              <strong className="text-on-surface">{TEXTURA_LABELS[textura]}</strong> {pct}%
            </span>
          </li>
        ))}
      </ul>

      {/* Feedback */}
      <p className="mt-4 text-sm text-on-surface leading-relaxed border-t border-on-surface-variant/20 pt-3">
        {data.feedback}
      </p>

      {/* Tooltip educativo */}
      <details className="mt-3">
        <summary className="text-[10px] font-label uppercase tracking-wider text-on-surface-variant cursor-pointer hover:text-on-surface">
          O que cada textura significa?
        </summary>
        <ul className="mt-2 space-y-1 text-[11px] text-on-surface-variant">
          {(Object.keys(TEXTURA_LABELS) as TexturaKey[]).map((k) => (
            <li key={k}>
              <strong className="text-on-surface">{TEXTURA_LABELS[k]}:</strong>{" "}
              {TEXTURA_DESCRIPTIONS[k]}
            </li>
          ))}
        </ul>
      </details>
    </section>
  );
}
