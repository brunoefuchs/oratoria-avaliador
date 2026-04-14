"use client";

import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { saveContext } from "@/lib/api-client";
import { AppShell } from "@/components/app-shell";

const MEDOS = [
  { id: "dar_branco", label: "Esquecer o que ia falar (dar branco)" },
  { id: "julgamento", label: "Do que os outros vão dizer (julgamento)" },
  { id: "monotono", label: "Parecer monótono ou entediante" },
  { id: "nao_convencer", label: "Não conseguir convencer" },
  { id: "errar", label: "De errar" },
  { id: "parecer_diferente", label: "Parecer diferente de quem eu sou" },
  { id: "outro", label: "Outro" },
];

const MOTIVACOES = [
  { id: "redes_sociais", label: "Me posicionar nas redes sociais" },
  { id: "vender_mais", label: "Vender mais" },
  { id: "carreira", label: "Crescer na profissão/carreira" },
  { id: "palestrar", label: "Palestrar" },
  { id: "satisfacao_pessoal", label: "Satisfação pessoal" },
  { id: "outro", label: "Outro" },
];

const DESEJOS_TRANSMITIR = [
  { id: "confianca", label: "Confiança" },
  { id: "autoridade", label: "Autoridade" },
  { id: "credibilidade", label: "Credibilidade" },
  { id: "naturalidade", label: "Naturalidade" },
  { id: "seguranca", label: "Segurança" },
  { id: "outro", label: "Outro" },
];

const DESEJOS_MELHORAR = [
  { id: "diccao", label: "Dicção" },
  { id: "postura", label: "Postura" },
  { id: "gestual", label: "Gestual" },
  { id: "tom_de_voz", label: "Tom de voz" },
  { id: "clareza_fala", label: "Clareza na fala (ritmo, pausas, velocidade)" },
  { id: "outro", label: "Outro" },
];

const SENTIMENTO_LABELS = [
  "Muito nervoso",
  "Nervoso",
  "Neutro",
  "Confiante",
  "Muito confiante",
];

export default function ContextPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const [step, setStep] = useState(0);
  const [sentimento, setSentimento] = useState<number>(3);
  const [medos, setMedos] = useState<string[]>([]);
  const [motivacoes, setMotivacoes] = useState<string[]>([]);
  const [avaliadoAntes, setAvaliadoAntes] = useState<boolean | null>(null);
  const [desejoTransmitir, setDesejoTransmitir] = useState<string[]>([]);
  const [desejoMelhorar, setDesejoMelhorar] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);

  const toggleItem = (
    list: string[],
    setList: (v: string[]) => void,
    id: string
  ) => {
    setList(list.includes(id) ? list.filter((m) => m !== id) : [...list, id]);
  };

  const handleSubmit = async () => {
    setSaving(true);
    try {
      await saveContext(id, {
        sentimento,
        maior_medo: medos.length > 0 ? medos : undefined,
        motivacao: motivacoes.length > 0 ? motivacoes : undefined,
        avaliado_antes: avaliadoAntes ?? undefined,
        desejo_transmitir:
          desejoTransmitir.length > 0 ? desejoTransmitir : undefined,
        desejo_melhorar:
          desejoMelhorar.length > 0 ? desejoMelhorar : undefined,
      });
    } catch {
      // silent — questionário é opcional
    }
    router.push(`/processing/${id}`);
  };

  const handleSkip = () => router.push(`/processing/${id}`);
  const nextStep = () => setStep((s) => Math.min(s + 1, 5));

  const MultiSelect = ({
    options,
    selected,
    onToggle,
  }: {
    options: { id: string; label: string }[];
    selected: string[];
    onToggle: (id: string) => void;
  }) => (
    <div className="space-y-2">
      {options.map((opt) => {
        const isActive = selected.includes(opt.id);
        return (
          <button
            key={opt.id}
            onClick={() => onToggle(opt.id)}
            className={`w-full flex items-center gap-3 rounded-2xl px-4 py-3.5 text-left text-sm transition-all ghost-border ${
              isActive
                ? "bg-surface-container-high text-on-surface shadow-focus-ring"
                : "bg-surface-container-low text-on-surface-variant hover:bg-surface-container"
            }`}
          >
            <span
              className={`w-5 h-5 shrink-0 rounded-md flex items-center justify-center transition ${
                isActive
                  ? "bg-ai-pulse"
                  : "bg-surface-container-highest ghost-border-strong"
              }`}
            >
              {isActive && (
                <span className="material-symbols-outlined text-on-primary text-sm">
                  check
                </span>
              )}
            </span>
            <span>{opt.label}</span>
          </button>
        );
      })}
    </div>
  );

  return (
    <AppShell maxWidth="md" showBack backHref="/" backLabel="Início">
      <div className="space-y-7">
        <div className="flex gap-1.5">
          {[0, 1, 2, 3, 4, 5].map((i) => (
            <div
              key={i}
              className={`h-1 flex-1 rounded-full transition-colors ${
                i <= step ? "bg-secondary" : "bg-surface-container-high"
              }`}
            />
          ))}
        </div>

        <div className="space-y-1">
          <span className="font-label text-xs uppercase tracking-[0.3em] text-secondary/80">
            Contexto · {step + 1} de 6
          </span>
        </div>

        {/* Step 1: Sentimento */}
        {step === 0 && (
          <div className="space-y-6 text-center">
            <h2 className="font-headline text-2xl md:text-3xl font-extrabold tracking-tight leading-tight">
              Como você se sentiu gravando esse vídeo?
            </h2>
            <div className="grid grid-cols-5 gap-2">
              {[1, 2, 3, 4, 5].map((v) => (
                <button
                  key={v}
                  onClick={() => {
                    setSentimento(v);
                    nextStep();
                  }}
                  className={`flex flex-col items-center justify-center rounded-2xl aspect-square transition-all ghost-border ${
                    sentimento === v
                      ? "bg-ai-pulse text-on-primary shadow-cta-glow"
                      : "bg-surface-container-low hover:bg-surface-container-high text-on-surface"
                  }`}
                >
                  <span className="font-headline text-2xl font-bold">{v}</span>
                  <span className="text-[9px] leading-tight mt-1 px-1 text-center opacity-80">
                    {SENTIMENTO_LABELS[v - 1].split(" ").pop()}
                  </span>
                </button>
              ))}
            </div>
            <p className="text-xs text-on-surface-variant">
              1 = muito nervoso · 5 = muito confiante
            </p>
          </div>
        )}

        {/* Step 2 */}
        {step === 1 && (
          <div className="space-y-5">
            <h2 className="font-headline text-2xl md:text-3xl font-extrabold tracking-tight leading-tight">
              Qual seu maior medo ao se comunicar?
            </h2>
            <MultiSelect
              options={MEDOS}
              selected={medos}
              onToggle={(id) => toggleItem(medos, setMedos, id)}
            />
            <button
              onClick={nextStep}
              className="w-full bg-ai-pulse text-on-primary font-bold px-6 py-3.5 rounded-full shadow-cta-glow active:scale-[0.98] transition"
            >
              Continuar
            </button>
          </div>
        )}

        {/* Step 3 */}
        {step === 2 && (
          <div className="space-y-5">
            <h2 className="font-headline text-2xl md:text-3xl font-extrabold tracking-tight leading-tight">
              Por que você quer melhorar a comunicação?
            </h2>
            <MultiSelect
              options={MOTIVACOES}
              selected={motivacoes}
              onToggle={(id) => toggleItem(motivacoes, setMotivacoes, id)}
            />
            <button
              onClick={nextStep}
              className="w-full bg-ai-pulse text-on-primary font-bold px-6 py-3.5 rounded-full shadow-cta-glow active:scale-[0.98] transition"
            >
              Continuar
            </button>
          </div>
        )}

        {/* Step 4 */}
        {step === 3 && (
          <div className="space-y-5 text-center">
            <h2 className="font-headline text-2xl md:text-3xl font-extrabold tracking-tight leading-tight">
              Você já se avaliou antes?
            </h2>
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => {
                  setAvaliadoAntes(true);
                  nextStep();
                }}
                className="rounded-2xl bg-surface-container-low hover:bg-surface-container-high p-6 ghost-border transition active:scale-95"
              >
                <span className="material-symbols-outlined text-secondary text-3xl mb-2 block">
                  thumb_up
                </span>
                <span className="font-headline text-xl font-bold">Sim</span>
              </button>
              <button
                onClick={() => {
                  setAvaliadoAntes(false);
                  nextStep();
                }}
                className="rounded-2xl bg-surface-container-low hover:bg-surface-container-high p-6 ghost-border transition active:scale-95"
              >
                <span className="material-symbols-outlined text-tertiary text-3xl mb-2 block">
                  rocket_launch
                </span>
                <span className="font-headline text-xl font-bold">Não</span>
              </button>
            </div>
          </div>
        )}

        {/* Step 5 */}
        {step === 4 && (
          <div className="space-y-5">
            <h2 className="font-headline text-2xl md:text-3xl font-extrabold tracking-tight leading-tight">
              O que você deseja transmitir através da sua comunicação?
            </h2>
            <MultiSelect
              options={DESEJOS_TRANSMITIR}
              selected={desejoTransmitir}
              onToggle={(id) =>
                toggleItem(desejoTransmitir, setDesejoTransmitir, id)
              }
            />
            <button
              onClick={nextStep}
              className="w-full bg-ai-pulse text-on-primary font-bold px-6 py-3.5 rounded-full shadow-cta-glow active:scale-[0.98] transition"
            >
              Continuar
            </button>
          </div>
        )}

        {/* Step 6 */}
        {step === 5 && (
          <div className="space-y-5">
            <h2 className="font-headline text-2xl md:text-3xl font-extrabold tracking-tight leading-tight">
              O que você espera melhorar?
            </h2>
            <MultiSelect
              options={DESEJOS_MELHORAR}
              selected={desejoMelhorar}
              onToggle={(id) =>
                toggleItem(desejoMelhorar, setDesejoMelhorar, id)
              }
            />
            <button
              onClick={handleSubmit}
              disabled={saving}
              className="w-full bg-ai-pulse text-on-primary font-bold px-6 py-3.5 rounded-full shadow-cta-glow active:scale-[0.98] transition disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {saving ? (
                <>
                  <span className="material-symbols-outlined animate-spin">
                    progress_activity
                  </span>
                  Salvando...
                </>
              ) : (
                <>
                  Começar avaliação
                  <span className="material-symbols-outlined">
                    arrow_forward
                  </span>
                </>
              )}
            </button>
          </div>
        )}

        <button
          onClick={handleSkip}
          className="w-full text-center text-sm text-on-surface-variant hover:text-on-surface transition py-2"
        >
          Pular e ir direto para avaliação
        </button>
      </div>
    </AppShell>
  );
}
