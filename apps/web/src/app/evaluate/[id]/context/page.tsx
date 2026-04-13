"use client";

import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { saveContext } from "@/lib/api-client";

const MEDOS = [
  { id: "dar_branco", label: "Esquecer o que ia falar (dar branco)" },
  { id: "julgamento", label: "Do que os outros vao dizer (julgamento)" },
  { id: "monotono", label: "Parecer monotono ou entediante" },
  { id: "nao_convencer", label: "Nao conseguir convencer" },
  { id: "errar", label: "De errar" },
  { id: "parecer_diferente", label: "Parecer diferente de quem eu sou" },
  { id: "outro", label: "Outro" },
];

const MOTIVACOES = [
  { id: "redes_sociais", label: "Me posicionar nas redes sociais" },
  { id: "vender_mais", label: "Vender mais" },
  { id: "carreira", label: "Crescer na profissao/carreira" },
  { id: "palestrar", label: "Palestrar" },
  { id: "satisfacao_pessoal", label: "Satisfacao pessoal" },
  { id: "outro", label: "Outro" },
];

const DESEJOS_TRANSMITIR = [
  { id: "confianca", label: "Confianca" },
  { id: "autoridade", label: "Autoridade" },
  { id: "credibilidade", label: "Credibilidade" },
  { id: "naturalidade", label: "Naturalidade" },
  { id: "seguranca", label: "Seguranca" },
  { id: "outro", label: "Outro" },
];

const DESEJOS_MELHORAR = [
  { id: "diccao", label: "Diccao" },
  { id: "postura", label: "Postura" },
  { id: "gestual", label: "Gestual" },
  { id: "tom_de_voz", label: "Tom de voz" },
  { id: "clareza_fala", label: "Clareza na fala (ritmo, pausas, velocidade)" },
  { id: "outro", label: "Outro" },
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

  const toggleItem = (list: string[], setList: (v: string[]) => void, id: string) => {
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
        desejo_transmitir: desejoTransmitir.length > 0 ? desejoTransmitir : undefined,
        desejo_melhorar: desejoMelhorar.length > 0 ? desejoMelhorar : undefined,
      });
    } catch {
      // Falha silenciosa — questionario e opcional
    }
    router.push(`/processing/${id}`);
  };

  const handleSkip = () => router.push(`/processing/${id}`);
  const nextStep = () => setStep((s) => Math.min(s + 1, 5));

  const sentimentoLabels = [
    "Muito nervoso",
    "Nervoso",
    "Neutro",
    "Confiante",
    "Muito confiante",
  ];

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
      {options.map((opt) => (
        <button
          key={opt.id}
          onClick={() => onToggle(opt.id)}
          className={`w-full rounded-xl p-3 text-left text-sm transition-all ${
            selected.includes(opt.id)
              ? "bg-blue-50 ring-2 ring-blue-300 text-blue-800"
              : "bg-gray-50 hover:bg-gray-100"
          }`}
        >
          {selected.includes(opt.id) ? "✓ " : ""}
          {opt.label}
        </button>
      ))}
    </div>
  );

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <div className="w-full max-w-md space-y-6">
        {/* Progress */}
        <div className="flex gap-1">
          {[0, 1, 2, 3, 4, 5].map((i) => (
            <div
              key={i}
              className={`h-1 flex-1 rounded-full transition-colors ${
                i <= step ? "bg-blue-500" : "bg-gray-200"
              }`}
            />
          ))}
        </div>

        {/* Step 1: Sentimento */}
        {step === 0 && (
          <div className="space-y-4 text-center">
            <h2 className="text-xl font-bold">
              Como voce se sentiu gravando esse video?
            </h2>
            <div className="flex justify-center gap-3">
              {[1, 2, 3, 4, 5].map((v) => (
                <button
                  key={v}
                  onClick={() => {
                    setSentimento(v);
                    nextStep();
                  }}
                  className={`flex h-14 w-14 flex-col items-center justify-center rounded-xl text-lg transition-all ${
                    sentimento === v
                      ? "bg-blue-500 text-white ring-2 ring-blue-300"
                      : "bg-gray-100 hover:bg-gray-200"
                  }`}
                >
                  {v}
                  <span className="text-[9px] leading-tight">
                    {sentimentoLabels[v - 1].split(" ").pop()}
                  </span>
                </button>
              ))}
            </div>
            <p className="text-xs text-gray-400">
              1 = muito nervoso, 5 = muito confiante
            </p>
          </div>
        )}

        {/* Step 2: Maior medo */}
        {step === 1 && (
          <div className="space-y-4">
            <h2 className="text-xl font-bold text-center">
              Qual seu maior medo ao se comunicar?
            </h2>
            <MultiSelect
              options={MEDOS}
              selected={medos}
              onToggle={(id) => toggleItem(medos, setMedos, id)}
            />
            <button
              onClick={nextStep}
              className="w-full rounded-xl bg-blue-500 py-3 text-white font-medium hover:bg-blue-600"
            >
              Continuar
            </button>
          </div>
        )}

        {/* Step 3: Motivacao */}
        {step === 2 && (
          <div className="space-y-4">
            <h2 className="text-xl font-bold text-center">
              Por que voce quer melhorar a comunicacao?
            </h2>
            <MultiSelect
              options={MOTIVACOES}
              selected={motivacoes}
              onToggle={(id) => toggleItem(motivacoes, setMotivacoes, id)}
            />
            <button
              onClick={nextStep}
              className="w-full rounded-xl bg-blue-500 py-3 text-white font-medium hover:bg-blue-600"
            >
              Continuar
            </button>
          </div>
        )}

        {/* Step 4: Avaliado antes */}
        {step === 3 && (
          <div className="space-y-4 text-center">
            <h2 className="text-xl font-bold">Voce ja se avaliou antes?</h2>
            <div className="flex justify-center gap-4">
              <button
                onClick={() => { setAvaliadoAntes(true); nextStep(); }}
                className="rounded-xl bg-gray-50 px-8 py-4 text-lg hover:bg-gray-100"
              >
                Sim
              </button>
              <button
                onClick={() => { setAvaliadoAntes(false); nextStep(); }}
                className="rounded-xl bg-gray-50 px-8 py-4 text-lg hover:bg-gray-100"
              >
                Nao
              </button>
            </div>
          </div>
        )}

        {/* Step 5: Desejo transmitir */}
        {step === 4 && (
          <div className="space-y-4">
            <h2 className="text-xl font-bold text-center">
              O que voce deseja transmitir atraves da sua comunicacao?
            </h2>
            <MultiSelect
              options={DESEJOS_TRANSMITIR}
              selected={desejoTransmitir}
              onToggle={(id) => toggleItem(desejoTransmitir, setDesejoTransmitir, id)}
            />
            <button
              onClick={nextStep}
              className="w-full rounded-xl bg-blue-500 py-3 text-white font-medium hover:bg-blue-600"
            >
              Continuar
            </button>
          </div>
        )}

        {/* Step 6: Desejo melhorar */}
        {step === 5 && (
          <div className="space-y-4">
            <h2 className="text-xl font-bold text-center">
              O que voce espera melhorar?
            </h2>
            <MultiSelect
              options={DESEJOS_MELHORAR}
              selected={desejoMelhorar}
              onToggle={(id) => toggleItem(desejoMelhorar, setDesejoMelhorar, id)}
            />
            <button
              onClick={handleSubmit}
              disabled={saving}
              className="w-full rounded-xl bg-blue-500 py-3 text-white font-medium hover:bg-blue-600 disabled:opacity-50"
            >
              {saving ? "Salvando..." : "Comecar avaliacao"}
            </button>
          </div>
        )}

        {/* Skip */}
        <button
          onClick={handleSkip}
          className="w-full text-center text-sm text-gray-400 hover:text-gray-600"
        >
          Pular e ir direto para avaliacao
        </button>
      </div>
    </main>
  );
}
