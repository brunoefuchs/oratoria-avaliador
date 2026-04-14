"use client";

import { useState } from "react";

interface StarRatingProps {
  onSubmit: (rating: number, comment?: string) => void;
  disabled?: boolean;
}

export function StarRating({ onSubmit, disabled }: StarRatingProps) {
  const [rating, setRating] = useState(0);
  const [hover, setHover] = useState(0);
  const [comment, setComment] = useState("");
  const [submitted, setSubmitted] = useState(false);

  if (submitted) {
    return (
      <div className="rounded-2xl bg-surface-container-high p-5 text-center ghost-border">
        <span className="material-symbols-outlined text-secondary text-3xl mb-2 block">
          favorite
        </span>
        <p className="text-sm text-on-surface">Obrigado pelo feedback!</p>
      </div>
    );
  }

  return (
    <div className="rounded-2xl bg-surface-container-low p-6 space-y-4 ghost-border">
      <div>
        <span className="font-label text-xs uppercase tracking-[0.2em] text-on-surface-variant">
          Feedback rápido
        </span>
        <p className="font-headline text-lg font-bold text-on-surface mt-1">
          Como você avalia este relatório?
        </p>
      </div>
      <div className="flex gap-2">
        {[1, 2, 3, 4, 5].map((star) => {
          const active = star <= (hover || rating);
          return (
            <button
              key={star}
              disabled={disabled}
              onMouseEnter={() => setHover(star)}
              onMouseLeave={() => setHover(0)}
              onClick={() => setRating(star)}
              className="text-4xl transition-transform hover:scale-110 active:scale-95 disabled:opacity-40"
              aria-label={`${star} estrelas`}
            >
              <span className={active ? "text-tertiary" : "text-outline-variant"}>
                {active ? "★" : "☆"}
              </span>
            </button>
          );
        })}
      </div>
      {rating > 0 && (
        <div className="space-y-3 pt-2">
          <div className="rounded-xl bg-surface-container-highest p-3 focus-glow transition-all">
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="Comentário opcional..."
              maxLength={500}
              className="w-full bg-transparent outline-none text-sm text-on-surface placeholder:text-outline resize-none"
              rows={2}
            />
          </div>
          <button
            onClick={() => {
              onSubmit(rating, comment || undefined);
              setSubmitted(true);
            }}
            disabled={disabled}
            className="bg-ai-pulse text-on-primary font-semibold px-5 py-2.5 rounded-full shadow-cta-glow active:scale-95 transition disabled:opacity-50 text-sm"
          >
            Enviar feedback
          </button>
        </div>
      )}
    </div>
  );
}
