"use client";

import { useState } from "react";

const SLIDES = [
  {
    title: "O que vamos analisar",
    content: (
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div className="rounded-lg bg-gray-50 p-3 text-center">
          <span className="text-2xl">🎹</span>
          <p className="mt-1 font-medium">Variedade Vocal</p>
        </div>
        <div className="rounded-lg bg-gray-50 p-3 text-center">
          <span className="text-2xl">🎙️</span>
          <p className="mt-1 font-medium">Voz e Diccao</p>
        </div>
        <div className="rounded-lg bg-gray-50 p-3 text-center">
          <span className="text-2xl">👁️</span>
          <p className="mt-1 font-medium">Presenca Visual</p>
        </div>
        <div className="rounded-lg bg-gray-50 p-3 text-center">
          <span className="text-2xl">🧍</span>
          <p className="mt-1 font-medium">Postura</p>
        </div>
        <div className="col-span-2 rounded-lg bg-gray-50 p-3 text-center">
          <span className="text-2xl">💬</span>
          <p className="mt-1 font-medium">Clareza Verbal</p>
        </div>
      </div>
    ),
  },
  {
    title: "Como funciona",
    content: (
      <div className="space-y-4 text-sm">
        <div className="flex items-center gap-3">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-100 text-blue-700 font-bold">1</span>
          <p>Envie um video de ate 5 minutos</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-100 text-blue-700 font-bold">2</span>
          <p>Nossa IA analisa em ~2 minutos</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-100 text-blue-700 font-bold">3</span>
          <p>Receba um relatorio completo com coaching personalizado + plano de 12 semanas</p>
        </div>
      </div>
    ),
  },
  {
    title: "Dica para melhor resultado",
    content: (
      <div className="space-y-3 text-sm text-gray-600">
        <p>📹 Grave olhando para a camera</p>
        <p>🔇 Ambiente silencioso (sem musica/ruido)</p>
        <p>💡 Boa iluminacao no rosto</p>
        <p>🧍 Corpo visivel (pelo menos da cintura pra cima)</p>
        <p>⏱️ Fale por pelo menos 1 minuto</p>
      </div>
    ),
  },
];

interface OnboardingProps {
  onComplete: () => void;
}

export function Onboarding({ onComplete }: OnboardingProps) {
  const [step, setStep] = useState(0);

  const handleNext = () => {
    if (step < SLIDES.length - 1) {
      setStep(step + 1);
    } else {
      localStorage.setItem("oratoria_onboarding_done", "true");
      onComplete();
    }
  };

  const handleSkip = () => {
    localStorage.setItem("oratoria_onboarding_done", "true");
    onComplete();
  };

  const slide = SLIDES[step];

  return (
    <div className="w-full max-w-md space-y-6 text-center">
      {/* Progress */}
      <div className="flex gap-1">
        {SLIDES.map((_, i) => (
          <div
            key={i}
            className={`h-1 flex-1 rounded-full transition-colors ${
              i <= step ? "bg-blue-500" : "bg-gray-200"
            }`}
          />
        ))}
      </div>

      <h2 className="text-xl font-bold">{slide.title}</h2>

      <div className="min-h-[200px]">{slide.content}</div>

      <div className="space-y-2">
        <button
          onClick={handleNext}
          className="w-full rounded-xl bg-blue-500 py-3 text-white font-medium hover:bg-blue-600"
        >
          {step < SLIDES.length - 1 ? "Proximo" : "Comecar!"}
        </button>
        <button
          onClick={handleSkip}
          className="w-full text-sm text-gray-400 hover:text-gray-600"
        >
          Pular
        </button>
      </div>
    </div>
  );
}
