"use client";

import { useParams } from "next/navigation";

export default function ReportPage() {
  const params = useParams();
  const id = params.id as string;

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <div className="text-center space-y-4 max-w-md">
        <div className="text-5xl">📊</div>
        <h1 className="text-2xl font-bold">Relatorio em construcao</h1>
        <p className="text-gray-500">
          O dashboard de relatorio sera implementado no Epic 3.
        </p>
        <div className="rounded-lg bg-gray-100 p-4 text-sm text-gray-600">
          <p>
            <strong>Avaliacao ID:</strong> {id}
          </p>
        </div>
      </div>
    </main>
  );
}
