"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect } from "react";
import { ProcessingStatus } from "@/components/processing-status";
import { useEvaluationStatus } from "@/hooks/use-evaluation-status";

export default function ProcessingPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;
  const { data, isLoading, error } = useEvaluationStatus(id);

  useEffect(() => {
    if (!data) return;
    if (data.status === "completed" || data.status === "analyzed") {
      router.push(`/report/${id}`);
    }
  }, [data, id, router]);

  if (isLoading) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <div className="text-gray-500">Carregando...</div>
      </main>
    );
  }

  if (error) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-8">
        <div className="rounded-lg bg-red-50 p-6 text-center">
          <p className="text-lg font-medium text-red-800">
            Erro ao buscar status
          </p>
          <p className="mt-1 text-sm text-red-600">{error}</p>
        </div>
        <button
          onClick={() => router.push("/")}
          className="rounded-lg bg-blue-600 px-6 py-2 text-white hover:bg-blue-700"
        >
          Tentar novamente
        </button>
      </main>
    );
  }

  if (data?.status === "error") {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-8">
        <div className="rounded-lg bg-red-50 p-6 text-center max-w-md">
          <p className="text-lg font-medium text-red-800">
            Erro no processamento
          </p>
          <p className="mt-1 text-sm text-red-600">
            Houve um problema ao analisar seu video. Por favor, tente novamente.
          </p>
        </div>
        <button
          onClick={() => router.push("/")}
          className="rounded-lg bg-blue-600 px-6 py-2 text-white hover:bg-blue-700"
        >
          Enviar outro video
        </button>
      </main>
    );
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-8 p-8">
      <div className="text-center space-y-2">
        <h1 className="text-2xl font-bold">Analisando seu video</h1>
        <p className="text-gray-500 text-sm">
          Isso pode levar alguns minutos...
        </p>
      </div>

      <ProcessingStatus
        substatus={data?.substatus ?? null}
        stepsCompleted={data?.progress?.steps_completed ?? 0}
      />
    </main>
  );
}
