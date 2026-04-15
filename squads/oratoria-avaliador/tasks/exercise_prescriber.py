"""
exercise_prescriber.py
──────────────────────
Mapeia cada problema ranqueado (top-N) para exercício prescrito na voz do
mentor escolhido. Epic 3 — Story 3.4.

Library de exercícios é mentor-específica:
- gui-reginatto: automodelagem 3 etapas, exposição progressiva, neutral ears,
  piramide I-C-M, FRN decomposição vetorial
- vinh-giang: 12-week plan, verbal highlighter, volume contrast, archetype
  cycling, 88 keys practice

Determinístico. Output: lista de exercícios linkados por dimensão problema.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# LIBRARY — mentor × dimensão → exercício
# ─────────────────────────────────────────────────────────────────────────────

EXERCISES: dict[str, dict[str, list[dict[str, Any]]]] = {
    "gui-reginatto": {
        "voice": [
            {
                "id": "gui_voice_01",
                "name": "Automodelagem em 3 Etapas",
                "duration_weeks": 2,
                "steps": [
                    "Grava 60s sobre qualquer tema que você domina. NÃO POSTA.",
                    "Etapa 1 — VER com áudio (reação natural).",
                    "Etapa 2 — OUVIR sem ver: como soa sua voz? Monotona? Variação? WPM?",
                    "Etapa 3 — VER sem ouvir: o que o corpo diz?",
                    "Anota 3 coisas que surpreenderam. Volta e conta.",
                ],
                "source": "squads/squad-creator-pro/minds/gui_reginatto/thinking_dna.yaml — Automodelagem em 3 Etapas",
                "mentor_voice": "Não é vaidade, é calibragem.",
            },
        ],
        "body": [
            {
                "id": "gui_body_01",
                "name": "Presença — Exposição Progressiva",
                "duration_weeks": 3,
                "steps": [
                    "Semana 1: gravar stories curtos (15s). Só isso.",
                    "Semana 2: 3 lives curtas com audiência pequena (family + friends).",
                    "Semana 3: uma apresentação real (reunião, palco pequeno).",
                    "Review semanal: postura, amplitude de gesto, ocupação de espaço.",
                ],
                "source": "thinking_dna.yaml — Exposição Progressiva",
                "mentor_voice": "A exposição gera vendas. Quem se esconde não converte.",
            },
        ],
        "face": [
            {
                "id": "gui_face_01",
                "name": "Rapport Facial em Neutral Ears",
                "duration_weeks": 2,
                "steps": [
                    "Conversa de 2 minutos com alguém neutro (barista, vizinho).",
                    "Foco: sorriso natural + contato visual variado.",
                    "Depois: grava a mesma fala sozinho. Compara. A face muda?",
                    "A ausência de audiência revela o default facial.",
                ],
                "source": "thinking_dna.yaml — Neutral Ears + Rapport",
                "mentor_voice": "Você trava quando tem câmera. Vamos descobrir o porquê.",
            },
        ],
        "storytelling": [
            {
                "id": "gui_story_01",
                "name": "Bridge Structure — Encontre sua Ponte",
                "duration_weeks": 2,
                "steps": [
                    "Escolhe UMA história pessoal que você já conta.",
                    "Pergunte: qual é o INSIGHT transferível? Qual ponte liga essa história à realidade do ouvinte?",
                    "Reescreve com bridge explícita: 'o motivo de te contar isso é que...'",
                    "Testa em 3 conversas reais. Observa se a audiência LEMBRA ou só sente pena.",
                ],
                "source": "Bridge Structure (Vinh) adaptada ao método comuniCAR",
                "mentor_voice": "Sua história tem que SERVIR quem ouve, não você.",
            },
        ],
        "tonality": [
            {
                "id": "gui_tonality_01",
                "name": "Senoide Emocional — Calibrar Picos e Vales",
                "duration_weeks": 2,
                "steps": [
                    "Grava 60s falando sobre um tema que te mexe de verdade.",
                    "Ouça sem ver: onde está o pico emocional? Onde está o vale?",
                    "Se a curva é plana: você está no piloto automático. Essa é a raiz do 'monótono'.",
                    "Regrava forçando UM pico alto (entusiasmo) e UM vale baixo (sussurro reflexivo).",
                    "Encantamento > persuasão. O ouvinte sente a senoide antes de entender as palavras.",
                ],
                "source": "Método comuniCAR — Senoide Emocional + 5 Canais de Autoridade",
                "mentor_voice": "Voz plana não converte. Você precisa criar a experiência emocional.",
            },
        ],
    },
    "vinh-giang": {
        "voice": [
            {
                "id": "vinh_voice_01",
                "name": "Verbal Highlighter + Volume Contrast",
                "duration_weeks": 3,
                "steps": [
                    "Week 1-3: SLOW DOWN dramatically on your most important point.",
                    "Week 4-6: contrast — drop volume DOWN, not up. From 7 to 2 beats 7 to 10.",
                    "Record one meeting. Count slowdowns. If zero: that's your default.",
                ],
                "source": "squads/squad-creator-pro/minds/vinh_giang/thinking_dna.yaml — Verbal Highlighter + Volume Contrast",
                "mentor_voice": "Your voice is an instrument. Start playing more keys.",
            },
        ],
        "body": [
            {
                "id": "vinh_body_01",
                "name": "Be As Big As The Room",
                "duration_weeks": 2,
                "steps": [
                    "Medir amplitude de gesto em gravação atual.",
                    "Aumentar conscientemente 30%. Gravar de novo.",
                    "Comparar. Scale to the room.",
                ],
                "source": "thinking_dna.yaml — Be As Big As The Room",
                "mentor_voice": "Small room = small energy. Big room = big presence.",
            },
        ],
        "face": [
            {
                "id": "vinh_face_01",
                "name": "Archetype Cycling (Coach → Friend → Educator)",
                "duration_weeks": 2,
                "steps": [
                    "Week 1: start every meeting with 30s of Friend archetype (warm, conversational).",
                    "Week 2: add Educator before Coach (context before directive).",
                    "Record before/after. The face follows the archetype.",
                ],
                "source": "thinking_dna.yaml — 4 Archetypes",
                "mentor_voice": "Anytime anything becomes default, it becomes non-functional.",
            },
        ],
        "storytelling": [
            {
                "id": "vinh_story_01",
                "name": "Bridge Structure + 4 Chemicals",
                "duration_weeks": 2,
                "steps": [
                    "Pick ONE story you tell. Which chemical? (Oxytocin/Dopamine/Endorphin/Cortisol)",
                    "Scene + Emotion + Characters + BRIDGE + Insight.",
                    "Tell to 3 strangers this week. Record. Review archetypes used.",
                    "Without the bridge: 'wow, poor thing'. With: 'that changed how I think.'",
                ],
                "source": "thinking_dna.yaml — Bridge Structure + 4 Storytelling Chemicals",
                "mentor_voice": "Your story serves them, not you.",
            },
        ],
        "tonality": [
            {
                "id": "vinh_tonality_01",
                "name": "Emotional Range — Play More Keys",
                "duration_weeks": 3,
                "steps": [
                    "Record yourself speaking about something you actually care about.",
                    "Listen audio-only: what's your emotional register? Mostly one note?",
                    "Map the 4 archetypes to emotional tones — Coach (sharp), Friend (warm), Educator (curious), Motivator (uplifting).",
                    "Re-record cycling through at least 3 archetypes in 60 seconds.",
                    "The most inauthentic thing you can do is only play these keys over here.",
                ],
                "source": "thinking_dna.yaml — 4 Archetypes + 88 Keys",
                "mentor_voice": "Anytime anything becomes default, it becomes non-functional.",
            },
        ],
    },
}


def prescribe(hierarchy: dict[str, Any], mentor: str) -> dict[str, Any]:
    """Para cada problema em hierarchy.problems, linka exercício(s) do mentor.

    Retorna exercise_plan.json — cada top-N tem ≥1 exercício (PRD G6_EXERCISE_LINKAGE).
    """
    if mentor not in EXERCISES:
        return {
            "error": f"Mentor desconhecido: {mentor}",
            "evaluation_id": hierarchy.get("evaluation_id"),
            "exercises_by_problem": [],
        }

    library = EXERCISES[mentor]
    plan: list[dict[str, Any]] = []

    for problem in hierarchy.get("problems", []):
        dim = problem["dimension"]
        exs = library.get(dim, [])
        plan.append({
            "rank": problem["rank"],
            "dimension": dim,
            "score": problem["score"],
            "exercises": exs,
            "primary_exercise_id": exs[0]["id"] if exs else None,
            "has_exercise": bool(exs),
        })

    coverage_ok = all(item["has_exercise"] for item in plan)

    return {
        "schema_version": "1.0.0",
        "evaluation_id": hierarchy.get("evaluation_id"),
        "mentor": mentor,
        "exercises_by_problem": plan,
        "g6_exercise_linkage_pass": coverage_ok,
    }
