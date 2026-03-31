import re

import structlog

logger = structlog.get_logger()

# Common PT-BR fillers
FILLER_PATTERNS = [
    r"\bné\b",
    r"\btipo\b",
    r"\bentão\b",
    r"\bentao\b",
    r"\béee+\b",
    r"\beee+\b",
    r"\bhum+\b",
    r"\baí\b",
    r"\bai\b",
    r"\bassim\b",
    r"\bbasicamente\b",
    r"\bna verdade\b",
    r"\bdigamos\b",
    r"\bvamos dizer\b",
    r"\btá\b",
    r"\bta\b",
]

FILLER_REGEX = re.compile("|".join(FILLER_PATTERNS), re.IGNORECASE)


def detect_fillers(transcription: dict) -> dict:
    """Detect filler words in transcription with timestamps and context."""
    words = transcription.get("words", [])
    audio_duration = 0.0

    if words:
        audio_duration = words[-1].get("end", 0.0) - words[0].get("start", 0.0)

    fillers_found = []
    filler_counts: dict[str, int] = {}

    for i, word_info in enumerate(words):
        word = word_info["word"]
        if FILLER_REGEX.search(word):
            # Get context (3 words before and after)
            context_before = " ".join(w["word"] for w in words[max(0, i - 3) : i])
            context_after = " ".join(
                w["word"] for w in words[i + 1 : min(len(words), i + 4)]
            )

            filler_entry = {
                "word": word.lower().strip(),
                "timestamp": word_info.get("start", 0.0),
                "context": f"...{context_before} [{word}] {context_after}...",
            }
            fillers_found.append(filler_entry)

            normalized = word.lower().strip()
            filler_counts[normalized] = filler_counts.get(normalized, 0) + 1

    # Fillers per minute
    duration_minutes = audio_duration / 60 if audio_duration > 0 else 1
    fillers_per_minute = round(len(fillers_found) / duration_minutes, 1)

    # Top 3 fillers
    top_fillers = sorted(filler_counts.items(), key=lambda x: x[1], reverse=True)[:3]

    # Lexical diversity (type-token ratio)
    all_words = [w["word"].lower().strip() for w in words if w["word"].strip()]
    unique_words = set(all_words)
    type_token_ratio = (
        round(len(unique_words) / len(all_words), 3) if all_words else 0.0
    )

    # Filler score (0-100): fewer fillers = higher score
    # Target: < 3 fillers/min = 100, > 10 fillers/min = 0
    if fillers_per_minute <= 3:
        filler_score = 100
    elif fillers_per_minute >= 10:
        filler_score = 0
    else:
        filler_score = round(100 - (fillers_per_minute - 3) * (100 / 7))

    filler_score = max(0, min(100, filler_score))

    logger.info(
        "filler_detection_complete",
        total_fillers=len(fillers_found),
        fillers_per_minute=fillers_per_minute,
        top_fillers=top_fillers,
    )

    return {
        "score": filler_score,
        "fillers_per_minute": fillers_per_minute,
        "total_fillers": len(fillers_found),
        "top_fillers": [{"word": w, "count": c} for w, c in top_fillers],
        "type_token_ratio": type_token_ratio,
        "fillers": fillers_found,
    }
