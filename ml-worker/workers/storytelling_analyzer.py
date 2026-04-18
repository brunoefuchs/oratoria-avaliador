"""Story 7.3 — Storytelling Analyzer (local-first com fallback LLM opcional).

Mede arquitetura da mensagem (NAO delivery): bridge sentence, opening hook, CTA,
e chemicals (dopamine + oxytocin) — 2 dos 4 do framework Vinh.

Vinh framework relevante:
- Bridge sentence ("the reason I'm telling you this is...") = conecta historia → audiencia
- Opening hook = primeiros 7 segundos decidem tudo
- CTA = convite a acao no fechamento
- 4 Chemicals: dopamine (curiosidade), oxytocin (vulnerabilidade), endorphins (humor — TODO), cortisol (anti-pattern)

Decisao do spike Task 0: regex-first determinístico (zero nova dependencia)
+ fallback LLM opt-in via env STORYTELLING_USE_LLM=true.
"""

import os
import re

import structlog

logger = structlog.get_logger()

# ─────────────────────────────────────────────────────────────────────────────
# PADROES PT-BR (validados via amostra de transcripts oratoria-avaliador)
# Ajustar via Task 8 com videos de calibracao.
# ─────────────────────────────────────────────────────────────────────────────

# Bridge sentence — frase que conecta historia/dado ao publico
BRIDGE_PATTERNS = [
    r"\b(a\s+)?raz[ãa]o (de eu )?(estar )?(te |lhe )?(contando|falando|compartilhando|dizendo) isso",
    r"\b(o\s+)?motivo (de eu |pra te |para te |de )?(contar|compartilhar|falar)",
    r"\btrago isso (aqui )?porque",
    r"\bisto (impor|interes)ta (para|pra) voc[êe] porque",
    r"\bo que isso significa (pra|para) voc[êe]",
    r"\bpor que (eu )?(estou )?(te )?(dizendo|contando|falando) isso",
    r"\bisso (interes|impor)ta (pra|para) voc[êe] porque",
    r"\b(eu )?(estou |vou )?(compartilho|compartilhando) isso (pra|para) voc[êe]",
    r"\bo ponto (aqui )?[ée]:?\s",
    r"\ba li[çc][ãa]o (aqui )?[ée]:?\s",
]

# CTA (Call to Action) — imperativos + convites
CTA_PATTERNS = [
    r"\b(eu )?te convido (a|para|pra)\s",
    r"\bcomece (hoje|agora|j[áa])",
    r"\bo pr[óo]ximo passo",
    r"\b(experimente|tente|fa[çc]a|veja|olhe|escute|escreva|grave|teste|comece|aplique|implemente|pratique)\s.{1,30}\b(hoje|agora|amanh[ãa]|essa\s+semana|esse\s+m[êe]s|j[áa])\b",
    r"\bvoc[êe] pode\s.{1,30}\b(hoje|agora)\b",
    r"\b(eu )?te chamo (para|pra)\s",
    r"\bse vira[çc]o[uem]?\s.{1,40}\b(comece|fa[çc]a|tente|teste)\b",
    r"\bclique no link",
    r"\bdescobr.{1,5} mais em\s",
    r"\bagora\s+[ée]\s+sua\s+vez\b",
]

# Hook patterns — tipos
HOOK_PATTERNS = {
    "question": [r"\?"],  # presença de "?"
    "story": [
        r"\bquando (eu|tinha)\b",
        r"\bh[áa] (\d+|[a-z]+)\s+(anos|meses|dias)\b",
        r"\bera uma vez\b",
        r"\bimagine\b",
        r"\blembro (que|quando|de)\b",
        r"\bvou contar\b",
    ],
    "stat": [
        r"\b\d+%\b",
        r"\b\d+\s+(milh[õo]es|bilh[õo]es|mil)\b",
        r"\b(metade|dois ter[çc]os|um ter[çc]o|tres em cada|9 em cada)\b",
    ],
    "vulnerability": [
        r"\beu (falhei|errei|n[ãa]o sabia|tive medo|fiquei perdid[oa]|me senti)",
        r"\bnunca (consegui|tive coragem)",
        r"\bera o pior\b",
    ],
    "challenge": [
        r"\b(voc[êe]|voces) j[áa] (parou|pararam|sentiu|sentiram|notou|notaram)",
        r"\bquantos de voc[êe]s",
        r"\bquem aqui (j[áa] |nunca |sente)",
    ],
    "magic_trick": [
        # Reservado para humor/surpresa — dificil detectar com regex sem falso positivo.
        # Mantemos vazio: detection vira "none" se nenhum outro tipo bater.
    ],
}

# Chemicals — dopamine (loops abertos, suspense)
DOPAMINE_PATTERNS = [
    r"\bvou (te )?contar (algo |uma coisa )?(surpreendente|que vai te surpreender|incri[íi]vel)",
    r"\b(em )?(\d+|alguns|tres|quatro|cinco) (segundos|minutos), voc[êe] vai\b",
    r"\bem instantes (eu )?vou (revelar|mostrar|contar)",
    r"\bguarde (essa |isso |essa frase|esse n[úu]mero)",
    r"\bspoiler:",
    r"\bvolto (a |em )?(isso|nisso) j[áa]",
]

# Chemicals — oxytocin (vulnerabilidade autodeclarada)
OXYTOCIN_PATTERNS = [
    r"\beu (falhei|errei|n[ãa]o sabia|tive medo|fiquei perdid[oa])",
    r"\bme senti (sozinh[oa]|fracassad[oa]|impotente|desesperad[oa]|envergonhad[oa])",
    r"\bn[ãa]o tinha (resposta|ideia|coragem|nada)",
    r"\bera (o |a )?(pior|mais (frac[oa]|insegur[oa]))",
    r"\b(perdi|falhei|fracassei) (em|no|na|com)",
    r"\b(at[ée] )?chorei",
]

# Cortisol risk — proxy textual (delivery cortisol vem de variety analyzer; aqui só palavras)
CORTISOL_TEXT_PATTERNS = [
    r"\b(p[ãa]nico|terror|desespero|ang[úu]stia|ansiedade)\b",
    r"\bperigo iminente",
    r"\bcatastr[óo]f(e|ico)",
]

OPENING_PCT = 0.20  # primeiros 20% do transcript
CLOSING_PCT = 0.15  # ultimos 15%


def _count_matches(text: str, patterns: list) -> tuple[int, list[str]]:
    """Conta matches de uma lista de padroes regex e retorna excerpts."""
    excerpts = []
    count = 0
    for pat in patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            count += 1
            # Excerpt: 40 chars around the match
            start = max(0, m.start() - 20)
            end = min(len(text), m.end() + 40)
            excerpts.append(text[start:end].strip())
    return count, excerpts[:3]


def _detect_bridge(text: str) -> dict:
    count, excerpts = _count_matches(text, BRIDGE_PATTERNS)
    return {
        "detected": count > 0,
        "count": count,
        "excerpts": excerpts,
    }


def _detect_cta(closing_text: str) -> dict:
    count, excerpts = _count_matches(closing_text, CTA_PATTERNS)
    return {
        "detected": count > 0,
        "excerpt": excerpts[0] if excerpts else None,
    }


def _classify_hook(opening_text: str) -> dict:
    """Identifica tipo dominante de hook nos primeiros 20%."""
    scores = {}
    for hook_type, patterns in HOOK_PATTERNS.items():
        if not patterns:
            continue
        count, _ = _count_matches(opening_text, patterns)
        scores[hook_type] = count

    if not any(scores.values()):
        return {"type": "none", "strength": "weak"}

    dominant = max(scores, key=scores.get)
    total = sum(scores.values())
    strength = "strong" if scores[dominant] >= 2 or total >= 3 else "medium"
    if scores[dominant] >= 1 and strength != "strong":
        strength = "medium"
    return {"type": dominant, "strength": strength}


def _detect_chemicals(text: str, variety_metrics: dict | None) -> dict:
    """Detecta presenca de chemicals via texto + cross-reference variety."""
    dopamine_count, dopamine_ex = _count_matches(text, DOPAMINE_PATTERNS)
    oxytocin_count, oxytocin_ex = _count_matches(text, OXYTOCIN_PATTERNS)
    cortisol_text_count, _ = _count_matches(text, CORTISOL_TEXT_PATTERNS)

    # Cortisol risk: cross-reference com variety (monotonia) se disponivel.
    # Story 7.3 fix QA — mensagem com mais contexto pedagogico pro usuario.
    cortisol_risk = False
    cortisol_reason = ""
    if variety_metrics:
        pct_monotono = variety_metrics.get("pct_tempo_monotono", 0)
        if pct_monotono > 60 and dopamine_count == 0 and oxytocin_count == 0:
            cortisol_risk = True
            cortisol_reason = (
                f"Risco de desengajamento: {pct_monotono}% da fala foi monotona "
                "(sem variacao vocal) E nenhuma estrutura narrativa que prenda atencao. "
                "Cortisol e quimica do desconforto — audiencia tende a parar de prestar atencao "
                "ou trocar de aba. Variar tom + adicionar uma historia/pergunta resolve."
            )
    if cortisol_text_count > 2 and not cortisol_reason:
        cortisol_risk = True
        cortisol_reason = (
            "Vocabulario com carga negativa elevada (panico/desespero/catastrofe). "
            "Use com moderacao — sobrecarga emocional negativa cansa a audiencia."
        )

    return {
        "dopamine": {
            "detected": dopamine_count > 0,
            "examples": dopamine_ex,
        },
        "oxytocin": {
            "detected": oxytocin_count > 0,
            "examples": oxytocin_ex,
        },
        "endorphins": "not_yet_implemented",
        "cortisol_risk": {
            "detected": cortisol_risk,
            "reason": cortisol_reason,
        },
    }


def _compute_score(bridge: dict, hook: dict, cta: dict, chemicals: dict) -> tuple[int, str]:
    """Score 0-100 + diagnostico textual."""
    # B4-real: base elevado de 20→45. Storytelling framework assume narrativa
    # (Bridge sentence canonica). Conteudo educacional/axiomatico valido cai
    # fora dos patterns mas nao e "narrativa ausente" — e outra categoria.
    score = 45  # base neutro

    if bridge["detected"]:
        score += 15
    if hook["type"] != "none":
        if hook["strength"] == "strong":
            score += 15
        elif hook["strength"] == "medium":
            score += 8
        else:
            score += 4
    if cta["detected"]:
        score += 15
    if chemicals["dopamine"]["detected"]:
        score += 10
    if chemicals["oxytocin"]["detected"]:
        score += 10
    if chemicals["cortisol_risk"]["detected"]:
        score -= 25

    score = max(0, min(100, score))

    if score >= 80:
        diagnostico = "narrativa_excepcional"
    elif score >= 60:
        diagnostico = "narrativa_solida"
    elif score >= 35:
        diagnostico = "narrativa_basica"
    else:
        diagnostico = "narrativa_ausente"

    return score, diagnostico


def _generate_suggestions(bridge: dict, hook: dict, cta: dict, chemicals: dict) -> list[str]:
    """Sugestoes acionaveis se score < 70."""
    suggestions = []
    if not bridge["detected"]:
        suggestions.append(
            "Adicione uma BRIDGE sentence: 'A razao de eu estar te contando isso e...' "
            "Sem ela, sua historia serve voce, nao a audiencia."
        )
    if hook["type"] == "none":
        suggestions.append(
            "Comece com um HOOK forte: pergunta reflexiva, dado chocante, "
            "ou historia pessoal (vulnerabilidade). Os primeiros 7 segundos decidem tudo."
        )
    elif hook["strength"] == "weak":
        suggestions.append(
            f"Seu hook ({hook['type']}) e fraco. Aprofunde — adicione detalhe sensorial ou tensao."
        )
    if not cta["detected"]:
        suggestions.append(
            "Termine com um CTA claro: 'Comece hoje', 'O proximo passo e...', "
            "'Experimente isso essa semana'. Sem CTA, a fala vira informacao, nao transformacao."
        )
    if not chemicals["dopamine"]["detected"] and not chemicals["oxytocin"]["detected"]:
        suggestions.append(
            "Sua fala nao acionou chemicals positivos. Considere abrir um loop "
            "(suspense/curiosidade) ou compartilhar uma vulnerabilidade autentica."
        )
    if chemicals["cortisol_risk"]["detected"]:
        suggestions.append(
            f"ATENCAO: risco de cortisol detectado. {chemicals['cortisol_risk']['reason']}"
        )
    return suggestions[:3]


def _hook_from_opening_result(opening_result: dict) -> dict | None:
    """Story 7.3 fix QA — reusa classificacao do opening_analyzer ao inves de re-classificar.

    Mapping opening_analyzer.tecnicas_detectadas → storytelling hook format.
    """
    if not opening_result or not opening_result.get("disponivel"):
        return None
    tecnicas = opening_result.get("tecnicas_detectadas", [])
    if not tecnicas:
        return {"type": "none", "strength": "weak"}
    primeira = tecnicas[0]
    tecnica_id = primeira.get("tecnica", "")
    qualidade = primeira.get("qualidade", "fraca")
    # Map tecnica_id → storytelling hook type
    type_map = {
        "pergunta_reflexiva": "question",
        "pergunta_casual": "question",
        "dado_chocante": "stat",
        "gancho_historia": "story",
        "frase_impacto": "vulnerability",
        "quebra_gelo": "challenge",
        "conexao_audiencia": "challenge",
        "citacao_autoridade": "stat",
    }
    hook_type = type_map.get(tecnica_id, "none")
    # qualidade: opening_analyzer usa "boa"/"fraca", storytelling usa "weak/medium/strong"
    if qualidade == "boa":
        strength = "strong" if len(tecnicas) >= 2 else "medium"
    else:
        strength = "weak"
    return {"type": hook_type, "strength": strength}


def _compute_storytelling_metrics(
    transcript: dict,
    variety_metrics: dict | None = None,
    opening_result: dict | None = None,
) -> dict:
    """Analisa estrutura narrativa do transcript.

    Args:
        transcript: dict com 'full_text' e 'words' (output do whisper)
        variety_metrics: dict opcional com pct_tempo_monotono etc (cross-reference)
        opening_result: dict opcional do opening_analyzer (story 7.3 fix consistencia)
            Se passado, hook reusa classificacao do opening_analyzer ao inves de re-classificar.
    """
    full_text = transcript.get("full_text", "")
    if not full_text or len(full_text.split()) < 30:
        logger.warning("storytelling_text_too_short")
        return _disponivel_false("Transcript muito curto para analise narrativa")

    text_lower = full_text.lower()
    text_len = len(text_lower)
    opening_text = text_lower[: int(text_len * OPENING_PCT)]
    closing_text = text_lower[int(text_len * (1 - CLOSING_PCT)) :]

    bridge = _detect_bridge(text_lower)
    # Story 7.3 fix QA: prefer opening_analyzer classification (consistencia cross-worker)
    hook_from_opening = _hook_from_opening_result(opening_result)
    hook = hook_from_opening if hook_from_opening else _classify_hook(opening_text)
    cta = _detect_cta(closing_text)
    chemicals = _detect_chemicals(text_lower, variety_metrics)
    score, diagnostico = _compute_score(bridge, hook, cta, chemicals)
    suggestions = _generate_suggestions(bridge, hook, cta, chemicals) if score < 70 else []

    # AC-9 — fallback LLM opcional (default off)
    use_llm = os.environ.get("STORYTELLING_USE_LLM", "false").lower() == "true"
    if use_llm:
        # Hook: futuro — chamada Gemini para refinar deteccao em casos border-line.
        # Por ora, log e segue com regex.
        logger.info("storytelling_llm_flag_set_but_not_implemented")

    logger.info(
        "storytelling_analysis_complete",
        score=score,
        diagnostico=diagnostico,
        bridge_detected=bridge["detected"],
        hook_type=hook["type"],
        cta_detected=cta["detected"],
    )

    return {
        "disponivel": True,
        "score": score,
        "diagnostico": diagnostico,
        "bridge_sentence": bridge,
        "opening_hook": hook,
        "cta": cta,
        "chemicals": chemicals,
        "suggestions": suggestions,
    }


def _disponivel_false(motivo: str) -> dict:
    return {
        "disponivel": False,
        "score": 0,
        "diagnostico": "indisponivel",
        "bridge_sentence": {"detected": False, "count": 0, "excerpts": []},
        "opening_hook": {"type": "none", "strength": "weak"},
        "cta": {"detected": False, "excerpt": None},
        "chemicals": {
            "dopamine": {"detected": False, "examples": []},
            "oxytocin": {"detected": False, "examples": []},
            "endorphins": "not_yet_implemented",
            "cortisol_risk": {"detected": False, "reason": ""},
        },
        "suggestions": [motivo],
    }


# Story 8.3 — Truth Contract
from contracts import WorkerFailure, WorkerResult, WorkerSuccess  # noqa: E402


def analyze_storytelling_legacy(
    transcript: dict,
    variety_metrics: dict | None = None,
    opening_result: dict | None = None,
) -> dict:
    """Legacy path (TRUTH_CONTRACT_ENABLED=false)."""
    return _compute_storytelling_metrics(transcript, variety_metrics, opening_result)


def analyze_storytelling(
    transcript: dict,
    variety_metrics: dict | None = None,
    opening_result: dict | None = None,
) -> "WorkerResult":
    """Truth Contract path — retorna WorkerResult (Pydantic).

    Adapta disponivel:bool pattern:
    - disponivel=True + score → WorkerSuccess
    - disponivel=False → WorkerFailure(skipped)
    - Exception → WorkerFailure(crashed)
    """
    try:
        result = _compute_storytelling_metrics(transcript, variety_metrics, opening_result)
        if not result.get("disponivel", True):
            reason = result.get("suggestions", ["indisponivel"])
            reason_str = reason[0] if reason else "analise de storytelling indisponivel"
            return WorkerFailure(
                dimension="storytelling",
                dimension_status="skipped",
                failure_reason=reason_str,
                metrics=result,
            )
        score = result.get("score")
        if score is None:
            return WorkerFailure(
                dimension="storytelling",
                dimension_status="insufficient_data",
                failure_reason="score is None after storytelling analysis",
            )
        metrics = {k: v for k, v in result.items() if k not in ("score", "disponivel")}
        return WorkerSuccess(
            dimension="storytelling",
            score=max(0, min(100, int(score))),
            metrics=metrics,
            confidence=1.0,
        )
    except Exception as e:
        logger.error(
            "storytelling_crashed", error_type=type(e).__name__, error=str(e), exc_info=True
        )
        return WorkerFailure(
            dimension="storytelling",
            dimension_status="crashed",
            failure_reason=f"{type(e).__name__}: {str(e)}",
        )
