"""
scoring_engine.py
─────────────────
Agrega features brutas de features_canonical.json em scores por dimensão (0-100)
aplicando pesos contextuais derivados do questionário 6.Q.

Epic 2 — Story 2.1. Substitui pela sua responsabilidade a lógica de scoring que
hoje vive em ml-worker/workers/aggregator.py (que mistura captura + scoring —
ver PRD seção 7.2: separation of concerns).

Input:  features_canonical (v1.0.0 validated) + evaluation_context (questionário 6.Q)
Output: scores_by_dimension.json
    {
      "schema_version": "1.0.0",
      "evaluation_id": "...",
      "weights_source": "motivacao:vender_mais → vendas" | "default",
      "applied_weights": { "voice": 0.20, "body": 0.35, ... },
      "dimension_scores": {
        "voice": { "score": 72.5, "evidence": [...], "confidence": "high" },
        "body": { "score": 68.0, ... },
        ...
      },
      "overall_score": 71.2,
      "incomplete_dimensions": []
    }

Princípios operacionais:
- Score 0-100 (0=péssimo, 100=ideal)
- Cada score tem evidence linkada (feature + valor de referência)
- Dimensão ausente vai para incomplete_dimensions (não é erro, é parcial)
- Pesos contextuais vêm de PESOS_POR_CONTEXTO (alinhado com ml-worker/aggregator.py
  para não quebrar compat até migração completa)
"""

from __future__ import annotations

from typing import Any

# ─────────────────────────────────────────────────────────────────────────────
# PESOS CONTEXTUAIS (canonical em Epic 2 — espelha ml-worker/aggregator.py v1)
# ─────────────────────────────────────────────────────────────────────────────

PESOS_DEFAULT = {
    "voice": 0.24,
    "body": 0.36,  # posture (0.18) + gesture (0.18)
    "face": 0.15,
    "storytelling": 0.25,
    # tonality adicionada via wf-evolve-dimension em v1.1.0
    # peso 0.0 default = neutro (não afeta overall até calibração explícita)
    "tonality": 0.0,
}

PESOS_POR_CONTEXTO: dict[str, dict[str, float]] = {
    "palco": {"voice": 0.20, "body": 0.40, "face": 0.15, "storytelling": 0.25},
    "podcast": {"voice": 0.50, "body": 0.10, "face": 0.10, "storytelling": 0.30},
    "vendas": {"voice": 0.25, "body": 0.25, "face": 0.20, "storytelling": 0.30},
    "rede_social": {"voice": 0.20, "body": 0.25, "face": 0.25, "storytelling": 0.30},
    "reuniao": {"voice": 0.30, "body": 0.25, "face": 0.15, "storytelling": 0.30},
    "aula": {"voice": 0.25, "body": 0.25, "face": 0.15, "storytelling": 0.35},
}

MOTIVACAO_TO_CONTEXTO = {
    "redes_sociais": "rede_social",
    "vender_mais": "vendas",
    "carreira": "reuniao",
    "palestrar": "palco",
    "satisfacao_pessoal": None,
    "outro": None,
}

# ─────────────────────────────────────────────────────────────────────────────
# SCORING PRIMITIVES — cada dimensão tem função dedicada com fórmula explícita
# ─────────────────────────────────────────────────────────────────────────────

WPM_IDEAL_MIN = 130
WPM_IDEAL_MAX = 170
WPM_IDEAL_CENTER = 150


def _clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def _score_voice(voice: dict) -> tuple[float, list[dict]]:
    """Voice score: prosódia + filler rate + WPM proximity.

    Retorna (score_0_100, evidence_list).
    """
    evidence: list[dict] = []
    components: list[tuple[float, float]] = []  # (score, weight)

    prosody = voice.get("prosody") or {}
    pitch_std = prosody.get("pitch_std_hz")
    if pitch_std is not None:
        # Variação prosódica saudável: std entre 25-60 Hz
        if pitch_std < 15:
            s = 30.0
            why = "pitch monótono (std < 15Hz)"
        elif pitch_std > 70:
            s = 55.0
            why = "pitch instável (std > 70Hz)"
        else:
            s = _clamp(50 + (pitch_std - 15) * 0.9)
            why = f"pitch_std={pitch_std}Hz dentro da faixa saudável"
        components.append((s, 0.4))
        evidence.append({"feature": "prosody.pitch_std_hz", "value": pitch_std, "score_contribution": s, "why": why})

    wpm = prosody.get("speaking_rate_wpm")
    if wpm is not None:
        if WPM_IDEAL_MIN <= wpm <= WPM_IDEAL_MAX:
            s = 90.0
            why = "WPM dentro do ideal pt-BR (130-170)"
        else:
            delta = min(abs(wpm - WPM_IDEAL_MIN), abs(wpm - WPM_IDEAL_MAX))
            s = _clamp(90 - delta * 0.8)
            why = f"WPM={wpm} fora do ideal"
        components.append((s, 0.3))
        evidence.append({"feature": "prosody.speaking_rate_wpm", "value": wpm, "score_contribution": s, "why": why})

    filler = voice.get("filler_words") or {}
    per_min = filler.get("per_minute")
    if per_min is not None:
        # Até 2/min = excelente. 5+/min = ruim.
        if per_min <= 2:
            s = 95.0
        elif per_min <= 5:
            s = 75.0 - (per_min - 2) * 10
        else:
            s = _clamp(45 - (per_min - 5) * 8)
        components.append((s, 0.3))
        evidence.append({"feature": "filler_words.per_minute", "value": per_min, "score_contribution": s, "why": f"{per_min} fillers/min"})

    if not components:
        return (50.0, [{"note": "voice: sem features suficientes, fallback neutro"}])

    total_w = sum(w for _, w in components)
    score = sum(s * w for s, w in components) / total_w
    return (round(score, 1), evidence)


def _score_body(body: dict) -> tuple[float, list[dict]]:
    evidence: list[dict] = []
    components: list[tuple[float, float]] = []

    posture = body.get("posture_score")
    if posture is not None:
        s = _clamp(posture)
        components.append((s, 0.5))
        evidence.append({"feature": "posture_score", "value": posture, "score_contribution": s})

    amp = body.get("gesture_amplitude")
    variety = body.get("gesture_variety")
    if amp is not None and variety is not None:
        # Gesture: precisa amplitude E variedade. 0.4-0.8 amplitude, >0.4 variety = bom
        amp_ok = 40 + 60 * max(0, min(1, (amp - 0.2) / 0.6))
        var_ok = 40 + 60 * max(0, min(1, variety))
        s = (amp_ok + var_ok) / 2
        components.append((s, 0.5))
        evidence.append({
            "feature": "gesture",
            "amplitude": amp,
            "variety": variety,
            "score_contribution": s,
        })

    if not components:
        return (50.0, [{"note": "body: sem features suficientes"}])
    total_w = sum(w for _, w in components)
    score = sum(s * w for s, w in components) / total_w
    return (round(score, 1), evidence)


def _score_face(face: dict) -> tuple[float, list[dict]]:
    evidence: list[dict] = []
    # Expression entropy > 1.5 = expressivo; smile frequency 0.1-0.4 = natural
    entropy = face.get("expression_entropy")
    smile = face.get("smile_frequency")
    gaze_var = face.get("gaze_variance")
    if entropy is None and smile is None:
        return (50.0, [{"note": "face: sem features suficientes"}])

    components: list[tuple[float, float]] = []
    if entropy is not None:
        s = _clamp(30 + entropy * 30)
        components.append((s, 0.5))
        evidence.append({"feature": "expression_entropy", "value": entropy, "score_contribution": s})

    if smile is not None:
        if 0.1 <= smile <= 0.4:
            s = 85.0
            why = "smile_frequency natural"
        elif smile < 0.1:
            s = _clamp(30 + smile * 500)
            why = "pouco sorriso"
        else:
            s = _clamp(85 - (smile - 0.4) * 100)
            why = "sorriso excessivo (pode indicar nervosismo)"
        components.append((s, 0.3))
        evidence.append({"feature": "smile_frequency", "value": smile, "score_contribution": s, "why": why})

    if gaze_var is not None:
        # gaze_variance 0.2-0.5 = conexão; <0.1 = fixo/agressivo; >0.6 = disperso
        if 0.15 <= gaze_var <= 0.5:
            s = 85.0
        else:
            s = _clamp(85 - abs(gaze_var - 0.3) * 100)
        components.append((s, 0.2))
        evidence.append({"feature": "gaze_variance", "value": gaze_var, "score_contribution": s})

    total_w = sum(w for _, w in components)
    score = sum(s * w for s, w in components) / total_w
    return (round(score, 1), evidence)


def _score_storytelling(story: dict) -> tuple[float, list[dict]]:
    evidence: list[dict] = []
    hints = story.get("narrative_structure_hints") or {}
    arc = story.get("emotional_arc") or []

    components: list[tuple[float, float]] = []

    if hints:
        score_hints = 0.0
        weights_map = {"has_opening_hook": 30, "has_personal_story": 40, "has_call_to_action": 30}
        for k, w in weights_map.items():
            if hints.get(k) is True:
                score_hints += w
                evidence.append({"feature": k, "value": True, "score_contribution": w})
            elif hints.get(k) is False:
                evidence.append({"feature": k, "value": False, "score_contribution": 0})
        components.append((score_hints, 0.6))

    if len(arc) >= 3:
        # arc range = max - min. > 0.3 = bom arco emocional
        arc_range = max(arc) - min(arc)
        s = _clamp(arc_range * 200)
        components.append((s, 0.4))
        evidence.append({"feature": "emotional_arc_range", "value": round(arc_range, 3), "score_contribution": s})

    if not components:
        return (50.0, [{"note": "storytelling: sem features suficientes"}])

    total_w = sum(w for _, w in components)
    score = sum(s * w for s, w in components) / total_w
    return (round(score, 1), evidence)


# ─────────────────────────────────────────────────────────────────────────────
# PÚBLICO — API do módulo
# ─────────────────────────────────────────────────────────────────────────────

def _score_tonality(tonality: dict) -> tuple[float, list[dict]]:
    """Tonality score: VAD-based (Valence / Arousal / Dominance) + emotion variety.

    Adicionada em schema v1.1.0 via wf-evolve-dimension. Peso default 0.0 —
    precisa calibration precedent antes de pesar no overall.
    """
    evidence: list[dict] = []
    components: list[tuple[float, float]] = []

    valence = tonality.get("valence_mean")
    arousal = tonality.get("arousal_mean")
    dominance = tonality.get("dominance_mean")
    variety = tonality.get("emotion_variety")

    if valence is not None:
        # Valence saudável 0.4-0.7 (ligeiramente positivo). Fora: penaliza.
        if 0.4 <= valence <= 0.7:
            s = 85.0
        else:
            s = _clamp(85 - abs(valence - 0.55) * 100)
        components.append((s, 0.3))
        evidence.append({"feature": "valence_mean", "value": valence, "score_contribution": s})

    if arousal is not None:
        # Arousal saudável 0.5-0.8 (energia sem hiperativação).
        if 0.5 <= arousal <= 0.8:
            s = 85.0
        else:
            s = _clamp(85 - abs(arousal - 0.65) * 100)
        components.append((s, 0.3))
        evidence.append({"feature": "arousal_mean", "value": arousal, "score_contribution": s})

    if dominance is not None:
        s = _clamp(30 + dominance * 60)
        components.append((s, 0.2))
        evidence.append({"feature": "dominance_mean", "value": dominance, "score_contribution": s})

    if variety is not None:
        # emotion_variety ∈ [0,1] — mais variedade = mais engajamento
        s = _clamp(variety * 100)
        components.append((s, 0.2))
        evidence.append({"feature": "emotion_variety", "value": variety, "score_contribution": s})

    if not components:
        return (50.0, [{"note": "tonality: sem features suficientes"}])

    total_w = sum(w for _, w in components)
    score = sum(s * w for s, w in components) / total_w
    return (round(score, 1), evidence)


SCORE_FUNCTIONS = {
    "voice": _score_voice,
    "body": _score_body,
    "face": _score_face,
    "storytelling": _score_storytelling,
    "tonality": _score_tonality,  # v1.1.0
}


def resolve_weights(evaluation_context: dict | None) -> tuple[dict[str, float], str]:
    """Resolve pesos a partir de evaluation_context (questionário 6.Q).

    Ordem: motivacao[] → contexto mapeado → default.
    Retorna (pesos, source_label).
    """
    if not evaluation_context:
        return (dict(PESOS_DEFAULT), "default:no_context")

    motivacao = evaluation_context.get("motivacao") or []
    for m in motivacao:
        mapped = MOTIVACAO_TO_CONTEXTO.get(m)
        if mapped and mapped in PESOS_POR_CONTEXTO:
            return (dict(PESOS_POR_CONTEXTO[mapped]), f"motivacao:{m}→{mapped}")

    return (dict(PESOS_DEFAULT), "default:no_mapping")


def score_evaluation(
    features_canonical: dict[str, Any],
    evaluation_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Aplica scoring em todas as dimensões presentes. Retorna scores_by_dimension."""
    evaluation_id = features_canonical.get("evaluation_id")
    dimensions = features_canonical.get("dimensions") or {}

    weights, weights_source = resolve_weights(evaluation_context)

    dimension_scores: dict[str, Any] = {}
    incomplete: list[str] = []

    for dim_name, fn in SCORE_FUNCTIONS.items():
        dim_data = dimensions.get(dim_name)
        if not dim_data:
            incomplete.append(dim_name)
            continue
        score, evidence = fn(dim_data)
        confidence = "high" if evidence and "note" not in evidence[0] else "low"
        dimension_scores[dim_name] = {
            "score": score,
            "evidence": evidence,
            "confidence": confidence,
        }

    # Overall: weighted sum, renormalizado sobre dimensões presentes
    overall = 0.0
    used_weight = 0.0
    for dim_name, entry in dimension_scores.items():
        w = weights.get(dim_name, 0)
        overall += entry["score"] * w
        used_weight += w
    if used_weight > 0:
        overall_score = round(overall / used_weight, 1)
    else:
        overall_score = None

    return {
        "schema_version": "1.0.0",
        "evaluation_id": evaluation_id,
        "weights_source": weights_source,
        "applied_weights": weights,
        "dimension_scores": dimension_scores,
        "incomplete_dimensions": incomplete,
        "overall_score": overall_score,
    }
