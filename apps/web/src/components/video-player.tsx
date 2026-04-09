"use client";

import { useRef, useState } from "react";

interface TimelineEvent {
  type: "cluster" | "monotono" | "alta_performance";
  start: number;
  end: number;
  label?: string;
}

interface VideoPlayerProps {
  videoUrl: string;
  events: TimelineEvent[];
  duration: number;
}

const EVENT_COLORS = {
  cluster: { bg: "bg-red-500", label: "Vicios de linguagem" },
  monotono: { bg: "bg-yellow-400", label: "Trecho monotono" },
  alta_performance: { bg: "bg-green-500", label: "Alta performance" },
};

export function VideoPlayer({ videoUrl, events, duration }: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [currentTime, setCurrentTime] = useState(0);
  const [playing, setPlaying] = useState(false);

  const seekTo = (time: number) => {
    if (videoRef.current) {
      videoRef.current.currentTime = time;
      videoRef.current.play();
      setPlaying(true);
    }
  };

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime);
    }
  };

  const pctPosition = (time: number) => `${(time / Math.max(1, duration)) * 100}%`;
  const pctWidth = (start: number, end: number) =>
    `${((end - start) / Math.max(1, duration)) * 100}%`;

  return (
    <div className="space-y-3">
      {/* Video */}
      <video
        ref={videoRef}
        src={videoUrl}
        controls
        onTimeUpdate={handleTimeUpdate}
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        className="w-full rounded-xl bg-black"
        preload="metadata"
      />

      {/* Timeline */}
      <div className="relative h-8 rounded-full bg-gray-200 overflow-hidden">
        {/* Event markers */}
        {events.map((event, i) => (
          <button
            key={i}
            onClick={() => seekTo(event.start)}
            title={`${EVENT_COLORS[event.type].label} (${Math.round(event.start)}s)`}
            className={`absolute top-0 h-full ${EVENT_COLORS[event.type].bg} opacity-60 hover:opacity-100 transition-opacity cursor-pointer`}
            style={{
              left: pctPosition(event.start),
              width: pctWidth(event.start, event.end),
              minWidth: "4px",
            }}
          />
        ))}

        {/* Playhead */}
        <div
          className="absolute top-0 h-full w-0.5 bg-blue-600 z-10 pointer-events-none"
          style={{ left: pctPosition(currentTime) }}
        />
      </div>

      {/* Legenda */}
      <div className="flex flex-wrap gap-3 text-xs text-gray-500">
        <span className="flex items-center gap-1">
          <span className="inline-block h-2 w-4 rounded bg-red-500" /> Vicios em cluster
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block h-2 w-4 rounded bg-yellow-400" /> Trechos monotonos
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block h-2 w-4 rounded bg-green-500" /> Alta performance
        </span>
      </div>
    </div>
  );
}
