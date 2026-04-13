"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { VideoPlayer } from "@/components/video-player";

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
      <main className="flex min-h-screen items-center justify-center">
        <p className="text-gray-500">Carregando replay...</p>
      </main>
    );
  }

  if (!data?.video_url) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-8">
        <p className="text-gray-500">Video nao disponivel para replay.</p>
        <button
          onClick={() => router.push(`/report/${id}`)}
          className="text-sm text-blue-600 hover:underline"
        >
          ← Voltar ao relatorio
        </button>
      </main>
    );
  }

  const stats = data.stats || {};

  return (
    <main className="mx-auto max-w-2xl p-6 space-y-6">
      <button
        onClick={() => router.push(`/report/${id}`)}
        className="text-sm text-blue-600 hover:underline"
      >
        ← Voltar ao relatorio
      </button>

      <div className="text-center space-y-1">
        <h1 className="text-xl font-bold">Seu Espelho Inteligente</h1>
        <p className="text-sm text-gray-500">
          Clique nos marcadores para ver os momentos-chave
        </p>
      </div>

      <VideoPlayer
        videoUrl={data.video_url}
        events={data.events || []}
        duration={data.duration_seconds || 0}
      />

      {/* Stats summary */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="rounded-xl bg-red-50 p-3 text-center ring-1 ring-red-200">
          <p className="text-2xl font-bold text-red-700">
            {stats.total_clusters ?? 0}
          </p>
          <p className="text-xs text-red-600">Clusters</p>
        </div>
        <div className="rounded-xl bg-orange-50 p-3 text-center ring-1 ring-orange-200">
          <p className="text-2xl font-bold text-orange-700">
            {stats.total_fillers ?? 0}
          </p>
          <p className="text-xs text-orange-600">Vicios isolados</p>
        </div>
        <div className="rounded-xl bg-emerald-50 p-3 text-center ring-1 ring-emerald-200">
          <p className="text-2xl font-bold text-emerald-700">
            {stats.pausas_estrategicas ?? 0}
          </p>
          <p className="text-xs text-emerald-600">Pausas estrategicas</p>
        </div>
        <div className="rounded-xl bg-amber-50 p-3 text-center ring-1 ring-amber-200">
          <p className="text-2xl font-bold text-amber-700">
            {stats.pausas_hesitacao ?? 0}
          </p>
          <p className="text-xs text-amber-600">Hesitacoes</p>
        </div>
      </div>

      {stats.olhar_baixo_pct && stats.olhar_baixo_pct > 10 && (
        <div className="rounded-lg bg-yellow-50 p-4 text-sm text-yellow-700 ring-1 ring-yellow-200">
          ⚠️ Voce passou <strong>{Math.round(stats.olhar_baixo_pct)}%</strong> do tempo olhando para baixo (ideal: menos de 10%)
        </div>
      )}

      <div className="rounded-lg bg-blue-50 p-4 text-xs text-blue-700">
        <p className="font-medium mb-1">Como usar:</p>
        <p>Cada lane mostra um tipo de evento. Clique em qualquer marcador para pular para aquele momento do video.</p>
      </div>
    </main>
  );
}
