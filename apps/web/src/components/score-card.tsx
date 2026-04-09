"use client";

interface ScoreCardProps {
  title: string;
  score: number;
  dimensionKey?: string;
  summary?: string;
  onClick?: () => void;
}

function getScoreColor(score: number) {
  if (score >= 70) return { bg: "bg-green-50", text: "text-green-700", ring: "ring-green-200" };
  if (score >= 40) return { bg: "bg-yellow-50", text: "text-yellow-700", ring: "ring-yellow-200" };
  return { bg: "bg-red-50", text: "text-red-700", ring: "ring-red-200" };
}

const DIMENSION_ICONS: Record<string, string> = {
  posture: "🧍",
  gesture: "👁️",
  voice: "🎙️",
  fillers: "💬",
  variety: "🎹",
  archetypes: "🎭",
};

export function ScoreCard({ title, score, dimensionKey, summary, onClick }: ScoreCardProps) {
  const color = getScoreColor(score);
  const icon = DIMENSION_ICONS[dimensionKey || ""] || "📊";

  return (
    <button
      onClick={onClick}
      className={`
        w-full rounded-xl p-5 text-left ring-1 transition-shadow hover:shadow-md
        ${color.bg} ${color.ring}
      `}
    >
      <div className="flex items-center justify-between">
        <span className="text-2xl">{icon}</span>
        <span className={`text-2xl font-bold ${color.text}`}>{score}</span>
      </div>
      <p className="mt-2 text-sm font-medium capitalize text-gray-800">
        {title}
      </p>
      {summary && (
        <p className="mt-1 text-xs text-gray-500 line-clamp-2">{summary}</p>
      )}
    </button>
  );
}
