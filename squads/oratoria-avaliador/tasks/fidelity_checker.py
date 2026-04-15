"""
fidelity_checker.py
───────────────────
Mede Voice DNA fidelity de uma narrativa gerada. G4_VOICE_DNA_FIDELITY — gate
blocking em Epic 4+, mas medido desde Epic 3.

Heurística:
- Conta signature phrases presentes no texto (fuzzy contains, case-insensitive).
- Conta power words.
- Score = (signature_hits / min_signature) * 0.6 + (word_hits / min_word) * 0.4
- Clamped [0, 100].

Threshold G4: ≥ 85% para passar.

Limitação conhecida: heurística lexical é aproximada. Substituir por embedding
similarity ou LLM-as-judge em Epic 4b se necessário.
"""

from __future__ import annotations

import logging
from typing import Any

from mentor_narrator import (
    extract_power_words,
    extract_signature_phrases,
    load_voice_dna,
)

logger = logging.getLogger(__name__)


def measure_fidelity(
    narrative: str,
    mentor: str,
    min_signature_hits: int = 2,
    min_word_hits: int = 5,
) -> dict[str, Any]:
    """Mede fidelidade Voice DNA de uma narrativa gerada.

    Aplica heurística lexical (fuzzy contains + case-insensitive) para contar
    signature phrases e power words do mentor presentes no texto. G4 gate.

    Args:
        narrative: Texto da narrativa gerada (template ou LLM output).
        mentor: Identificador do mentor ("gui-reginatto" | "vinh-giang").
        min_signature_hits: Threshold mínimo para score de signature (default 2).
        min_word_hits: Threshold mínimo para score de power words (default 5).

    Returns:
        dict com as chaves:
          - gate: "G4_VOICE_DNA_FIDELITY"
          - mentor: str
          - fidelity_pct: float (0-100, score agregado: 0.6*sig + 0.4*word)
          - threshold_pct: 85 (constante)
          - result: "PASS" | "FAIL" (PASS se fidelity_pct >= 85)
          - signature_hits: list[str]
          - signature_total_available: int
          - signature_required: int
          - power_word_hits: list[str]
          - power_word_total_available: int
          - power_word_required: int
    """
    voice_dna = load_voice_dna(mentor)
    signatures = extract_signature_phrases(voice_dna, limit=20)
    power_words = extract_power_words(voice_dna, limit=20)

    narrative_lower = narrative.lower()

    # Signature phrase hits — fuzzy contains (primeiras 5 palavras da phrase)
    sig_hits: list[str] = []
    for phrase in signatures:
        core = " ".join(phrase.lower().split()[:5])
        if core and core in narrative_lower:
            sig_hits.append(phrase)

    # Power word hits
    word_hits: list[str] = []
    for w in power_words:
        wl = w.lower().strip()
        if wl and wl in narrative_lower:
            word_hits.append(w)

    sig_score = min(1.0, len(sig_hits) / max(1, min_signature_hits))
    word_score = min(1.0, len(word_hits) / max(1, min_word_hits))
    fidelity_pct = round((sig_score * 0.6 + word_score * 0.4) * 100, 1)

    verdict = "PASS" if fidelity_pct >= 85 else "FAIL"

    return {
        "gate": "G4_VOICE_DNA_FIDELITY",
        "mentor": mentor,
        "fidelity_pct": fidelity_pct,
        "threshold_pct": 85,
        "result": verdict,
        "signature_hits": sig_hits,
        "signature_total_available": len(signatures),
        "signature_required": min_signature_hits,
        "power_word_hits": word_hits,
        "power_word_total_available": len(power_words),
        "power_word_required": min_word_hits,
    }
