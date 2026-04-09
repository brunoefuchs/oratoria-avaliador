"use client";

import { useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8002";

interface Progress {
  steps_completed: number;
  steps_total: number;
  current_step: string | null;
}

interface EvaluationStatus {
  id: string;
  status: string;
  substatus: string | null;
  progress: Progress | null;
}

export function useEvaluationStatus(id: string) {
  const [data, setData] = useState<EvaluationStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    const fetchStatus = async () => {
      try {
        const res = await fetch(`${API_URL}/evaluations/${id}/status`);
        if (!res.ok) {
          throw new Error("Falha ao buscar status");
        }
        const status: EvaluationStatus = await res.json();
        if (active) {
          setData(status);
          setIsLoading(false);
          setError(null);
        }
        return status;
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : "Erro desconhecido");
          setIsLoading(false);
        }
        return null;
      }
    };

    // Initial fetch
    fetchStatus();

    // Poll every 3 seconds
    const interval = setInterval(async () => {
      const status = await fetchStatus();
      if (
        status &&
        (status.status === "completed" ||
          status.status === "error" ||
          status.status === "analyzed")
      ) {
        clearInterval(interval);
      }
    }, 3000);

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [id]);

  return { data, isLoading, error };
}
