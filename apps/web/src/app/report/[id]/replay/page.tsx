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
          Clique nos marcadores coloridos para ver os momentos-chave
        </p>
      </div>

      <VideoPlayer
        videoUrl={data.video_url}
        events={data.events || []}
        duration={data.duration_seconds || 0}
      />

      <div className="rounded-lg bg-blue-50 p-4 text-sm text-blue-700">
        <p className="font-medium">Como usar:</p>
        <ul className="mt-1 space-y-1 text-xs">
          <li>🔴 Vermelho = clusters de vicios de linguagem — onde voce travou</li>
          <li>🟡 Amarelo = trechos monotonos — onde a fala ficou previsivel</li>
          <li>🟢 Verde = pausas estrategicas — momentos de impacto</li>
        </ul>
      </div>
    </main>
  );
}
