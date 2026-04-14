"use client";

const STEPS = [
  { key: "splitting", label: "Separando áudio e vídeo" },
  { key: "analyzing_posture", label: "Analisando postura" },
  { key: "analyzing_gesture", label: "Analisando gestual e contato visual" },
  { key: "analyzing_voice", label: "Analisando voz e prosódia" },
  { key: "analyzing_fillers", label: "Detectando vícios de linguagem" },
  { key: "analyzing_variety", label: "Analisando variedade vocal" },
  { key: "analyzing_archetypes", label: "Classificando arquétipos vocais" },
  { key: "generating_report", label: "Gerando relatório de coaching" },
];

interface ProcessingStatusProps {
  substatus: string | null;
  stepsCompleted: number;
}

export function ProcessingStatus({
  substatus,
  stepsCompleted,
}: ProcessingStatusProps) {
  const progressPct = Math.min(
    100,
    Math.round((stepsCompleted / STEPS.length) * 100)
  );

  return (
    <div className="w-full max-w-lg mx-auto space-y-6">
      <div>
        <div className="flex justify-between text-xs font-label uppercase tracking-[0.2em] text-on-surface-variant mb-2">
          <span>Progresso</span>
          <span className="text-secondary">{progressPct}%</span>
        </div>
        <div className="h-1.5 rounded-full bg-surface-container-high overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-secondary to-primary-container transition-all duration-500"
            style={{ width: `${progressPct}%` }}
          />
        </div>
      </div>

      <div className="space-y-3">
        {STEPS.map((step, index) => {
          const isCompleted = index < stepsCompleted;
          const isCurrent = step.key === substatus;

          return (
            <div
              key={step.key}
              className={`flex items-center gap-4 rounded-xl p-3 transition-all ${
                isCurrent
                  ? "bg-surface-container-high ghost-border"
                  : isCompleted
                  ? "bg-transparent"
                  : "bg-transparent opacity-60"
              }`}
            >
              <div
                className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-sm font-semibold transition-all ${
                  isCompleted
                    ? "bg-secondary-container/20 text-secondary"
                    : isCurrent
                    ? "bg-ai-pulse text-on-primary shadow-cta-glow"
                    : "bg-surface-container-highest text-on-surface-variant ghost-border"
                }`}
              >
                {isCompleted ? (
                  <span className="material-symbols-outlined text-lg">
                    check
                  </span>
                ) : isCurrent ? (
                  <svg
                    className="h-5 w-5 animate-spin"
                    viewBox="0 0 24 24"
                    fill="none"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="3"
                    />
                    <path
                      className="opacity-90"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                    />
                  </svg>
                ) : (
                  <span className="text-xs">{index + 1}</span>
                )}
              </div>

              <span
                className={`text-sm leading-snug ${
                  isCompleted
                    ? "text-on-surface-variant"
                    : isCurrent
                    ? "text-on-surface font-semibold"
                    : "text-on-surface-variant"
                }`}
              >
                {step.label}
                {isCurrent && "..."}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
