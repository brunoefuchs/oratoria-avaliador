"use client";

const STEPS = [
  { key: "splitting", label: "Separando audio e video" },
  { key: "analyzing_posture", label: "Analisando postura" },
  { key: "analyzing_gesture", label: "Analisando gestual" },
  { key: "analyzing_voice", label: "Analisando tom de voz" },
  { key: "analyzing_fillers", label: "Detectando vicios de linguagem" },
  { key: "generating_report", label: "Gerando relatorio" },
];

interface ProcessingStatusProps {
  substatus: string | null;
  stepsCompleted: number;
}

export function ProcessingStatus({
  substatus,
  stepsCompleted,
}: ProcessingStatusProps) {
  return (
    <div className="w-full max-w-md mx-auto space-y-4">
      {STEPS.map((step, index) => {
        const isCompleted = index < stepsCompleted;
        const isCurrent = step.key === substatus;

        return (
          <div key={step.key} className="flex items-center gap-3">
            {/* Icon */}
            <div
              className={`
                flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-medium
                ${isCompleted
                  ? "bg-green-500 text-white"
                  : isCurrent
                    ? "bg-blue-500 text-white"
                    : "bg-gray-200 text-gray-500"
                }
              `}
            >
              {isCompleted ? (
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                </svg>
              ) : isCurrent ? (
                <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
              ) : (
                <span>{index + 1}</span>
              )}
            </div>

            {/* Label */}
            <span
              className={`text-sm ${
                isCompleted
                  ? "text-green-700 font-medium"
                  : isCurrent
                    ? "text-blue-700 font-medium"
                    : "text-gray-400"
              }`}
            >
              {step.label}
              {isCurrent && "..."}
            </span>
          </div>
        );
      })}
    </div>
  );
}
