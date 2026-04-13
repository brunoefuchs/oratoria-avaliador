"use client";

import { useRef, useState } from "react";

interface TimelineEvent {
  type: "cluster" | "filler" | "pausa_hesitacao" | "pausa_estrategica" | "monotono" | "alta_performance";
  start: number;
  end: number;
  label?: string;
}

interface VideoPlayerProps {
  videoUrl: string;
  events: TimelineEvent[];
  duration: number;
}

const EVENT_STYLES: Record<string, { bg: string; emoji: string; label: string }> = {
  cluster:           { bg: "bg-red-600",    emoji: "🔴", label: "Cluster de vicios" },
  filler:            { bg: "bg-orange-400", emoji: "🟠", label: "Vicio isolado" },
  pausa_hesitacao:   { bg: "bg-amber-300",  emoji: "🟡", label: "Hesitacao" },
  pausa_estrategica: { bg: "bg-emerald-500", emoji: "🟢", label: "Pausa estrategica" },
  monotono:          { bg: "bg-yellow-400", emoji: "🟡", label: "Trecho monotono" },
  alta_performance:  { bg: "bg-green-500",  emoji: "🟢", label: "Alta performance" },
};

const DEFAULT_STYLE = { bg: "bg-gray-400", emoji: "⚪", label: "Evento" };

function getStyle(type: string) {
  return EVENT_STYLES[type] || DEFAULT_STYLE;
}

export function VideoPlayer({ videoUrl, events, duration }: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [currentTime, setCurrentTime] = useState(0);
  const [hoveredEvent, setHoveredEvent] = useState<TimelineEvent | null>(null);

  const seekTo = (time: number) => {
    if (videoRef.current) {
      videoRef.current.currentTime = time;
      videoRef.current.play();
    }
  };

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime);
    }
  };

  const pctPosition = (time: number) => `${(time / Math.max(1, duration)) * 100}%`;
  const pctWidth = (start: number, end: number) =>
    `${Math.max(0.5, ((end - start) / Math.max(1, duration)) * 100)}%`;

  // Agrupar eventos por categoria para evitar overlap visual
  const groupedEvents = events.reduce<Record<string, TimelineEvent[]>>((acc, ev) => {
    const cat = ev.type === "cluster" || ev.type === "filler" ? "vicios"
              : ev.type === "pausa_estrategica" ? "estrategicas"
              : ev.type === "pausa_hesitacao" ? "hesitacoes"
              : "outros";
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(ev);
    return acc;
  }, {});

  return (
    <div className="space-y-4">
      {/* Video */}
      <video
        ref={videoRef}
        src={videoUrl}
        controls
        onTimeUpdate={handleTimeUpdate}
        className="w-full rounded-xl bg-black"
        preload="metadata"
      />

      {/* Tooltip do evento hovered */}
      {hoveredEvent && (
        <div className="rounded-lg bg-gray-900 p-2 text-xs text-white">
          {getStyle(hoveredEvent.type).emoji} {hoveredEvent.label || getStyle(hoveredEvent.type).label}
          {" "}— {hoveredEvent.start.toFixed(1)}s
        </div>
      )}

      {/* Timeline com 3 lanes */}
      <div className="space-y-1">
        {/* Lane 1: Vicios de linguagem (vermelho/laranja) */}
        <div className="space-y-0.5">
          <p className="text-[10px] text-gray-500 uppercase tracking-wide">Vicios de linguagem</p>
          <div className="relative h-4 rounded bg-gray-100 overflow-hidden">
            {groupedEvents.vicios?.map((event, i) => (
              <button
                key={i}
                onClick={() => seekTo(event.start)}
                onMouseEnter={() => setHoveredEvent(event)}
                onMouseLeave={() => setHoveredEvent(null)}
                title={event.label}
                className={`absolute top-0 h-full ${getStyle(event.type).bg} hover:brightness-110 cursor-pointer rounded-sm`}
                style={{
                  left: pctPosition(event.start),
                  width: pctWidth(event.start, event.end),
                  minWidth: "3px",
                }}
              />
            ))}
            {/* Playhead */}
            <div
              className="absolute top-0 h-full w-0.5 bg-blue-600 z-10 pointer-events-none"
              style={{ left: pctPosition(currentTime) }}
            />
          </div>
        </div>

        {/* Lane 2: Pausas estrategicas (verde) */}
        <div className="space-y-0.5">
          <p className="text-[10px] text-gray-500 uppercase tracking-wide">Pausas estrategicas (poder)</p>
          <div className="relative h-4 rounded bg-gray-100 overflow-hidden">
            {groupedEvents.estrategicas?.map((event, i) => (
              <button
                key={i}
                onClick={() => seekTo(event.start)}
                onMouseEnter={() => setHoveredEvent(event)}
                onMouseLeave={() => setHoveredEvent(null)}
                title={event.label}
                className={`absolute top-0 h-full ${getStyle(event.type).bg} hover:brightness-110 cursor-pointer rounded-sm`}
                style={{
                  left: pctPosition(event.start),
                  width: pctWidth(event.start, event.end),
                  minWidth: "3px",
                }}
              />
            ))}
            <div
              className="absolute top-0 h-full w-0.5 bg-blue-600 z-10 pointer-events-none"
              style={{ left: pctPosition(currentTime) }}
            />
          </div>
        </div>

        {/* Lane 3: Hesitacoes (amarelo claro) */}
        <div className="space-y-0.5">
          <p className="text-[10px] text-gray-500 uppercase tracking-wide">Hesitacoes</p>
          <div className="relative h-4 rounded bg-gray-100 overflow-hidden">
            {groupedEvents.hesitacoes?.map((event, i) => (
              <button
                key={i}
                onClick={() => seekTo(event.start)}
                onMouseEnter={() => setHoveredEvent(event)}
                onMouseLeave={() => setHoveredEvent(null)}
                title={event.label}
                className={`absolute top-0 h-full ${getStyle(event.type).bg} hover:brightness-110 cursor-pointer rounded-sm`}
                style={{
                  left: pctPosition(event.start),
                  width: pctWidth(event.start, event.end),
                  minWidth: "3px",
                }}
              />
            ))}
            <div
              className="absolute top-0 h-full w-0.5 bg-blue-600 z-10 pointer-events-none"
              style={{ left: pctPosition(currentTime) }}
            />
          </div>
        </div>
      </div>

      {/* Legenda */}
      <div className="grid grid-cols-2 gap-2 text-xs text-gray-600">
        <span className="flex items-center gap-1">
          <span className="inline-block h-2 w-3 rounded bg-red-600" />
          Cluster (3+ vicios em sequencia)
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block h-2 w-3 rounded bg-orange-400" />
          Vicio isolado
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block h-2 w-3 rounded bg-emerald-500" />
          Pausa estrategica
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block h-2 w-3 rounded bg-amber-300" />
          Hesitacao
        </span>
      </div>
    </div>
  );
}
