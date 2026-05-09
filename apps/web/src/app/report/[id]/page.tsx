"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { StarRating } from "@/components/star-rating";
import { AppShell } from "@/components/app-shell";
import { OpeningCard } from "@/components/opening-card";
import { ScoreBreakdown } from "@/components/score-breakdown";
import { FacialCard } from "@/components/facial-card";
import { TonalityViz } from "@/components/tonality-viz";
import { NarrativeCard } from "@/components/narrative-card";
import { ConfidenceBadge } from "@/components/confidence-badge";
import { fetchReport, submitRating, createShare } from "@/lib/api-client";
import type { DimensionConfidence } from "@/lib/types/report";
import { CONFIDENCE_BADGES } from "@/lib/report-labels";

const DIMENSION_LABELS: Record<string, string> = {
  variety: "Variedade Vocal",
  voice: "Voz e Dicção",
  articulation: "Articulação",
  gesture: "Presença Visual",
  posture: "Postura e Presença",
  fillers: "Clareza Verbal",
  facial: "Expressão Facial",
  storytelling: "Storytelling",
  archetypes: "Arquétipos Vocais",
  tonality: "Tonalidade",
  identity: "Identidade",
  discourse_arc: "Arco do Discurso",
};

const DIMENSION_DESC: Record<string, string> = {
  voice: "Como sua voz está calibrada agora — ritmo médio, volume base, alcance melódico e estrutura de pausas.",
  variety: "Quanto você modula sua voz ao longo do tempo — se mantém igual ou cria altos e baixos que prendem atenção.",
  fillers: "Frequência de vícios de linguagem (né, tipo, ahn, sabe).",
  gesture: "Frequência, vocabulário e propósito dos gestos das mãos.",
  posture: "Estabilidade corporal, alinhamento e abertura postural.",
  facial: "Variação de expressão e contato visual com a câmera.",
  storytelling: "Abertura que prende, conexão entre ideias e gatilhos emocionais ativados.",
  archetypes: "Alternância entre os 4 modos de falar: Coach, Educador, Motivador e Amigo.",
  tonality: "Carga emocional da voz — o quanto transmite confiança, calor, energia ou tensão.",
  identity: "Coerência da persona ao longo do vídeo.",
  discourse_arc: "Estrutura macro: tem início, desenvolvimento e fechamento? Há callback ou payoff que conecta ponta a ponta?",
};

const DIMENSION_ORDER = ["variety", "voice", "gesture", "facial", "posture", "fillers"];

// Mapping inglês → PT usado pelas chaves do Gemini em report.dimensoes
const DIMENSION_TO_PT_KEY: Record<string, string> = {
  variety: "variedade",
  voice: "voz",
  gesture: "presenca_visual",
  posture: "postura",
  fillers: "clareza_verbal",
  facial: "expressao_facial",
};

const CONGRUENCE_EXPLAIN: Record<string, string> = {
  entusiasmo_vs_postura:
    "Sua voz transmite energia (range melódico amplo) mas o corpo fica fechado. Audiência sente que algo não bate — energia vocal sem abertura corporal cria sensação de teatro.",
  confianca_vs_olhar:
    "Volume forte indica autoridade, mas olhar pra baixo desmonta. Som diz 'eu mando aqui', visual diz 'estou inseguro'.",
  abertura_vs_volume:
    "Gestos amplos pedem voz amplificada. Quando o corpo abre mas o volume não acompanha, o espectador percebe descompasso (parece tímido performando).",
  urgencia_vs_parado:
    "Cadência rápida sugere urgência. Corpo parado anula o efeito — voz pede ação, corpo desmente.",
  sorriso_vs_tom_tenso:
    "Sorriso é o sinal universal de relaxamento. Quando aparece sobre voz tensa, vira sorriso forçado — cérebro detecta como teatralidade.",
  fala_rapida_vs_voz_plana:
    "Falar rápido sem variar pitch transmite ansiedade. Velocidade pede modulação pra criar engajamento; sem isso, vira fala monótona acelerada.",
  postura_forte_vs_voz_fraca:
    "Postura ereta projeta autoridade física. Voz baixa contradiz — corpo diz 'estou aqui', voz sussurra 'não me ouça'.",
  expressao_facial_vs_voz_apatica:
    "Sobrancelhas ativas indicam engajamento facial. Voz apática anula — rosto vivo + voz morta vira sinal de ensaio mecânico.",
  coach_vs_rosto_estatico:
    "Arquetipo Coach é diretivo, energético — pede expressão facial à altura. Quando a face fica estática enquanto a voz comanda, parece autoritarismo frio em vez de liderança calorosa.",
};

function getScoreTone(score: number) {
  if (score >= 70) return "text-secondary";
  if (score >= 40) return "text-tertiary";
  return "text-error";
}

const FAMILIES: Array<{
  key: "tecnica" | "presenca" | "narrativa";
  label: string;
  icon: string;
  desc: string;
  dims: string[];
  feedback: (score: number) => string;
}> = [
  {
    key: "tecnica",
    label: "Técnica Vocal",
    icon: "mic",
    desc: "Como sua voz funciona como instrumento.\nO que você fez bem e onde mira a próxima evolução.",
    dims: ["voice", "variety", "fillers"],
    feedback: (s) =>
      s >= 85
        ? "Sua voz é um instrumento afiado — cadência, range melódico e dicção em nível alto."
        : s >= 65
        ? "Boa base técnica. Há espaço pra ampliar variação intencional."
        : s >= 40
        ? "Técnica funcional, mas previsível. Alterne cadências e volumes pra criar contraste."
        : "Sua voz está em piloto automático. Quebre o padrão pra prender atenção.",
  },
  {
    key: "presenca",
    label: "Presença Física",
    icon: "accessibility_new",
    desc: "O que seu corpo diz paralelo à fala.\nGesto, postura e rosto somam ou contradizem a mensagem.",
    dims: ["gesture", "posture", "facial"],
    feedback: (s) =>
      s >= 85
        ? "Presença confiante — corpo, gestos e rosto reforçam o que você diz."
        : s >= 65
        ? "Boa presença. Refine gesto intencional e ocupe mais espaço visual."
        : s >= 40
        ? "Corpo poderia abrir mais — gesto repetitivo ou postura fechada está te limitando."
        : "Seu corpo está apagando sua mensagem. Ocupe mais espaço, seja maior que o quadro.",
  },
  {
    key: "narrativa",
    label: "Narrativa",
    icon: "auto_stories",
    desc: "Se sua mensagem está conectando ou só ocupando ar.\nMede o poder de prender atenção pela forma como o conteúdo é apresentado.",
    dims: ["storytelling", "archetypes", "tonality", "identity", "discourse_arc"],
    feedback: (s) =>
      s >= 85
        ? "Sua mensagem prende e transforma — abertura, estrutura e tonalidade alinhados."
        : s >= 65
        ? "Boa estrutura narrativa. Adicione frase-ponte ('a razão de eu te contar isso...') e variação de arquétipos pra amplificar."
        : s >= 40
        ? "Sua mensagem precisa de uma frase-ponte: 'a razão de eu estar te dizendo isso é...'"
        : "Você está dizendo palavras certas mas sem narrativa que conecte. Foque em prender atenção e conduzir até o ponto.",
  },
];

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
          <div className="flex flex-wrap items-center gap-3">
            <span className="font-label text-xs uppercase tracking-[0.3em] text-secondary/80">
              Seu relatório · The Resonant Stage
            </span>
            {data.detailed_metrics?.contexto && (
              <span
                className="inline-flex items-center gap-1.5 rounded-full bg-secondary/10 px-3 py-1 text-xs font-label uppercase tracking-wider text-secondary"
                title="Os pesos das dimensões são ajustados conforme o contexto declarado no questionário"
              >
                <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z"
                    clipRule="evenodd"
                  />
                </svg>
                Avaliado para: {data.detailed_metrics.contexto}
              </span>
            )}
          </div>
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
              {data.detailed_metrics?.congruence?.score != null && (() => {
                const cong = data.detailed_metrics.congruence;
                const score = cong.score;
                const total = cong.total_contradicoes ?? 0;
                const tier = score >= 90 ? {
                  label: "Verbal-Vocal-Visual alinhados: audiência sente verdade.",
                  bg: "bg-secondary/15 text-secondary border-secondary/30",
                  icon: "verified",
                } : score >= 70 ? {
                  label: "Pequenas incongruências entre o que diz e como mostra",
                  bg: "bg-tertiary/15 text-tertiary border-tertiary/30",
                  icon: "warning",
                } : {
                  label: "Sinais conflitantes prejudicam credibilidade",
                  bg: "bg-error/15 text-error border-error/30",
                  icon: "error",
                };
                return (
                  <button
                    type="button"
                    onClick={() => router.push(`/report/${id}/congruence`)}
                    className={`mt-4 inline-flex items-center gap-2 px-3 py-1.5 rounded-full border ${tier.bg} text-xs font-medium hover:opacity-90 transition-opacity`}
                  >
                    <span className="material-symbols-outlined text-base">
                      {tier.icon}
                    </span>
                    Congruência {score}/100 — {tier.label}
                    {total > 0 && (
                      <span className="opacity-70">
                        ({total} {total === 1 ? "alerta" : "alertas"})
                      </span>
                    )}
                  </button>
                );
              })()}
            </div>
            <div
              className={`shrink-0 ${getScoreTone(data.overall_score)}`}
            >
              <ScoreBreakdown
                overallScore={data.overall_score}
                dimensionScores={data.dimension_scores ?? {}}
                weights={data.detailed_metrics?.pesos_utilizados ?? null}
                contexto={data.detailed_metrics?.contexto ?? null}
              />
            </div>
          </div>
          <div className="absolute bottom-0 left-0 right-0 fluency-wave opacity-60" />
        </section>

        {/* Family scores (2026-04-29) — Look-Feel-Sound Triangle */}
        {data.family_scores && (
          <section className="space-y-4">
            <div className="flex items-center gap-3">
              <span className="material-symbols-outlined text-secondary text-2xl">
                category
              </span>
              <h2 className="font-headline text-2xl md:text-3xl font-bold tracking-tight">
                Famílias de Performance
              </h2>
            </div>
            <div className="space-y-4">
              {FAMILIES.map((fam) => {
                const score = data.family_scores?.[fam.key];
                const tone = getScoreTone(score ?? 0);
                return (
                  <article
                    key={fam.key}
                    className="rounded-2xl bg-surface-container-low ghost-border overflow-hidden"
                  >
                    {/* Header da família — score grande + descrição */}
                    <div className="p-6 border-b border-outline-variant/20">
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex items-start gap-4 flex-1 min-w-0">
                          <span className="material-symbols-outlined text-secondary text-4xl shrink-0">
                            {fam.icon}
                          </span>
                          <div className="flex-1 min-w-0">
                            <h3 className="font-headline text-xl md:text-2xl font-bold mb-1">
                              {fam.label}
                            </h3>
                            <p className="text-xs text-on-surface-variant uppercase tracking-wider mb-3 whitespace-pre-line">
                              {fam.desc}
                            </p>
                            <p className="text-sm text-on-surface leading-relaxed italic">
                              {score != null ? fam.feedback(score) : "Sem dados suficientes."}
                            </p>
                          </div>
                        </div>
                        <div className="text-right shrink-0">
                          <div className={`font-mono font-bold text-5xl md:text-6xl ${tone}`}>
                            {score ?? "—"}
                          </div>
                          <div className="text-xs text-on-surface-variant mt-1">/ 100</div>
                        </div>
                      </div>
                    </div>
                    {/* Sub-dimensões nested */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 p-4 bg-surface-container">
                      {fam.dims.map((dim) => {
                        const dimScore =
                          data.dimension_scores?.[dim] ??
                          data.detailed_metrics?.[dim]?.score;
                        const subTone = getScoreTone(dimScore ?? 0);
                        const label = DIMENSION_LABELS[dim] || dim;
                        if (dimScore == null) return null;
                        const confidence = (
                          data.dimension_confidence as DimensionConfidence | undefined
                        )?.[dim];
                        return (
                          <button
                            key={dim}
                            onClick={() => router.push(`/report/${id}/${dim}`)}
                            className="rounded-xl bg-surface-container-low p-3 hover:bg-surface-container-high transition-colors text-left flex flex-col relative"
                          >
                            <div className="flex items-baseline justify-between mb-1 gap-2">
                              <div className="text-xs text-on-surface-variant truncate flex-1">
                                {label}
                              </div>
                              <div className={`font-mono font-bold text-2xl ${subTone}`}>
                                {dimScore}
                              </div>
                            </div>
                            {DIMENSION_DESC[dim] && (
                              <p className="text-[11px] text-on-surface-variant/80 leading-snug mt-1">
                                {DIMENSION_DESC[dim]}
                              </p>
                            )}
                            {confidence && (
                              <div className="absolute top-2 right-2 pointer-events-none">
                                <ConfidenceBadge confidence={confidence} compact />
                              </div>
                            )}
                          </button>
                        );
                      })}
                    </div>
                    {fam.key === "tecnica" && (
                      <div className="px-4 pb-4 pt-2 bg-surface-container">
                        <p className="text-xs font-medium text-on-surface mb-1">
                          Combinação Voz + Variedade Vocal
                        </p>
                        <p className="text-xs text-on-surface-variant leading-relaxed whitespace-pre-line">
                          <span className="font-medium text-on-surface">Voz</span> = como sua voz está calibrada. <span className="font-medium text-on-surface">Variedade</span> = quanto ela muda ao longo do tempo.{"\n"}As duas trabalham juntas: voz forte sem variedade vira monótona; variedade sem base perde impacto.
                        </p>
                      </div>
                    )}
                  </article>
                );
              })}
            </div>
          </section>
        )}

        {/* Congruência (movido 2026-05-06: logo apos family cards pra
            cliente entender que e a "validacao" das 3 familias) */}
        {data.detailed_metrics?.congruence?.score != null && (
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
            <div className="rounded-xl bg-surface-container p-4 text-sm text-on-surface-variant leading-relaxed space-y-2">
              <p>
                <strong className="text-on-surface">Congruência</strong> mede se
                seus 3 canais de comunicação estão dizendo a mesma coisa:
              </p>
              <ul className="list-disc pl-5 space-y-1">
                <li><strong>Verbal</strong> — o que você fala (palavras)</li>
                <li><strong>Vocal</strong> — como você fala (tom, ritmo, energia)</li>
                <li><strong>Visual</strong> — o que seu corpo mostra (rosto, gesto, postura)</li>
              </ul>
              <p>
                Quando os 3 estão alinhados, a audiência sente verdade. Quando
                contradizem (ex: sorriso forçado + voz tensa), o cérebro do
                espectador detecta — mesmo que ele não saiba explicar.
              </p>
            </div>
            <div className="space-y-3">
              {(data.detailed_metrics.congruence.total_contradicoes ?? 0) === 0 ? (
                <div className="rounded-xl bg-secondary/10 border border-secondary/30 p-4 flex items-start gap-3">
                  <span className="material-symbols-outlined text-secondary text-xl mt-0.5">
                    verified
                  </span>
                  <div className="text-sm text-on-surface-variant leading-relaxed">
                    <p className="font-medium text-on-surface">
                      Nenhuma incongruência detectada.
                    </p>
                    <p className="mt-1">
                      Seus 3 canais (verbal, vocal e visual) estão alinhados.
                      Não houve sinais conflitantes — a mensagem que você fala,
                      o tom da voz e o que o corpo mostra dizem a mesma coisa.
                    </p>
                  </div>
                </div>
              ) : (
                <p className="text-xs uppercase tracking-wider text-on-surface-variant font-medium">
                  Alertas detectados
                </p>
              )}
              {data.detailed_metrics.congruence.contradicoes?.map(
                (c: any, i: number) => {
                  const explicacao = CONGRUENCE_EXPLAIN[c.id] ?? "";
                  return (
                    <div
                      key={i}
                      className="rounded-xl bg-tertiary/10 border border-tertiary/30 p-3 space-y-1.5"
                    >
                      <div className="flex items-start gap-2 text-sm">
                        <span className="material-symbols-outlined text-tertiary text-base mt-0.5">
                          flash_on
                        </span>
                        <span className="font-medium text-on-surface">
                          {c.descricao}
                        </span>
                      </div>
                      {explicacao && (
                        <p className="text-xs text-on-surface-variant leading-snug pl-7">
                          {explicacao}
                        </p>
                      )}
                    </div>
                  );
                }
              )}
            </div>
          </section>
        )}

        {/* Story 7.2 — Sua Abertura (antes das dimensões — momento crítico) */}
        <OpeningCard data={data.detailed_metrics?.opening} evaluationId={id} />

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

        {/* Section "Dimensões analisadas" + Locked archetype removidos
            (2026-05-06): info ja consolidada nas 3 family cards acima com
            sub-dims clickaveis. Archetypes ja existe como dimensao real,
            "lock em breve" estava obsoleto. */}

        {/* Story 7.4 — Expressão Facial (sub-dimensão qualitativa, junto com Identidade) */}
        <FacialCard data={data.detailed_metrics?.facial} />

        {/* Story 7.5 — Tonality VAD (5ª Vocal Foundation, sub-dimensão qualitativa) */}
        <TonalityViz data={data.detailed_metrics?.tonality} />

        {/* Story 7.3 — Narrativa (arquitetura da mensagem, sub-dimensão qualitativa) */}
        <NarrativeCard data={data.detailed_metrics?.storytelling} />

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
