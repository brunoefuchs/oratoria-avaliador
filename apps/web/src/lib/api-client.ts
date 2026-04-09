const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function uploadVideo(
  file: File,
  onProgress?: (percent: number) => void
): Promise<{ id: string; status: string; video_url: string; created_at: string }> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const formData = new FormData();
    formData.append("video", file);

    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    });

    xhr.addEventListener("load", () => {
      if (xhr.status === 201) {
        resolve(JSON.parse(xhr.responseText));
      } else {
        try {
          const error = JSON.parse(xhr.responseText);
          reject(new Error(error.detail?.message || "Erro ao fazer upload"));
        } catch {
          reject(new Error("Erro ao fazer upload"));
        }
      }
    });

    xhr.addEventListener("error", () => {
      reject(new Error("Erro de conexao com o servidor"));
    });

    xhr.open("POST", `${API_URL}/evaluations`);
    xhr.send(formData);
  });
}

export async function fetchReport(evaluationId: string) {
  const res = await fetch(`${API_URL}/evaluations/${evaluationId}/report`);
  if (!res.ok) throw new Error("Falha ao carregar relatorio");
  return res.json();
}

export async function fetchDimensionDetail(evaluationId: string, dimension: string) {
  const res = await fetch(`${API_URL}/evaluations/${evaluationId}/report/${dimension}`);
  if (!res.ok) throw new Error("Falha ao carregar dimensao");
  return res.json();
}

export async function saveContext(
  evaluationId: string,
  context: {
    sentimento?: number;
    maior_medo?: string[];
    contexto?: string;
    avaliado_antes?: boolean;
    objetivo?: string;
  }
) {
  const res = await fetch(`${API_URL}/evaluations/${evaluationId}/context`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(context),
  });
  if (!res.ok) throw new Error("Falha ao salvar contexto");
  return res.json();
}

export async function fetchEvaluationStatus(evaluationId: string) {
  const res = await fetch(`${API_URL}/evaluations/${evaluationId}/status`);
  if (!res.ok) throw new Error("Falha ao carregar status");
  return res.json();
}

export async function createShare(evaluationId: string) {
  const res = await fetch(`${API_URL}/evaluations/${evaluationId}/share`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Falha ao criar link de compartilhamento");
  return res.json();
}

export async function fetchSharedReport(shareToken: string) {
  const res = await fetch(`${API_URL}/shared/${shareToken}`);
  if (!res.ok) throw new Error("Relatorio nao encontrado ou expirado");
  return res.json();
}

export async function fetchEvolution(userToken: string) {
  const res = await fetch(`${API_URL}/evaluations?user_token=${userToken}`);
  if (!res.ok) throw new Error("Falha ao carregar evolucao");
  return res.json();
}

export async function submitRating(evaluationId: string, rating: number, comment?: string) {
  const res = await fetch(`${API_URL}/evaluations/${evaluationId}/rating`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ rating, comment }),
  });
  if (!res.ok) throw new Error("Falha ao enviar avaliacao");
  return res.json();
}
