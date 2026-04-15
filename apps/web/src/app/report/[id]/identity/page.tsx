"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { fetchReport } from "@/lib/api-client";
import type { IdentityData } from "@/lib/types/report";

const VICIO_LABELS: Record<string, string> = {
  vitimizacao: "Vitimização",
  rejeicao: "Rejeição",
  inseguranca: "Insegurança",
  validacao: "Busca por validação",
  comparacao: "Comparação",
};

function getTone(score: number) {
  if (score >= 70) return { accent: "text-secondary", bar: "bg-secondary" };
  if (score >= 40) return { accent: "text-tertiary", bar: "bg-tertiary" };
  return { accent: "text-error", bar: "bg-error" };
}

export default function IdentityDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const [data, setData] = useState<IdentityData | null | undefined>(undefined);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchReport(id)
      .then((report) => setData(report?.detailed_metrics?.identity ?? null))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <AppShell maxWidth="lg" showBack backHref={`/report/${id}`} backLabel="Voltar ao relatório">
        <div className="min-h-[40vh] flex items-center justify-center">
          <p className="text-on-surface-variant text-sm">Carregando...</p>
        </div>
      </AppShell>
    );
  }

  if (!data) {
    return (
      <AppShell maxWidth="lg" showBack backHref={`/report/${id}`} backLabel="Voltar ao relatório">
        <div className="min-h-[40vh] flex items-center justify-center text-center">
          <div>
            <p className="text-on-surface mb-2">Análise de identidade indisponível</p>
            <p className="text-xs text-on-surface-variant">
              Este vídeo foi processado antes da análise de identidade ou o transcript não tinha sinais suficientes.
            </p>
          </div>
        </div>
      </AppShell>
    );
  }

  const tone = getTone(data.score);

  return (
    <AppShell maxWidth="lg" showBack backHref={`/report/${id}`} backLabel="Voltar ao relatório">
      <div className="space-y-8">
        <header className="flex items-start justify-between gap-6">
          <div>
            <span className="font-label text-xs uppercase tracking-[0.3em] text-on-surface-variant">
              Sub-dimensão · Análise completa
            </span>
            <h1 className="font-headline text-3xl md:text-4xl font-extrabold mt-2">
              Sua Identidade
            </h1>
          </div>
          <div className="text-right">
            <span className={`font-headline text-5xl md:text-6xl font-extrabold ${tone.accent}`}>
              {data.score}
            </span>
            <span className="text-on-surface-variant text-xl">/100</span>
          </div>
        </header>

        <div className="h-2 w-full rounded-full bg-surface-container overflow-hidden">
          <div
            className={`h-full rounded-full ${tone.bar} transition-all`}
            style={{ width: `${Math.min(100, Math.max(0, data.score))}%` }}
          />
        </div>

        <section className="rounded-2xl bg-surface-container-low p-6 ghost-border">
          <h2 className="font-headline text-lg font-bold mb-3">Diagnóstico</h2>
          <p className="text-sm text-on-surface leading-relaxed">{data.diagnostico}</p>
        </section>

        <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="rounded-2xl bg-surface-container-low p-5 ghost-border">
            <p className="text-xs font-label uppercase tracking-wider text-on-surface-variant mb-1">
              Frases de autoridade
            </p>
            <p className="font-headline text-3xl font-bold text-secondary">
              {data.autoridade_count}
            </p>
            <p className="text-xs text-on-surface-variant mt-2">
              Posicionamento ativo na fala
            </p>
          </div>
          <div className="rounded-2xl bg-surface-container-low p-5 ghost-border">
            <p className="text-xs font-label uppercase tracking-wider text-on-surface-variant mb-1">
              Vícios emocionais
            </p>
            <p className="font-headline text-3xl font-bold text-tertiary">
              {data.total_vicios}
            </p>
            <p className="text-xs text-on-surface-variant mt-2">
              Vitimização, insegurança, busca por validação
            </p>
          </div>
          <div className="rounded-2xl bg-surface-container-low p-5 ghost-border">
            <p className="text-xs font-label uppercase tracking-wider text-on-surface-variant mb-1">
              Razão autoridade/vítima
            </p>
            <p className="font-headline text-3xl font-bold text-on-surface">
              {data.autoridade_ratio.toFixed(2)}x
            </p>
            <p className="text-xs text-on-surface-variant mt-2">
              {data.autoridade_ratio >= 2
                ? "Posicionamento forte"
                : data.autoridade_ratio >= 1
                ? "Equilíbrio"
                : "Sinal de fragilidade"}
            </p>
          </div>
        </section>

        {data.vicio_dominante && (
          <section className="rounded-2xl bg-tertiary/10 p-5 ghost-border">
            <p className="font-headline text-base font-bold text-tertiary">
              Vício dominante:{" "}
              {VICIO_LABELS[data.vicio_dominante] ?? data.vicio_dominante}
            </p>
            <p className="text-xs text-on-surface-variant mt-2 italic">
              Padrão emocional mais frequente identificado no transcript.
            </p>
          </section>
        )}

        {data.exemplos && data.exemplos.length > 0 && (
          <section>
            <h2 className="font-headline text-lg font-bold mb-3">
              Exemplos do seu transcript
            </h2>
            <ul className="space-y-3">
              {data.exemplos.map((ex, i) => (
                <li
                  key={i}
                  className="rounded-2xl bg-surface-container-low p-4 ghost-border"
                >
                  <p className="text-sm italic text-on-surface mb-2">
                    &ldquo;{ex.texto}&rdquo;
                  </p>
                  <p className="text-xs font-label uppercase tracking-wider text-on-surface-variant">
                    {ex.tipo === "autoridade"
                      ? "Posicionamento ativo"
                      : "Padrão de vício"}
                    {ex.timestamp != null && ` · ${Math.floor(ex.timestamp)}s`}
                  </p>
                </li>
              ))}
            </ul>
          </section>
        )}
      </div>
    </AppShell>
  );
}
