"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ScoreCard } from "@/components/score-card";
import { StarRating } from "@/components/star-rating";
import { AppShell } from "@/components/app-shell";
import { fetchReport, submitRating, createShare } from "@/lib/api-client";

const DIMENSION_LABELS: Record<string, string> = {
  variety: "Variedade Vocal",
  voice: "Voz e Dicção",
  gesture: "Presença Visual",
  posture: "Postura e Presença",
  fillers: "Clareza Verbal",
};

const DIMENSION_ORDER = ["variety", "voice", "gesture", "posture", "fillers"];

function getScoreTone(score: number) {
  if (score >= 70) return "text-secondary";
  if (score >= 40) return "text-tertiary";
  return "text-error";
}

function getCongruenceTone(score: number) {
  if (score >= 70) return "text-secondary";
  if (score >= 40) return "text-tertiary";
  return "text-error";
}

export default function ReportPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [shareStatus, setShareStatus] = useState<string | null>(null);

  useEffect(() => {
    fetchReport(id)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <AppShell maxWidth="lg" showBack backHref="/" backLabel="Início">
        <div className="min-h-[50vh] flex items-center justify-center">
          <p className="text-on-surface-variant text-sm">
            Carregando relatório...
          </p>
        </div>
      </AppShell>
    );
  }

  if (error || !data) {
    return (
      <AppShell maxWidth="md" showBack backHref="/" backLabel="Início">
        <div className="min-h-[40vh] flex flex-col items-center justify-center gap-4 text-center">
          <span className="material-symbols-outlined text-error text-5xl">
            error
          </span>
          <p className="text-error">{error || "Relatório não encontrado"}</p>
          <button
            onClick={() => router.push("/")}
            className="bg-ai-pulse text-on-primary font-bold px-6 py-3 rounded-full shadow-cta-glow active:scale-95 transition"
          >
            Voltar
          </button>
        </div>
      </AppShell>
    );
  }

  const report = data.report || {};
  const resumo = report.resumo || report.summary || "";
  const forcas = report.forcas || [];
  const melhorias = report.melhorias_80_20 || [];
  const dimensoes = report.dimensoes || report.dimension_feedback || {};
  const plano = report.plano_12_semanas || [];
  const mensagemFinal = report.mensagem_final || "";

  const sortedDimensions = DIMENSION_ORDER.filter(
    (d) => d in (data.dimension_scores || {})
  );

  const handleShare = async () => {
    try {
      const result = await createShare(id);
      const shareUrl = `${window.location.origin}/report/${id}/shared?token=${result.share_token}`;
      await navigator.clipboard.writeText(shareUrl);
      setShareStatus("Link copiado!");
      setTimeout(() => setShareStatus(null), 2500);
    } catch {
      setShareStatus("Erro ao gerar link.");
      setTimeout(() => setShareStatus(null), 2500);
    }
  };

  return (
    <AppShell maxWidth="2xl" showBack backHref="/" backLabel="Início">
      <div className="space-y-10 md:space-y-14">
        {/* Score Hero */}
        <section className="rounded-3xl bg-surface-container-low p-6 md:p-10 stage-ambient relative overflow-hidden">
          <span className="font-label text-xs uppercase tracking-[0.3em] text-secondary/80">
            Seu relatório · The Resonant Stage
          </span>
          <div className="mt-4 flex flex-col md:flex-row md:items-end md:justify-between gap-6">
            <div>
              <h1 className="font-headline text-3xl md:text-5xl font-extrabold tracking-tight leading-tight">
                Sua performance foi
                <br />
                <span className="bg-clip-text text-transparent bg-gradient-to-r from-secondary to-primary">
                  iluminada pela IA
                </span>
              </h1>
              {resumo && (
                <p className="mt-5 text-on-surface-variant leading-relaxed max-w-xl">
                  {resumo}
                </p>
              )}
            </div>
            <div className="shrink-0 flex items-baseline gap-2">
              <span
                className={`font-headline text-6xl md:text-8xl font-extrabold ${getScoreTone(
                  data.overall_score
                )}`}
              >
                {data.overall_score}
              </span>
              <span className="text-on-surface-variant text-2xl">/100</span>
            </div>
          </div>
          <div className="absolute bottom-0 left-0 right-0 fluency-wave opacity-60" />
        </section>

        {/* Forças */}
        {forcas.length > 0 && (
          <section className="space-y-4">
            <div className="flex items-center gap-3">
              <span className="material-symbols-outlined text-secondary text-2xl">
                bolt
              </span>
              <h2 className="font-headline text-2xl md:text-3xl font-bold tracking-tight">
                Pontos Fortes
              </h2>
            </div>
            <div className="grid md:grid-cols-2 gap-4">
              {forcas.map((forca: any, i: number) => (
                <article
                  key={i}
                  className="rounded-2xl bg-surface-container-low p-5 ghost-border"
                >
                  <p className="font-headline text-lg font-bold text-on-surface">
                    {forca.titulo}
                  </p>
                  <p className="mt-2 text-sm text-on-surface-variant leading-relaxed">
                    {forca.descricao}
                  </p>
                  {forca.impacto && (
                    <p className="mt-3 text-xs text-secondary italic border-l-2 border-secondary/40 pl-3">
                      {forca.impacto}
                    </p>
                  )}
                </article>
              ))}
            </div>
          </section>
        )}

        {/* Dimensões */}
        <section className="space-y-4">
          <div className="flex items-center gap-3">
            <span className="material-symbols-outlined text-secondary text-2xl">
              analytics
            </span>
            <h2 className="font-headline text-2xl md:text-3xl font-bold tracking-tight">
              Dimensões analisadas
            </h2>
          </div>
          <p className="text-on-surface-variant text-sm">
            Clique em qualquer dimensão para ver métricas e feedback detalhados.
          </p>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 md:gap-4">
            {sortedDimensions.map((dimension) => {
              const score = data.dimension_scores[dimension] as number;
              const feedback = dimensoes[dimension];
              return (
                <ScoreCard
                  key={dimension}
                  title={DIMENSION_LABELS[dimension] || dimension}
                  dimensionKey={dimension}
                  score={score}
                  summary={feedback?.dica || feedback?.tip}
                  onClick={() => router.push(`/report/${id}/${dimension}`)}
                />
              );
            })}
          </div>

          {/* Locked archetype */}
          <div className="rounded-2xl bg-surface-container-low p-4 flex items-center gap-4 ghost-border opacity-70">
            <div className="w-10 h-10 rounded-full bg-surface-container-highest flex items-center justify-center ghost-border">
              <span className="material-symbols-outlined text-tertiary">
                lock
              </span>
            </div>
            <div>
              <p className="text-sm font-semibold text-on-surface">
                Arquétipos Vocais
              </p>
              <p className="text-xs text-on-surface-variant">
                Recurso avançado · em breve
              </p>
            </div>
          </div>
        </section>

        {/* Melhorias 80/20 */}
        {melhorias.length > 0 && (
          <section className="space-y-4">
            <div>
              <div className="flex items-center gap-3">
                <span className="material-symbols-outlined text-tertiary text-2xl">
                  target
                </span>
                <h2 className="font-headline text-2xl md:text-3xl font-bold tracking-tight">
                  Top Melhorias
                </h2>
              </div>
              <p className="text-on-surface-variant text-sm mt-1">
                Regra 80/20 · as mudanças que vão gerar o maior impacto.
              </p>
            </div>
            <div className="space-y-3">
              {melhorias
                .slice()
                .sort(
                  (a: any, b: any) => (a.prioridade || 0) - (b.prioridade || 0)
                )
                .map((melhoria: any, i: number) => (
                  <details
                    key={i}
                    className="group rounded-2xl bg-surface-container-low ghost-border overflow-hidden"
                  >
                    <summary className="cursor-pointer list-none flex items-start gap-4 p-5 hover:bg-surface-container-high transition-colors">
                      <div className="w-10 h-10 rounded-xl bg-ai-pulse text-on-primary font-headline font-bold flex items-center justify-center shrink-0 shadow-cta-glow">
                        {i + 1}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-headline text-lg font-bold text-on-surface">
                          {melhoria.titulo}
                        </p>
                      </div>
                      <span className="material-symbols-outlined text-on-surface-variant group-open:rotate-180 transition-transform">
                        expand_more
                      </span>
                    </summary>
                    <div className="px-5 pb-5 pl-20 space-y-3">
                      <p className="text-sm text-on-surface-variant leading-relaxed">
                        {melhoria.descricao}
                      </p>
                      {melhoria.exercicio && (
                        <div className="rounded-xl bg-surface-container-high p-4 ghost-border">
                          <p className="font-label text-[10px] uppercase tracking-[0.2em] text-tertiary">
                            Exercício prático
                          </p>
                          <p className="mt-1 text-sm text-on-surface leading-relaxed">
                            {melhoria.exercicio}
                          </p>
                        </div>
                      )}
                    </div>
                  </details>
                ))}
            </div>
          </section>
        )}

        {/* Congruência */}
        {data.detailed_metrics?.congruence?.total_contradicoes > 0 && (
          <section className="rounded-2xl bg-surface-container-low p-6 ghost-border space-y-4">
            <div className="flex items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <span className="material-symbols-outlined text-secondary text-2xl">
                  balance
                </span>
                <h2 className="font-headline text-xl md:text-2xl font-bold tracking-tight">
                  Congruência corpo-voz
                </h2>
              </div>
              <span
                className={`font-headline text-3xl md:text-4xl font-bold ${getCongruenceTone(
                  data.detailed_metrics.congruence.score
                )}`}
              >
                {data.detailed_metrics.congruence.score}
              </span>
            </div>
            <div className="space-y-2">
              {data.detailed_metrics.congruence.contradicoes.map(
                (c: any, i: number) => (
                  <p
                    key={i}
                    className="flex items-start gap-2 text-sm text-on-surface-variant"
                  >
                    <span className="material-symbols-outlined text-tertiary text-base mt-0.5">
                      flash_on
                    </span>
                    <span>{c.descricao}</span>
                  </p>
                )
              )}
            </div>
          </section>
        )}

        {/* Arco da Performance */}
        {data.detailed_metrics?.temporal?.disponivel && (
          <section className="space-y-4">
            <div>
              <div className="flex items-center gap-3">
                <span className="material-symbols-outlined text-secondary text-2xl">
                  timeline
                </span>
                <h2 className="font-headline text-2xl md:text-3xl font-bold tracking-tight">
                  Arco da Performance
                </h2>
              </div>
              <p className="text-on-surface-variant text-sm mt-1">
                {data.detailed_metrics.temporal.padrao_descricao}
              </p>
            </div>
            <div className="grid grid-cols-3 gap-3 md:gap-4">
              {["abertura", "meio", "fechamento"].map((terco) => {
                const t = data.detailed_metrics.temporal.por_terco?.[terco];
                if (!t) return null;
                return (
                  <div
                    key={terco}
                    className="rounded-2xl bg-surface-container-low p-4 md:p-6 text-center ghost-border"
                  >
                    <p
                      className={`font-headline text-3xl md:text-4xl font-bold ${getScoreTone(
                        t.score
                      )}`}
                    >
                      {t.score}
                    </p>
                    <p className="text-xs font-label uppercase tracking-[0.2em] text-on-surface-variant mt-2 capitalize">
                      {terco}
                    </p>
                    {t.fillers > 0 && (
                      <p className="text-xs text-on-surface-variant/70 mt-1">
                        {t.fillers} vício{t.fillers > 1 ? "s" : ""}
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {/* Plano de 12 Semanas */}
        {plano.length > 0 && (
          <section className="space-y-4">
            <div>
              <div className="flex items-center gap-3">
                <span className="material-symbols-outlined text-secondary text-2xl">
                  event_note
                </span>
                <h2 className="font-headline text-2xl md:text-3xl font-bold tracking-tight">
                  Plano de 12 Semanas
                </h2>
              </div>
              <p className="text-on-surface-variant text-sm mt-1">
                Uma habilidade por semana · grave, revise, ajuste.
              </p>
            </div>
            <div className="grid md:grid-cols-2 gap-3">
              {plano.map((item: any, i: number) => (
                <div
                  key={i}
                  className="flex gap-4 rounded-2xl bg-surface-container-low p-4 md:p-5 ghost-border"
                >
                  <div className="flex flex-col items-center justify-center min-w-[56px] rounded-xl bg-surface-container-high px-2 py-2 text-xs font-bold text-secondary ghost-border">
                    <span className="font-label uppercase tracking-[0.15em] text-[9px] text-on-surface-variant">
                      Sem
                    </span>
                    <span className="font-headline text-lg">
                      {item.semana}
                    </span>
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-semibold text-on-surface">
                      {item.foco}
                    </p>
                    <p className="mt-1 text-xs text-on-surface-variant leading-relaxed">
                      {item.exercicio}
                    </p>
                    {item.meta && (
                      <p className="mt-2 text-xs text-tertiary italic">
                        Meta: {item.meta}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Dimensoes incompletas */}
        {data.incomplete_dimensions?.length > 0 && (
          <div className="rounded-2xl bg-tertiary/10 p-4 text-sm text-tertiary ghost-border flex items-start gap-3">
            <span className="material-symbols-outlined">warning</span>
            <span>
              Algumas dimensões não puderam ser analisadas:{" "}
              <strong>
                {data.incomplete_dimensions
                  .map((d: string) => DIMENSION_LABELS[d] || d)
                  .join(", ")}
              </strong>
            </span>
          </div>
        )}

        {/* Mensagem Final */}
        {mensagemFinal && (
          <section className="rounded-3xl bg-surface-container-high p-6 md:p-8 ghost-border relative overflow-hidden">
            <span className="material-symbols-outlined text-tertiary text-4xl mb-3 opacity-50">
              format_quote
            </span>
            <p className="font-headline text-lg md:text-xl leading-relaxed text-on-surface italic">
              &ldquo;{mensagemFinal}&rdquo;
            </p>
            <span className="material-symbols-outlined absolute -bottom-4 -right-4 text-[120px] text-tertiary opacity-5">
              record_voice_over
            </span>
          </section>
        )}

        {/* CTAs */}
        <section className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <button
            onClick={() => router.push(`/report/${id}/replay`)}
            className="flex flex-col items-center gap-2 rounded-2xl bg-surface-container-low p-5 ghost-border hover:bg-surface-container-high transition active:scale-95 text-center"
          >
            <span className="material-symbols-outlined text-secondary text-2xl">
              movie
            </span>
            <span className="text-xs md:text-sm font-semibold text-on-surface">
              Replay marcado
            </span>
          </button>
          <button
            onClick={() => router.push("/evolution")}
            className="flex flex-col items-center gap-2 rounded-2xl bg-surface-container-low p-5 ghost-border hover:bg-surface-container-high transition active:scale-95 text-center"
          >
            <span className="material-symbols-outlined text-secondary text-2xl">
              insights
            </span>
            <span className="text-xs md:text-sm font-semibold text-on-surface">
              Ver evolução
            </span>
          </button>
          <button
            onClick={() => router.push("/")}
            className="flex flex-col items-center gap-2 rounded-2xl bg-surface-container-low p-5 ghost-border hover:bg-surface-container-high transition active:scale-95 text-center"
          >
            <span className="material-symbols-outlined text-tertiary text-2xl">
              videocam
            </span>
            <span className="text-xs md:text-sm font-semibold text-on-surface">
              Gravar novamente
            </span>
          </button>
          <button
            onClick={handleShare}
            className="flex flex-col items-center gap-2 rounded-2xl bg-surface-container-low p-5 ghost-border hover:bg-surface-container-high transition active:scale-95 text-center relative"
          >
            <span className="material-symbols-outlined text-on-surface-variant text-2xl">
              share
            </span>
            <span className="text-xs md:text-sm font-semibold text-on-surface">
              {shareStatus || "Compartilhar"}
            </span>
          </button>
        </section>

        {/* Rating */}
        <section>
          <StarRating
            onSubmit={(rating, comment) => submitRating(id, rating, comment)}
          />
        </section>
      </div>
    </AppShell>
  );
}
