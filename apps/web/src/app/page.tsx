"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { VideoUploader } from "@/components/video-uploader";
import { Onboarding } from "@/components/onboarding";

export default function Home() {
  const router = useRouter();
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const done = localStorage.getItem("oratoria_onboarding_done");
    if (!done) {
      setShowOnboarding(true);
    }
    // Gerar user_token se nao existe
    if (!localStorage.getItem("oratoria_user_token")) {
      localStorage.setItem("oratoria_user_token", crypto.randomUUID());
    }
    setReady(true);
  }, []);

  if (!ready) return null;

  if (showOnboarding) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center p-8">
        <Onboarding onComplete={() => setShowOnboarding(false)} />
      </main>
    );
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <div className="w-full max-w-xl space-y-8 text-center">
        <div className="space-y-3">
          <h1 className="text-4xl font-bold tracking-tight">
            Descubra o que esta travando sua comunicacao
          </h1>
          <p className="text-lg text-gray-600">
            Envie um video e receba um relatorio completo com coaching
            personalizado e um plano de 12 semanas para destravar sua oratoria.
          </p>
          <div className="flex flex-wrap justify-center gap-2 text-sm text-gray-500">
            <span>🎹 Variedade Vocal</span>
            <span>🎙️ Voz e Diccao</span>
            <span>👁️ Presenca Visual</span>
            <span>🧍 Postura</span>
            <span>💬 Clareza Verbal</span>
          </div>
        </div>

        <VideoUploader
          onUploadComplete={(id) => router.push(`/evaluate/${id}/context`)}
        />
      </div>
    </main>
  );
}
