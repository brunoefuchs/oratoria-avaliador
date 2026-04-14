"use client";

import { useState } from "react";

type Dimension = { icon: string; label: string };

const DIMENSIONS: Dimension[] = [
  { icon: "graphic_eq", label: "Variedade Vocal" },
  { icon: "mic", label: "Voz e Dicção" },
  { icon: "visibility", label: "Presença Visual" },
  { icon: "accessibility", label: "Postura" },
  { icon: "chat_bubble", label: "Clareza Verbal" },
];

const SLIDES = [
  {
    kicker: "O que você vai ganhar",
    title: "Cinco dimensões iluminadas",
    content: (
      <div className="grid grid-cols-2 gap-3 text-sm">
        {DIMENSIONS.slice(0, 4).map((d) => (
          <div
            key={d.label}
            className="rounded-2xl bg-surface-container-high p-4 text-center ghost-border"
          >
            <span className="material-symbols-outlined text-secondary text-2xl mb-1 block">
              {d.icon}
            </span>
            <p className="font-medium text-on-surface">{d.label}</p>
          </div>
        ))}
        <div className="col-span-2 rounded-2xl bg-surface-container-high p-4 text-center ghost-border">
          <span className="material-symbols-outlined text-secondary text-2xl mb-1 block">
            {DIMENSIONS[4].icon}
          </span>
          <p className="font-medium text-on-surface">{DIMENSIONS[4].label}</p>
        </div>
      </div>
    ),
  },
  {
    kicker: "Como funciona",
    title: "Três passos simples",
    content: (
      <div className="space-y-3 text-sm">
        {[
          { n: "1", label: "Envie um vídeo de até 5 minutos" },
          { n: "2", label: "Nossa IA analisa em ~2 minutos" },
          {
            n: "3",
            label:
              "Receba relatório completo com coaching + plano de 12 semanas",
          },
        ].map((s) => (
          <div
            key={s.n}
            className="flex items-center gap-4 rounded-2xl bg-surface-container-high p-4 ghost-border"
          >
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-ai-pulse text-on-primary font-headline font-bold shadow-cta-glow">
              {s.n}
            </span>
            <p className="text-on-surface">{s.label}</p>
          </div>
        ))}
      </div>
    ),
  },
  {
    kicker: "Dicas de captura",
    title: "Para a melhor leitura da IA",
    content: (
      <div className="space-y-2 text-sm">
        {[
          { icon: "videocam", label: "Grave olhando para a câmera" },
          { icon: "volume_off", label: "Ambiente silencioso (sem música/ruído)" },
          { icon: "wb_sunny", label: "Boa iluminação no rosto" },
          { icon: "accessibility", label: "Corpo visível (ao menos cintura pra cima)" },
          { icon: "schedule", label: "Fale por pelo menos 1 minuto" },
        ].map((t) => (
          <div
            key={t.icon}
            className="flex items-center gap-3 rounded-xl bg-surface-container-high p-3 ghost-border"
          >
            <span className="material-symbols-outlined text-secondary">
              {t.icon}
            </span>
            <p className="text-on-surface-variant">{t.label}</p>
          </div>
        ))}
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
    <div className="w-full max-w-md space-y-7">
      <div className="flex gap-1.5">
        {SLIDES.map((_, i) => (
          <div
            key={i}
            className={`h-1 flex-1 rounded-full transition-colors ${
              i <= step ? "bg-secondary" : "bg-surface-container-high"
            }`}
          />
        ))}
      </div>

      <div className="space-y-2">
        <span className="font-label text-xs uppercase tracking-[0.3em] text-secondary">
          {slide.kicker}
        </span>
        <h2 className="font-headline text-3xl md:text-4xl font-extrabold tracking-tight leading-tight">
          {slide.title}
        </h2>
      </div>

      <div className="min-h-[260px]">{slide.content}</div>

      <div className="space-y-3">
        <button
          onClick={handleNext}
          className="w-full bg-ai-pulse text-on-primary font-bold px-6 py-3.5 rounded-full shadow-cta-glow active:scale-[0.98] transition-all"
        >
          {step < SLIDES.length - 1 ? "Próximo" : "Começar!"}
        </button>
        <button
          onClick={handleSkip}
          className="w-full text-center text-sm text-on-surface-variant hover:text-on-surface transition py-2"
        >
          Pular introdução
        </button>
      </div>
    </div>
  );
}
