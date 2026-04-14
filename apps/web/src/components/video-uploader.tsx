"use client";

import { useCallback, useRef, useState } from "react";

const ALLOWED_TYPES = ["video/mp4", "video/webm"];
const MAX_SIZE = 500 * 1024 * 1024; // 500MB
const MAX_DURATION = 600; // 10 minutes

interface VideoUploaderProps {
  onUploadComplete: (evaluationId: string) => void;
}

export function VideoUploader({ onUploadComplete }: VideoUploaderProps) {
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [progress, setProgress] = useState<number | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateFile = useCallback(
    (file: File): Promise<string | null> => {
      return new Promise((resolve) => {
        if (!ALLOWED_TYPES.includes(file.type)) {
          resolve("Formato não suportado. Use MP4 ou WebM.");
          return;
        }

        if (file.size > MAX_SIZE) {
          resolve("Vídeo deve ter no máximo 500MB.");
          return;
        }

        const video = document.createElement("video");
        video.preload = "metadata";
        video.onloadedmetadata = () => {
          URL.revokeObjectURL(video.src);
          if (video.duration > MAX_DURATION) {
            resolve("Vídeo deve ter no máximo 10 minutos.");
          } else {
            resolve(null);
          }
        };
        video.onerror = () => {
          URL.revokeObjectURL(video.src);
          resolve("Não foi possível ler o vídeo.");
        };
        video.src = URL.createObjectURL(file);
      });
    },
    []
  );

  const handleFile = useCallback(
    async (file: File) => {
      setError(null);
      setProgress(null);

      const validationError = await validateFile(file);
      if (validationError) {
        setError(validationError);
        return;
      }

      setIsUploading(true);
      try {
        const { uploadVideo } = await import("@/lib/api-client");
        const result = await uploadVideo(file, setProgress);
        onUploadComplete(result.id);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Erro ao fazer upload");
      } finally {
        setIsUploading(false);
      }
    },
    [validateFile, onUploadComplete]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  return (
    <div className="w-full">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            fileInputRef.current?.click();
          }
        }}
        className={`
          group relative cursor-pointer rounded-3xl p-8 md:p-12 text-center transition-all
          ${
            isDragging
              ? "bg-surface-container-high shadow-cta-glow"
              : "bg-surface-container-low hover:bg-surface-container"
          }
          ${isUploading ? "pointer-events-none opacity-70" : ""}
        `}
        style={{
          borderWidth: "2px",
          borderStyle: "dashed",
          borderColor: isDragging
            ? "rgba(69, 216, 237, 0.5)"
            : "rgba(67, 70, 82, 0.4)",
        }}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="video/mp4,video/webm"
          onChange={handleChange}
          className="hidden"
        />

        <div className="space-y-4">
          <div className="w-16 h-16 mx-auto rounded-full bg-surface-container-highest flex items-center justify-center ghost-border group-hover:scale-110 transition-transform">
            <span className="material-symbols-outlined text-secondary text-3xl">
              videocam
            </span>
          </div>
          <div className="space-y-1">
            <p className="font-headline text-lg font-bold text-on-surface">
              Arraste seu vídeo aqui
            </p>
            <p className="text-sm text-on-surface-variant">
              ou <span className="text-secondary font-semibold">clique para selecionar</span>
            </p>
          </div>
          <div className="flex items-center justify-center gap-2 text-xs text-on-surface-variant pt-2">
            <span className="px-2.5 py-1 rounded-full bg-surface-container-highest ghost-border font-label uppercase tracking-wider">
              MP4 / WebM
            </span>
            <span className="px-2.5 py-1 rounded-full bg-surface-container-highest ghost-border font-label uppercase tracking-wider">
              Até 500MB
            </span>
            <span className="px-2.5 py-1 rounded-full bg-surface-container-highest ghost-border font-label uppercase tracking-wider">
              10 min
            </span>
          </div>
        </div>
      </div>

      {progress !== null && (
        <div className="mt-5 rounded-2xl bg-surface-container-low p-5 ghost-border space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-on-surface-variant flex items-center gap-2">
              <span className="material-symbols-outlined text-secondary text-base animate-glow-pulse">
                cloud_upload
              </span>
              Enviando...
            </span>
            <span className="text-secondary font-semibold">{progress}%</span>
          </div>
          <div className="h-2 rounded-full bg-surface-container-highest overflow-hidden">
            <div
              className="h-full rounded-full bg-gradient-to-r from-secondary to-primary-container transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {error && (
        <div className="mt-5 rounded-2xl bg-error-container/20 p-4 text-sm text-error ghost-border flex items-center gap-3">
          <span className="material-symbols-outlined">error</span>
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}
