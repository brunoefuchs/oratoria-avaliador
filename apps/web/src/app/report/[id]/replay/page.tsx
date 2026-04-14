"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { VideoPlayer } from "@/components/video-player";
import { AppShell } from "@/components/app-shell";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8002";

export default function ReplayPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_URL}/evaluations/${id}/replay`)
      .then((r) => r.json())
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <AppShell maxWidth="2xl" showBack backHref={`/report/${id}`} backLabel="Relatório">
        <div className="min-h-[50vh] flex items-center justify-center">
          <p className="text-on-surface-variant text-sm">
            Carregando replay...
          </p>
        </div>
      </AppShell>
    );
  }

  if (!data?.video_url) {
    return (
      <AppShell maxWidth="md" showBack backHref={`/report/${id}`} backLabel="Relatório">
        <div className="min-h-[40vh] flex flex-col items-center justify-center gap-4 text-center">
          <span className="material-symbols-outlined text-on-surface-variant text-5xl">
            movie_filter
          </span>
          <p className="text-on-surface-variant">
            Vídeo não disponível para replay.
          </p>
          <button
            onClick={() => router.push(`/report/${id}`)}
            className="bg-ai-pulse text-on-primary font-bold px-6 py-3 rounded-full shadow-cta-glow active:scale-95 transition"
          >
            Voltar ao relatório
          </button>
        </div>
      </AppShell>
    );
  }

  const stats = data.stats || {};

  return (
    <AppShell maxWidth="2xl" showBack backHref={`/report/${id}`} backLabel="Relatório">
      <div className="space-y-8">
        <header className="space-y-3">
          <span className="font-label text-xs uppercase tracking-[0.3em] text-secondary/80">
            Seu espelho inteligente
          </span>
          <h1 className="font-headline text-3xl md:text-5xl font-extrabold tracking-tight">
            Replay com
            <br />
            <span className="bg-clip-text text-transparent bg-gradient-to-r from-secondary to-primary">
              marcadores de IA
            </span>
          </h1>
          <p className="text-on-surface-variant">
            Clique nos marcadores para pular direto para os momentos-chave.
          </p>
        </header>

        <VideoPlayer
          videoUrl={data.video_url}
          events={data.events || []}
          duration={data.duration_seconds || 0}
        />

        {/* Stats summary */}
        <section className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="rounded-2xl bg-surface-container-low p-4 text-center ghost-border">
            <p className="font-headline text-3xl font-bold text-error">
              {stats.total_clusters ?? 0}
            </p>
            <p className="text-xs text-on-surface-variant mt-1">Clusters</p>
          </div>
          <div className="rounded-2xl bg-surface-container-low p-4 text-center ghost-border">
            <p className="font-headline text-3xl font-bold text-tertiary">
              {stats.total_fillers ?? 0}
            </p>
            <p className="text-xs text-on-surface-variant mt-1">
              Vícios isolados
            </p>
          </div>
          <div className="rounded-2xl bg-surface-container-low p-4 text-center ghost-border">
            <p className="font-headline text-3xl font-bold text-secondary">
              {stats.pausas_estrategicas ?? 0}
            </p>
            <p className="text-xs text-on-surface-variant mt-1">
              Pausas estratégicas
            </p>
          </div>
          <div className="rounded-2xl bg-surface-container-low p-4 text-center ghost-border">
            <p className="font-headline text-3xl font-bold text-tertiary/80">
              {stats.pausas_hesitacao ?? 0}
            </p>
            <p className="text-xs text-on-surface-variant mt-1">Hesitações</p>
          </div>
        </section>

        {stats.olhar_baixo_pct && stats.olhar_baixo_pct > 10 && (
          <div className="rounded-2xl bg-tertiary/10 p-5 ghost-border flex items-start gap-3">
            <span className="material-symbols-outlined text-tertiary">
              visibility_off
            </span>
            <p className="text-sm text-on-surface leading-relaxed">
              Você passou{" "}
              <strong className="text-tertiary">
                {Math.round(stats.olhar_baixo_pct)}%
              </strong>{" "}
              do tempo olhando para baixo (ideal: menos de 10%).
            </p>
          </div>
        )}

        <div className="rounded-2xl bg-surface-container-low p-5 ghost-border">
          <p className="font-label text-[10px] uppercase tracking-[0.3em] text-secondary mb-2">
            Como usar
          </p>
          <p className="text-sm text-on-surface-variant leading-relaxed">
            Cada lane mostra um tipo de evento. Clique em qualquer marcador
            para pular para aquele momento do vídeo.
          </p>
        </div>
      </div>
    </AppShell>
  );
}
