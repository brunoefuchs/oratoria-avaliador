"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect } from "react";
import { ProcessingStatus } from "@/components/processing-status";
import { AppShell } from "@/components/app-shell";
import { useEvaluationStatus } from "@/hooks/use-evaluation-status";

export default function ProcessingPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;
  const { data, isLoading, error } = useEvaluationStatus(id);

  useEffect(() => {
    if (!data) return;
    if (data.status === "completed" || data.status === "analyzed") {
      router.push(`/report/${id}`);
    }
  }, [data, id, router]);

  if (isLoading) {
    return (
      <AppShell maxWidth="md">
        <div className="min-h-[60vh] flex flex-col items-center justify-center gap-3">
          <div className="w-12 h-12 rounded-full bg-ai-pulse flex items-center justify-center shadow-cta-glow animate-glow-pulse">
            <span className="material-symbols-outlined text-on-primary">
              auto_awesome
            </span>
          </div>
          <p className="text-on-surface-variant text-sm">Carregando...</p>
        </div>
      </AppShell>
    );
  }

  if (error) {
    return (
      <AppShell maxWidth="md">
        <div className="space-y-5">
          <div className="rounded-2xl bg-error-container/20 p-6 ghost-border text-center space-y-2">
            <span className="material-symbols-outlined text-error text-4xl">
              error
            </span>
            <p className="font-headline text-lg font-bold text-error">
              Erro ao buscar status
            </p>
            <p className="text-sm text-on-surface-variant">{error}</p>
          </div>
          <button
            onClick={() => router.push("/")}
            className="w-full bg-ai-pulse text-on-primary font-bold px-6 py-3 rounded-full shadow-cta-glow active:scale-[0.98] transition"
          >
            Tentar novamente
          </button>
        </div>
      </AppShell>
    );
  }

  if (data?.status === "error") {
    return (
      <AppShell maxWidth="md">
        <div className="space-y-5">
          <div className="rounded-2xl bg-error-container/20 p-6 ghost-border text-center space-y-2">
            <span className="material-symbols-outlined text-error text-4xl">
              error
            </span>
            <p className="font-headline text-lg font-bold text-error">
              Erro no processamento
            </p>
            <p className="text-sm text-on-surface-variant">
              Houve um problema ao analisar seu vídeo. Por favor, tente novamente.
            </p>
          </div>
          <button
            onClick={() => router.push("/")}
            className="w-full bg-ai-pulse text-on-primary font-bold px-6 py-3 rounded-full shadow-cta-glow active:scale-[0.98] transition"
          >
            Enviar outro vídeo
          </button>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell maxWidth="md">
      <div className="space-y-10 md:space-y-12">
        <div className="text-center space-y-4 relative stage-ambient py-6">
          <div className="w-16 h-16 mx-auto rounded-full bg-ai-pulse flex items-center justify-center shadow-cta-glow animate-glow-pulse">
            <span
              className="material-symbols-outlined text-on-primary text-3xl"
              style={{ fontVariationSettings: "'FILL' 1" }}
            >
              auto_awesome
            </span>
          </div>
          <div className="space-y-2">
            <span className="font-label text-xs uppercase tracking-[0.3em] text-secondary">
              Análise em andamento
            </span>
            <h1 className="font-headline text-3xl md:text-4xl font-extrabold tracking-tight">
              Iluminando seu palco
            </h1>
            <p className="text-on-surface-variant text-sm">
              Isso pode levar alguns minutos — relaxe, a IA está trabalhando.
            </p>
          </div>
        </div>

        <ProcessingStatus
          substatus={data?.substatus ?? null}
          stepsCompleted={data?.progress?.steps_completed ?? 0}
        />
      </div>
    </AppShell>
  );
}
