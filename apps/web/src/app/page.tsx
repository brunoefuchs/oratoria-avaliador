"use client";

import { useRouter } from "next/navigation";
import { VideoUploader } from "@/components/video-uploader";

export default function Home() {
  const router = useRouter();

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <div className="w-full max-w-xl space-y-8 text-center">
        <div className="space-y-2">
          <h1 className="text-4xl font-bold tracking-tight">
            Oratoria Avaliador
          </h1>
          <p className="text-lg text-gray-600">
            Envie um video e receba feedback sobre sua oratoria
          </p>
        </div>

        <VideoUploader
          onUploadComplete={(id) => router.push(`/processing/${id}`)}
        />
      </div>
    </main>
  );
}
