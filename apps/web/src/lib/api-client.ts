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
