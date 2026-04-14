"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { VideoUploader } from "@/components/video-uploader";
import { Onboarding } from "@/components/onboarding";
import { AppShell } from "@/components/app-shell";

const FEATURE_CHIPS = [
  { icon: "graphic_eq", label: "Variedade Vocal" },
  { icon: "mic", label: "Voz e Dicção" },
  { icon: "visibility", label: "Presença Visual" },
  { icon: "accessibility", label: "Postura" },
  { icon: "chat_bubble", label: "Clareza Verbal" },
];

export default function Home() {
  const router = useRouter();
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const done = localStorage.getItem("oratoria_onboarding_done");
    if (!done) {
      setShowOnboarding(true);
    }
    if (!localStorage.getItem("oratoria_user_token")) {
      localStorage.setItem("oratoria_user_token", crypto.randomUUID());
    }
    setReady(true);
  }, []);

  if (!ready) return null;

  if (showOnboarding) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6 md:p-10">
        <Onboarding onComplete={() => setShowOnboarding(false)} />
      </div>
    );
  }

  return (
    <AppShell maxWidth="xl">
      <div className="space-y-10 md:space-y-14">
        {/* Hero */}
        <section className="space-y-5 md:space-y-6">
          <span className="font-label text-xs uppercase tracking-[0.3em] text-secondary/80">
            The Resonant Stage
          </span>
          <h1 className="display-lg">
            <span className="block bg-clip-text text-transparent bg-gradient-to-br from-on-surface to-on-surface-variant">
              Descubra o que está
            </span>
            <span className="block bg-clip-text text-transparent bg-gradient-to-r from-secondary via-primary to-tertiary">
              travando sua comunicação
            </span>
          </h1>
          <p className="text-on-surface-variant text-base md:text-lg leading-relaxed max-w-2xl">
            Envie um vídeo e receba um relatório completo com coaching
            personalizado e um plano de 12 semanas para destravar sua oratória.
          </p>
          <div className="flex flex-wrap gap-2">
            {FEATURE_CHIPS.map((f) => (
              <span
                key={f.label}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs text-on-surface-variant bg-surface-container-high ghost-border"
              >
                <span className="material-symbols-outlined text-secondary text-base">
                  {f.icon}
                </span>
                {f.label}
              </span>
            ))}
          </div>
        </section>

        {/* Uploader */}
        <section>
          <VideoUploader
            onUploadComplete={(id) => router.push(`/evaluate/${id}/context`)}
          />
        </section>

        {/* Highlights */}
        <section className="grid md:grid-cols-3 gap-4 md:gap-5">
          <div className="rounded-2xl bg-surface-container-low p-6 ghost-border">
            <span className="material-symbols-outlined text-secondary text-3xl mb-3 block">
              bolt
            </span>
            <h3 className="font-headline text-lg font-bold mb-1.5">
              Análise em minutos
            </h3>
            <p className="text-sm text-on-surface-variant leading-relaxed">
              IA processa postura, voz, gestos e fluência em ~2 minutos.
            </p>
          </div>
          <div className="rounded-2xl bg-surface-container-low p-6 ghost-border">
            <span className="material-symbols-outlined text-secondary text-3xl mb-3 block">
              psychology
            </span>
            <h3 className="font-headline text-lg font-bold mb-1.5">
              Coaching personalizado
            </h3>
            <p className="text-sm text-on-surface-variant leading-relaxed">
              Pontos fortes, 80/20 de melhorias e exercícios práticos.
            </p>
          </div>
          <div className="rounded-2xl bg-surface-container-low p-6 ghost-border">
            <span className="material-symbols-outlined text-tertiary text-3xl mb-3 block">
              timeline
            </span>
            <h3 className="font-headline text-lg font-bold mb-1.5">
              Plano de 12 semanas
            </h3>
            <p className="text-sm text-on-surface-variant leading-relaxed">
              Uma habilidade por semana — grave, revise, ajuste.
            </p>
          </div>
        </section>
      </div>
    </AppShell>
  );
}
