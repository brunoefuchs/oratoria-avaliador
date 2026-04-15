"""
mentor_narrator.py
──────────────────
Gera narrativa do relatório na voz do mentor escolhido (gui ou vinh) aplicando
Voice DNA injection no prompt.

Epic 3 — Story 3.2.

Duas modalidades:
1. build_llm_prompt() — constrói prompt com DNA injection para LLM externo
2. render_template_narrative() — render determinístico baseado em templates
   com signature phrases extraídas do DNA (sem LLM — para testes + fallback)

A modalidade "template" existe porque:
- Tests determinísticos (LLM é não-reproduzível)
- Fallback quando LLM provider está offline (PRD 8.4 failure_modes)
- Baseline de fidelity (G4 voice_dna_fidelity ≥ 85%)

Arquivo de saída: mentor_narrative.md
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]  # .../oratoria-avaliador (repo)
MINDS_BASE = REPO_ROOT / "squads" / "squad-creator-pro" / "minds"


def load_voice_dna(mentor: str) -> dict[str, Any]:
    """Carrega voice_dna.yaml do mentor. Requer PyYAML."""
    if not HAS_YAML:
        return {"_error": "PyYAML not installed — load_voice_dna degraded"}
    slug = mentor.replace("-", "_")
    path = MINDS_BASE / slug / "voice_dna.yaml"
    if not path.exists():
        return {"_error": f"voice_dna not found at {path}"}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def extract_signature_phrases(voice_dna: dict[str, Any], limit: int = 10) -> list[str]:
    """Extrai signature phrases limpas do voice_dna. Ignora UNVERIFIED.

    Paths conhecidos (walk recursivo em 'signature_phrases' key):
    - gui: vocabulary.signature_phrases (list of dict)
    - vinh: voice_dna.vocabulary.signature_phrases (nested deeper)
    - ambos podem ter outras seções também
    """
    phrases: list[str] = []

    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == "signature_phrases":
                    if isinstance(v, list):
                        for item in v:
                            p = _extract_phrase(item)
                            if p:
                                phrases.append(p)
                    elif isinstance(v, dict):
                        for section in v.values():
                            if isinstance(section, list):
                                for item in section:
                                    p = _extract_phrase(item)
                                    if p:
                                        phrases.append(p)
                else:
                    walk(v)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(voice_dna)
    # Dedup preservando ordem
    seen = set()
    deduped: list[str] = []
    for p in phrases:
        if p not in seen:
            seen.add(p)
            deduped.append(p)
    return deduped[:limit]


def _extract_phrase(item: Any) -> str | None:
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        p = item.get("phrase")
        src = str(item.get("source", ""))
        if p and "UNVERIFIED" not in src:
            return p
    return None


def extract_power_words(voice_dna: dict[str, Any], limit: int = 15) -> list[str]:
    """Power words top-N (walk recursivo em 'power_words' key)."""
    words: list[str] = []

    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == "power_words" and isinstance(v, list):
                    for item in v:
                        if isinstance(item, str):
                            head = item.split("—")[0].strip()
                            if head:
                                # Pega primeira palavra se tiver separador /
                                head = head.split("/")[0].strip()
                                words.append(head)
                        elif isinstance(item, dict):
                            w = item.get("word")
                            if w:
                                words.append(w.split("/")[0].strip())
                else:
                    walk(v)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(voice_dna)
    seen = set()
    deduped: list[str] = []
    for w in words:
        wl = w.lower()
        if wl and wl not in seen:
            seen.add(wl)
            deduped.append(w)
    return deduped[:limit]


def build_llm_prompt(
    mentor: str,
    hierarchy: dict[str, Any],
    exercise_plan: dict[str, Any],
    evaluation_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Constrói prompt completo com Voice DNA injection para LLM externo."""
    voice_dna = load_voice_dna(mentor)
    signatures = extract_signature_phrases(voice_dna, limit=8)
    power_words = extract_power_words(voice_dna, limit=15)
    identity = voice_dna.get("identity_statement") or (
        voice_dna.get("voice_dna", {}) or {}
    ).get("identity_statement", "")

    system = f"""You are {mentor}. Speak EXACTLY as {mentor} speaks.

IDENTITY:
{identity}

MANDATORY SIGNATURE PHRASES TO USE (at least 2):
{_bullet(signatures)}

POWER WORDS TO WEAVE IN (at least 5):
{', '.join(power_words)}

RULES:
- Speak in first person ("I" / "eu").
- Use the mentor's exact idiom. Never speak like an AI or report.
- Address the user directly, como se estivessem em uma mentoria.
- Language: {"Portuguese (pt-BR)" if mentor == "gui-reginatto" else "English"}.
- Tom: confident, direto, sem hesitação.
"""

    user = _build_user_prompt(hierarchy, exercise_plan, evaluation_context)

    return {
        "mentor": mentor,
        "system": system.strip(),
        "user": user,
        "fidelity_targets": {
            "signature_phrases": signatures,
            "power_words": power_words,
            "min_phrase_hits": 2,
            "min_word_hits": 5,
        },
    }


def _bullet(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "(none)"


def _build_user_prompt(
    hierarchy: dict[str, Any],
    exercise_plan: dict[str, Any],
    ctx: dict[str, Any] | None,
) -> str:
    problems = hierarchy.get("problems", [])
    plan = exercise_plan.get("exercises_by_problem", [])

    ctx_block = ""
    if ctx:
        ctx_block = f"\nCONTEXTO DO USUÁRIO (6.Q):\n- motivacao: {ctx.get('motivacao')}\n- desejo_transmitir: {ctx.get('desejo_transmitir')}\n- desejo_melhorar: {ctx.get('desejo_melhorar')}\n"

    prob_lines = []
    for p in problems:
        prob_lines.append(
            f"  #{p['rank']} — {p['dimension']} (score {p['score']}/100, gap {p['gap_from_target']}): {p['why']}"
        )

    ex_lines = []
    for item in plan:
        exs = item.get("exercises", [])
        if exs:
            ex_lines.append(f"  #{item['rank']} {item['dimension']}: {exs[0]['name']}")

    return f"""Top-{hierarchy.get('top_n', 3)} problemas identificados:
{chr(10).join(prob_lines) or '(nenhum)'}

Exercícios prescritos:
{chr(10).join(ex_lines) or '(nenhum)'}
{ctx_block}
Escreva o relatório narrativo para este speaker, focando no #1 (80/20).
Abra com força, apresente o diagnóstico, prescreva o exercício #1 com detalhes,
feche com encorajamento + próximo passo concreto."""


def render_template_narrative(
    mentor: str,
    hierarchy: dict[str, Any],
    exercise_plan: dict[str, Any],
) -> str:
    """Render determinístico (sem LLM) — para testes + fallback."""
    voice_dna = load_voice_dna(mentor)
    signatures = extract_signature_phrases(voice_dna, limit=3)
    power_words = extract_power_words(voice_dna, limit=5)
    problems = hierarchy.get("problems", [])
    plan = exercise_plan.get("exercises_by_problem", [])

    if not problems:
        return _empty_report(mentor, signatures)

    top = problems[0]
    primary_ex = None
    for item in plan:
        if item["rank"] == 1 and item["exercises"]:
            primary_ex = item["exercises"][0]
            break

    greeting = {
        "gui-reginatto": "Turma,",
        "vinh-giang": "Hey friend,",
    }.get(mentor, "Oi,")

    sig1 = signatures[0] if signatures else ""
    sig2 = signatures[1] if len(signatures) > 1 else ""

    power_inline = ", ".join(power_words[:3])

    problem_line = (
        f"Você está travado em **{top['dimension']}** — score {top['score']}/100. "
        f"{top['why']}"
    )

    exercise_block = ""
    if primary_ex:
        voice_line = primary_ex.get("mentor_voice", "")
        steps = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(primary_ex.get("steps", [])))
        exercise_block = f"""
## Exercício #1 — {primary_ex['name']}
*{voice_line}*

{steps}

Duração: {primary_ex.get('duration_weeks', 2)} semanas.
"""

    return f"""# Relatório na voz de {mentor}

{greeting}

{sig1}

{problem_line}

{sig2}
{exercise_block}
## Próximo passo
Foco em UMA coisa. Não liste 10. Essa semana é {top['dimension']}.
Power words pra lembrar: {power_inline}.

—{mentor}
"""


def _empty_report(mentor: str, signatures: list[str]) -> str:
    sig = signatures[0] if signatures else ""
    return f"""# Relatório — {mentor}

{sig}

Nenhum problema crítico foi identificado. Seus scores estão dentro da faixa saudável.
Continue praticando. Consistência é o bilhete premiado.

—{mentor}
"""
