"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { fetchReport } from "@/lib/api-client";

interface DiscourseArcData {
  score: number;
  discourse_type?: "lista" | "argumentacao" | "narrativa" | "explicativo";
  arc_label?: "incompleto" | "linear" | "arco_completo" | "circular_callback";
  tem_payoff?: boolean;
  tipo_payoff?: "insight" | "imagem" | "cta" | "licao" | null;
  callback_abertura_fechamento?: boolean;
  justificativa?: string;
  confidence?: number;
  criterios_atendidos?: {
    inicio_claro?: boolean;
    desenvolvimento?: boolean;
    fechamento?: boolean;
    transicoes?: boolean;
    profundidade?: boolean;
  };
  cost_usd?: number;
  latency_ms?: number;
}

const ARC_LABEL_TEXT: Record<string, { titulo: string; descricao: string }> = {
  incompleto: {
    titulo: "Arco incompleto",
    descricao: "Falta um dos elementos macro: início, desenvolvimento ou fechamento. Mensagem fica suspensa.",
  },
  linear: {
    titulo: "Arco linear",
    descricao: "Tem início, meio e fim, mas sem callback nem payoff identificável. Estrutura funcional mas sem amarração.",
  },
  arco_completo: {
    titulo: "Arco completo",
    descricao: "Estrutura íntegra com payoff (insight, imagem, CTA ou lição). Mensagem entrega valor concreto.",
  },
  circular_callback: {
    titulo: "Arco circular com callback",
    descricao: "Estrutura completa + payoff + retorno temático abrindo↔fechando. Técnica Matthew Dicks. Tipo mais sofisticado.",
  },
};

const DISCOURSE_TYPE_TEXT: Record<string, string> = {
  lista: "Você organizou em lista de pontos — formato reto, baixo storytelling.",
  argumentacao: "Argumentação — você defende um ponto com razões.",
  narrativa: "Narrativa — você conta uma história/jornada.",
  explicativo: "Explicativo — você ensina ou descreve um conceito.",
};

const PAYOFF_TEXT: Record<string, string> = {
  insight: "Insight — você articulou uma revelação ou aprendizado.",
  imagem: "Imagem sensorial — você criou uma cena concreta na cabeça da audiência.",
  cta: "CTA — você chamou a audiência pra ação clara.",
  licao: "Lição — você extraiu uma moral ou princípio.",
};

const CRITERIO_LABELS: Record<string, string> = {
  inicio_claro: "Início claro (apresenta tema/contexto/hook)",
  desenvolvimento: "Desenvolvimento (progride com tensão/exemplos)",
  fechamento: "Fechamento (resolve, sintetiza ou faz CTA)",
  transicoes: "Transições/conectivos entre seções",
  profundidade: "Profundidade (não fica raso)",
};

const DISCOURSE_ARC_INTRO =
  "Arco do Discurso mede a estrutura macro da sua fala: tem início claro, desenvolvimento, fechamento? Há um callback que retorna ao tema da abertura? Existe payoff (insight, imagem concreta, CTA ou lição) que entrega valor? Avaliação semântica via IA com rubric explícita (Toastmasters Pathways + TOEFL Topic Development + Matthew Dicks + Kindra Hall).";

function getTone(score: number) {
  if (score >= 70) return { accent: "text-secondary", bar: "bg-secondary" };
  if (score >= 40) return { accent: "text-tertiary", bar: "bg-tertiary" };
  return { accent: "text-error", bar: "bg-error" };
}

export default function DiscourseArcDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const [data, setData] = useState<DiscourseArcData | null | undefined>(undefined);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchReport(id)
      .then((report) => setData(report?.detailed_metrics?.discourse_arc ?? null))
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

  if (!data || data.score == null) {
    return (
      <AppShell maxWidth="lg" showBack backHref={`/report/${id}`} backLabel="Voltar ao relatório">
        <div className="min-h-[40vh] flex items-center justify-center text-center">
          <div>
            <p className="text-on-surface mb-2">Análise de arco do discurso indisponível</p>
            <p className="text-xs text-on-surface-variant">
              Esta análise só roda quando a família narrativa está ativada (NARRATIVE_FAMILY_ENABLED). Vídeos processados antes da Story 10.3 não têm este dado.
            </p>
          </div>
        </div>
      </AppShell>
    );
  }

  const tone = getTone(data.score);
  const arcInfo = data.arc_label ? ARC_LABEL_TEXT[data.arc_label] : null;
  const discourseTypeText = data.discourse_type ? DISCOURSE_TYPE_TEXT[data.discourse_type] : null;
  const payoffText = data.tipo_payoff ? PAYOFF_TEXT[data.tipo_payoff] : null;

  return (
    <AppShell maxWidth="lg" showBack backHref={`/report/${id}`} backLabel="Voltar ao relatório">
      <div className="space-y-8">
        <header className="flex items-start justify-between gap-6">
          <div>
            <span className="font-label text-xs uppercase tracking-[0.3em] text-on-surface-variant">
              Sub-dimensão · Família narrativa
            </span>
            <h1 className="font-headline text-3xl md:text-4xl font-extrabold mt-2">
              Arco do Discurso
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

        <section className="rounded-2xl bg-surface-container-low p-5 ghost-border">
          <h3 className="font-label text-xs uppercase tracking-[0.3em] text-secondary mb-2">
            O que é e como avaliamos
          </h3>
          <p className="text-sm text-on-surface-variant leading-relaxed">
            {DISCOURSE_ARC_INTRO}
          </p>
        </section>

        {arcInfo && (
          <section className="rounded-2xl bg-surface-container-low p-6 ghost-border">
            <h2 className="font-headline text-lg font-bold mb-2">{arcInfo.titulo}</h2>
            <p className="text-sm text-on-surface leading-relaxed">{arcInfo.descricao}</p>
          </section>
        )}

        {(discourseTypeText || data.callback_abertura_fechamento != null || data.tem_payoff != null) && (
          <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {discourseTypeText && (
              <div className="rounded-2xl bg-surface-container-low p-5 ghost-border">
                <p className="text-xs font-label uppercase tracking-wider text-on-surface-variant mb-1">
                  Tipo de discurso
                </p>
                <p className="font-headline text-lg font-bold text-on-surface mb-2 capitalize">
                  {data.discourse_type}
                </p>
                <p className="text-xs text-on-surface-variant leading-snug">
                  {discourseTypeText}
                </p>
              </div>
            )}
            <div className="rounded-2xl bg-surface-container-low p-5 ghost-border">
              <p className="text-xs font-label uppercase tracking-wider text-on-surface-variant mb-1">
                Callback abertura↔fechamento
              </p>
              <p className={`font-headline text-3xl font-bold ${data.callback_abertura_fechamento ? "text-secondary" : "text-on-surface-variant"}`}>
                {data.callback_abertura_fechamento ? "Sim" : "Não"}
              </p>
              <p className="text-xs text-on-surface-variant mt-2">
                {data.callback_abertura_fechamento
                  ? "Você fechou retomando a abertura. Técnica Matthew Dicks."
                  : "Sem retorno temático. Considere amarrar fim com algo da abertura."}
              </p>
            </div>
            <div className="rounded-2xl bg-surface-container-low p-5 ghost-border">
              <p className="text-xs font-label uppercase tracking-wider text-on-surface-variant mb-1">
                Payoff
              </p>
              <p className={`font-headline text-3xl font-bold ${data.tem_payoff ? "text-secondary" : "text-error"}`}>
                {data.tem_payoff ? "Sim" : "Não"}
              </p>
              <p className="text-xs text-on-surface-variant mt-2">
                {payoffText ?? (data.tem_payoff ? "Payoff identificado." : "Sem payoff claro — fala não entrega valor concreto.")}
              </p>
            </div>
          </section>
        )}

        {data.criterios_atendidos && (
          <section className="rounded-2xl bg-surface-container-low p-6 ghost-border">
            <h2 className="font-headline text-lg font-bold mb-4">Critérios da rubric</h2>
            <ul className="space-y-2">
              {Object.entries(data.criterios_atendidos).map(([key, value]) => (
                <li key={key} className="flex items-start gap-3">
                  <span
                    className={`material-symbols-outlined text-xl ${value ? "text-secondary" : "text-error"}`}
                  >
                    {value ? "check_circle" : "cancel"}
                  </span>
                  <span className="text-sm text-on-surface flex-1">
                    {CRITERIO_LABELS[key] ?? key}
                  </span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {data.justificativa && (
          <section className="rounded-2xl bg-surface-container-low p-6 ghost-border">
            <h2 className="font-headline text-lg font-bold mb-3">Justificativa da análise</h2>
            <p className="text-sm text-on-surface leading-relaxed italic">
              {data.justificativa}
            </p>
            <p className="text-xs text-on-surface-variant mt-3 not-italic">
              Avaliação automática com IA (Gemini 2.5 Flash) seguindo rubric Toastmasters Pathways + TOEFL Topic Development + Matthew Dicks + Kindra Hall. Citações são trechos do seu próprio transcript.
            </p>
          </section>
        )}

        {(data.cost_usd != null || data.confidence != null) && (
          <section className="text-xs text-on-surface-variant/70 grid grid-cols-2 md:grid-cols-3 gap-3 pt-2">
            {data.confidence != null && (
              <div>Confiança: {(data.confidence * 100).toFixed(0)}%</div>
            )}
            {data.cost_usd != null && (
              <div>Custo da análise: US$ {data.cost_usd.toFixed(4)}</div>
            )}
            {data.latency_ms != null && (
              <div>Latência IA: {(data.latency_ms / 1000).toFixed(1)}s</div>
            )}
          </section>
        )}
      </div>
    </AppShell>
  );
}
