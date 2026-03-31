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
          resolve("Formato nao suportado. Use MP4 ou WebM.");
          return;
        }

        if (file.size > MAX_SIZE) {
          resolve("Video deve ter no maximo 500MB.");
          return;
        }

        // Check duration
        const video = document.createElement("video");
        video.preload = "metadata";
        video.onloadedmetadata = () => {
          URL.revokeObjectURL(video.src);
          if (video.duration > MAX_DURATION) {
            resolve("Video deve ter no maximo 10 minutos.");
          } else {
            resolve(null);
          }
        };
        video.onerror = () => {
          URL.revokeObjectURL(video.src);
          resolve("Nao foi possivel ler o video.");
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
    <div className="w-full max-w-xl mx-auto">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`
          relative cursor-pointer rounded-2xl border-2 border-dashed p-12
          text-center transition-colors
          ${isDragging
            ? "border-blue-500 bg-blue-50"
            : "border-gray-300 hover:border-gray-400 hover:bg-gray-50"
          }
          ${isUploading ? "pointer-events-none opacity-60" : ""}
        `}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="video/mp4,video/webm"
          onChange={handleChange}
          className="hidden"
        />

        <div className="space-y-3">
          <div className="text-4xl">🎬</div>
          <p className="text-lg font-medium text-gray-700">
            Arraste seu video aqui ou clique para selecionar
          </p>
          <p className="text-sm text-gray-500">
            MP4 ou WebM, ate 500MB e 10 minutos
          </p>
        </div>
      </div>

      {progress !== null && (
        <div className="mt-4">
          <div className="flex justify-between text-sm text-gray-600 mb-1">
            <span>Enviando...</span>
            <span>{progress}%</span>
          </div>
          <div className="h-2 rounded-full bg-gray-200">
            <div
              className="h-2 rounded-full bg-blue-500 transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {error && (
        <div className="mt-4 rounded-lg bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}
    </div>
  );
}
