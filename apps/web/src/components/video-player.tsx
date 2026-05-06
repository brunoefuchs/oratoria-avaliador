"use client";

import { useRef, useState } from "react";

interface TimelineEvent {
  type:
    | "cluster"
    | "filler"
    | "pausa_hesitacao"
    | "pausa_estrategica"
    | "pausa_respiracao"
    | "monotono"
    | "alta_performance";
  start: number;
  end: number;
  label?: string;
}

interface VideoPlayerProps {
  videoUrl: string;
  events: TimelineEvent[];
  duration: number;
}

const EVENT_STYLES: Record<
  string,
  { bg: string; dot: string; label: string }
> = {
  cluster: {
    bg: "bg-error",
    dot: "bg-error",
    label: "Cluster de vícios",
  },
  filler: {
    bg: "bg-tertiary",
    dot: "bg-tertiary",
    label: "Vício isolado",
  },
  pausa_hesitacao: {
    bg: "bg-tertiary/70",
    dot: "bg-tertiary/70",
    label: "Hesitação",
  },
  pausa_estrategica: {
    bg: "bg-secondary",
    dot: "bg-secondary",
    label: "Pausa estratégica",
  },
  pausa_respiracao: {
    bg: "bg-outline-variant",
    dot: "bg-outline-variant",
    label: "Respiração",
  },
  monotono: {
    bg: "bg-tertiary/60",
    dot: "bg-tertiary/60",
    label: "Trecho monótono",
  },
  alta_performance: {
    bg: "bg-secondary",
    dot: "bg-secondary",
    label: "Alta performance",
  },
};

const DEFAULT_STYLE = {
  bg: "bg-outline-variant",
  dot: "bg-outline-variant",
  label: "Evento",
};

function getStyle(type: string) {
  return EVENT_STYLES[type] || DEFAULT_STYLE;
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
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

  const pctPosition = (time: number) =>
    `${(time / Math.max(1, duration)) * 100}%`;
  const pctWidth = (start: number, end: number) =>
    `${Math.max(0.5, ((end - start) / Math.max(1, duration)) * 100)}%`;

  const groupedEvents = events.reduce<Record<string, TimelineEvent[]>>(
    (acc, ev) => {
      const cat =
        ev.type === "cluster" || ev.type === "filler"
          ? "vicios"
          : ev.type === "pausa_estrategica"
          ? "estrategicas"
          : ev.type === "pausa_hesitacao"
          ? "hesitacoes"
          : ev.type === "pausa_respiracao"
          ? "respiracoes"
          : "outros";
      if (!acc[cat]) acc[cat] = [];
      acc[cat].push(ev);
      return acc;
    },
    {}
  );

  const lanes: {
    key: string;
    label: string;
    data: TimelineEvent[] | undefined;
  }[] = [
    {
      key: "vicios",
      label: "Vícios de linguagem",
      data: groupedEvents.vicios,
    },
    {
      key: "estrategicas",
      label: "Pausas estratégicas (poder)",
      data: groupedEvents.estrategicas,
    },
    {
      key: "hesitacoes",
      label: "Hesitações",
      data: groupedEvents.hesitacoes,
    },
    {
      key: "respiracoes",
      label: "Respirações",
      data: groupedEvents.respiracoes,
    },
  ];

  return (
    <div className="space-y-5">
      <div className="rounded-3xl bg-surface-container-lowest p-3 ghost-border">
        <video
          ref={videoRef}
          src={videoUrl}
          controls
          onTimeUpdate={handleTimeUpdate}
          className="w-full rounded-2xl bg-black aspect-video"
          preload="metadata"
        />
      </div>

      <div
        className={`rounded-xl bg-surface-container-high px-3 py-2 text-xs ghost-border transition-opacity h-9 flex items-center whitespace-nowrap overflow-hidden ${
          hoveredEvent ? "opacity-100" : "opacity-0"
        }`}
        aria-hidden={!hoveredEvent}
      >
        <span
          className={`inline-block w-2 h-2 rounded-full mr-2 shrink-0 ${
            hoveredEvent ? getStyle(hoveredEvent.type).dot : "bg-transparent"
          }`}
        />
        <span className="font-semibold text-on-surface truncate">
          {hoveredEvent
            ? hoveredEvent.label || getStyle(hoveredEvent.type).label
            : " "}
        </span>
        {hoveredEvent && (
          <span className="text-on-surface-variant ml-2 shrink-0">
            — {formatTime(hoveredEvent.start)}
          </span>
        )}
      </div>

      <div className="rounded-2xl bg-surface-container-low p-5 space-y-4 ghost-border">
        <div className="flex items-center justify-between text-xs font-label uppercase tracking-[0.2em] text-on-surface-variant">
          <span>Timeline · {events.length} eventos</span>
          <span className="text-secondary font-mono">
            {formatTime(currentTime)} / {formatTime(duration)}
          </span>
        </div>

        {lanes.map((lane) => (
          <div key={lane.key} className="space-y-1.5">
            <p className="text-[10px] text-on-surface-variant uppercase tracking-wide">
              {lane.label}
            </p>
            <div className="relative h-5 rounded-lg bg-surface-container-highest overflow-hidden">
              {lane.data?.map((event, i) => (
                <button
                  key={i}
                  onClick={() => seekTo(event.start)}
                  onMouseEnter={() => setHoveredEvent(event)}
                  onMouseLeave={() => setHoveredEvent(null)}
                  title={event.label}
                  className={`absolute top-0 h-full ${
                    getStyle(event.type).bg
                  } hover:brightness-125 cursor-pointer rounded`}
                  style={{
                    left: pctPosition(event.start),
                    width: pctWidth(event.start, event.end),
                    minWidth: "3px",
                  }}
                />
              ))}
              <div
                className="absolute top-0 h-full w-0.5 bg-secondary shadow-[0_0_8px_rgba(69,216,237,0.8)] z-10 pointer-events-none"
                style={{ left: pctPosition(currentTime) }}
              />
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-2 text-xs">
        <span className="flex items-center gap-2 rounded-lg bg-surface-container-low p-2.5 ghost-border">
          <span className="inline-block w-2.5 h-2.5 rounded-full bg-error" />
          <span className="text-on-surface-variant">Cluster (3+ vícios)</span>
        </span>
        <span className="flex items-center gap-2 rounded-lg bg-surface-container-low p-2.5 ghost-border">
          <span className="inline-block w-2.5 h-2.5 rounded-full bg-tertiary" />
          <span className="text-on-surface-variant">Vício isolado</span>
        </span>
        <span className="flex items-center gap-2 rounded-lg bg-surface-container-low p-2.5 ghost-border">
          <span className="inline-block w-2.5 h-2.5 rounded-full bg-secondary" />
          <span className="text-on-surface-variant">Pausa estratégica</span>
        </span>
        <span className="flex items-center gap-2 rounded-lg bg-surface-container-low p-2.5 ghost-border">
          <span className="inline-block w-2.5 h-2.5 rounded-full bg-tertiary/70" />
          <span className="text-on-surface-variant">Hesitação</span>
        </span>
        <span className="flex items-center gap-2 rounded-lg bg-surface-container-low p-2.5 ghost-border">
          <span className="inline-block w-2.5 h-2.5 rounded-full bg-outline-variant" />
          <span className="text-on-surface-variant">Respiração</span>
        </span>
      </div>
    </div>
  );
}
