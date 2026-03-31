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
      <div className="rounded-lg bg-green-50 p-4 text-center text-sm text-green-700">
        Obrigado pelo feedback!
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-sm font-medium text-gray-700">
        Como voce avalia este relatorio?
      </p>
      <div className="flex gap-1">
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            disabled={disabled}
            onMouseEnter={() => setHover(star)}
            onMouseLeave={() => setHover(0)}
            onClick={() => setRating(star)}
            className="text-3xl transition-transform hover:scale-110"
          >
            {star <= (hover || rating) ? "★" : "☆"}
          </button>
        ))}
      </div>
      {rating > 0 && (
        <>
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Comentario opcional..."
            maxLength={500}
            className="w-full rounded-lg border border-gray-200 p-2 text-sm"
            rows={2}
          />
          <button
            onClick={() => {
              onSubmit(rating, comment || undefined);
              setSubmitted(true);
            }}
            disabled={disabled}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700"
          >
            Enviar
          </button>
        </>
      )}
    </div>
  );
}
