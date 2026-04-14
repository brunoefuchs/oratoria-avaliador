"use client";

interface ScoreCardProps {
  title: string;
  score: number;
  dimensionKey?: string;
  summary?: string;
  onClick?: () => void;
}

function getScoreTone(score: number) {
  if (score >= 70)
    return {
      accent: "text-secondary",
      badge: "bg-secondary-container/20 text-secondary",
      bar: "bg-secondary",
    };
  if (score >= 40)
    return {
      accent: "text-tertiary",
      badge: "bg-tertiary/20 text-tertiary",
      bar: "bg-tertiary",
    };
  return {
    accent: "text-error",
    badge: "bg-error-container/30 text-error",
    bar: "bg-error",
  };
}

const DIMENSION_ICONS: Record<string, string> = {
  posture: "accessibility",
  gesture: "visibility",
  voice: "mic",
  fillers: "chat_bubble",
  variety: "graphic_eq",
  archetypes: "theater_comedy",
};

export function ScoreCard({
  title,
  score,
  dimensionKey,
  summary,
  onClick,
}: ScoreCardProps) {
  const tone = getScoreTone(score);
  const icon = DIMENSION_ICONS[dimensionKey || ""] || "analytics";
  const interactive = !!onClick;

  return (
    <button
      onClick={onClick}
      disabled={!interactive}
      className={`group relative w-full rounded-2xl bg-surface-container-low p-5 text-left ghost-border transition-all ${
        interactive
          ? "hover:bg-surface-container active:scale-[0.98] cursor-pointer"
          : "cursor-default"
      }`}
    >
      <div className="flex items-start justify-between gap-3 mb-4">
        <span
          className={`material-symbols-outlined text-2xl ${tone.accent}`}
          aria-hidden
        >
          {icon}
        </span>
        <span className={`font-headline text-3xl font-bold ${tone.accent}`}>
          {score}
        </span>
      </div>
      <p className="text-sm font-semibold text-on-surface leading-tight">
        {title}
      </p>
      <div className="mt-3 h-1 w-full rounded-full bg-surface-container-highest overflow-hidden">
        <div
          className={`h-full rounded-full ${tone.bar} transition-all`}
          style={{ width: `${Math.min(100, Math.max(0, score))}%` }}
        />
      </div>
      {summary && (
        <p className="mt-3 text-xs text-on-surface-variant line-clamp-2 leading-relaxed">
          {summary}
        </p>
      )}
      {interactive && (
        <span className="material-symbols-outlined absolute right-3 bottom-3 text-base text-on-surface-variant opacity-0 group-hover:opacity-60 transition-opacity">
          arrow_forward
        </span>
      )}
    </button>
  );
}
