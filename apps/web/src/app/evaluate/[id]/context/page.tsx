"use client";

import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { saveContext } from "@/lib/api-client";

const MEDOS = [
  { id: "esquecer", label: "Esquecer o que ia falar" },
  { id: "julgamento", label: "Ser julgado pela audiencia" },
  { id: "monotono", label: "Parecer monotono ou entediante" },
  { id: "nao_convencer", label: "Nao conseguir convencer" },
  { id: "outro", label: "Outro" },
];

const CONTEXTOS = [
  { id: "vendas", label: "Vendas / Pitch" },
  { id: "palco", label: "Palco / Palestra" },
  { id: "aula", label: "Aula / Treinamento" },
  { id: "rede_social", label: "Rede Social / Video" },
  { id: "reuniao", label: "Reuniao" },
  { id: "podcast", label: "Podcast / Audio" },
  { id: "outro", label: "Outro" },
];

export default function ContextPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const [step, setStep] = useState(0);
  const [sentimento, setSentimento] = useState<number>(3);
  const [medos, setMedos] = useState<string[]>([]);
  const [contexto, setContexto] = useState<string>("");
  const [avaliadoAntes, setAvaliadoAntes] = useState<boolean | null>(null);
  const [objetivo, setObjetivo] = useState("");
  const [saving, setSaving] = useState(false);

  const toggleMedo = (id: string) => {
    setMedos((prev) =>
      prev.includes(id) ? prev.filter((m) => m !== id) : [...prev, id]
    );
  };

  const handleSubmit = async () => {
    setSaving(true);
    try {
      await saveContext(id, {
        sentimento,
        maior_medo: medos.length > 0 ? medos : undefined,
        contexto: contexto || undefined,
        avaliado_antes: avaliadoAntes ?? undefined,
        objetivo: objetivo || undefined,
      });
    } catch {
      // Falha silenciosa — questionario e opcional
    }
    router.push(`/processing/${id}`);
  };

  const handleSkip = () => {
    router.push(`/processing/${id}`);
  };

  const nextStep = () => setStep((s) => Math.min(s + 1, 4));

  const sentimentoLabels = [
    "Muito nervoso",
    "Nervoso",
    "Neutro",
    "Confiante",
    "Muito confiante",
  ];

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <div className="w-full max-w-md space-y-6">
        {/* Progress */}
        <div className="flex gap-1">
          {[0, 1, 2, 3, 4].map((i) => (
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
            <div className="space-y-2">
              {MEDOS.map((m) => (
                <button
                  key={m.id}
                  onClick={() => toggleMedo(m.id)}
                  className={`w-full rounded-xl p-3 text-left text-sm transition-all ${
                    medos.includes(m.id)
                      ? "bg-blue-50 ring-2 ring-blue-300 text-blue-800"
                      : "bg-gray-50 hover:bg-gray-100"
                  }`}
                >
                  {medos.includes(m.id) ? "✓ " : ""}
                  {m.label}
                </button>
              ))}
            </div>
            <button
              onClick={nextStep}
              className="w-full rounded-xl bg-blue-500 py-3 text-white font-medium hover:bg-blue-600"
            >
              Continuar
            </button>
          </div>
        )}

        {/* Step 3: Contexto */}
        {step === 2 && (
          <div className="space-y-4">
            <h2 className="text-xl font-bold text-center">
              Qual o contexto dessa apresentacao?
            </h2>
            <div className="grid grid-cols-2 gap-2">
              {CONTEXTOS.map((c) => (
                <button
                  key={c.id}
                  onClick={() => {
                    setContexto(c.id);
                    nextStep();
                  }}
                  className={`rounded-xl p-3 text-sm transition-all ${
                    contexto === c.id
                      ? "bg-blue-50 ring-2 ring-blue-300 text-blue-800"
                      : "bg-gray-50 hover:bg-gray-100"
                  }`}
                >
                  {c.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Step 4: Avaliado antes */}
        {step === 3 && (
          <div className="space-y-4 text-center">
            <h2 className="text-xl font-bold">
              Voce ja se avaliou antes?
            </h2>
            <div className="flex justify-center gap-4">
              <button
                onClick={() => {
                  setAvaliadoAntes(true);
                  nextStep();
                }}
                className="rounded-xl bg-gray-50 px-8 py-4 text-lg hover:bg-gray-100"
              >
                Sim
              </button>
              <button
                onClick={() => {
                  setAvaliadoAntes(false);
                  nextStep();
                }}
                className="rounded-xl bg-gray-50 px-8 py-4 text-lg hover:bg-gray-100"
              >
                Nao
              </button>
            </div>
          </div>
        )}

        {/* Step 5: Objetivo */}
        {step === 4 && (
          <div className="space-y-4">
            <h2 className="text-xl font-bold text-center">
              O que voce espera melhorar?
            </h2>
            <textarea
              value={objetivo}
              onChange={(e) => setObjetivo(e.target.value.slice(0, 200))}
              placeholder="Ex: Quero falar com mais confianca em reunioes..."
              className="w-full rounded-xl border p-4 text-sm resize-none h-24 focus:ring-2 focus:ring-blue-300 focus:outline-none"
              maxLength={200}
            />
            <p className="text-xs text-gray-400 text-right">
              {objetivo.length}/200
            </p>
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
