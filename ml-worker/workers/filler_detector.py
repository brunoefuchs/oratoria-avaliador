import re
from collections import Counter

import structlog

logger = structlog.get_logger()

# Muletas retoticas (fim de frase, habito social — menos graves)
MULETAS_RETORICAS = [
    r"\bné\b",
    r"\bne\b",     # Whisper pode transcrever sem acento
    r"\btá\b",
    r"\bta\b",
    r"\bsabe\b",
    r"\bentendeu\b",
    r"\bcerto\b",
]

# Hesitacoes (interrompem o raciocinio — mais graves)
HESITACOES = [
    r"\béee+\b",
    r"\beee+\b",
    r"\bhum+\b",
    r"\bãã+\b",
    r"\baa+\b",
    r"\buhh*\b",
]

# Muletas de conexao (usadas como ponte entre ideias — gravidade media)
MULETAS_CONEXAO = [
    r"\btipo\b",
    r"\bentão\b",
    r"\bentao\b",
    r"\baí\b",
    r"\bai\b",
    r"\bassim\b",
    r"\bbasicamente\b",
    r"\bna verdade\b",
    r"\bdigamos\b",
    r"\bvamos dizer\b",
    r"\bou seja\b",
    r"\bpor exemplo\b",
]

CATEGORIAS = {
    "hesitacao": HESITACOES,
    "muleta_retorica": MULETAS_RETORICAS,
    "muleta_conexao": MULETAS_CONEXAO,
}

# Compilar todos os patterns com categoria
_ALL_PATTERNS = []
for categoria, patterns in CATEGORIAS.items():
    for p in patterns:
        _ALL_PATTERNS.append((re.compile(p, re.IGNORECASE), categoria))

# Pattern unico para deteccao rapida
ALL_FILLER_REGEX = re.compile(
    "|".join(
        p for patterns in CATEGORIAS.values() for p in patterns
    ),
    re.IGNORECASE,
)


def _classificar_filler(word: str) -> str:
    """Retorna a categoria do filler: hesitacao, muleta_retorica, muleta_conexao."""
    word_lower = word.lower().strip()
    for pattern, categoria in _ALL_PATTERNS:
        if pattern.search(word_lower):
            return categoria
    return "muleta_conexao"  # fallback


def _detectar_clusters(fillers_found: list) -> list:
    """Detecta clusters de fillers (3+ em sequencia rapida = red flag).

    Um cluster e quando 3 ou mais fillers ocorrem em menos de 10 segundos.
    """
    if len(fillers_found) < 3:
        return []

    clusters = []
    cluster_atual = [fillers_found[0]]

    for i in range(1, len(fillers_found)):
        gap = fillers_found[i]["timestamp"] - fillers_found[i - 1]["timestamp"]
        if gap < 10.0:  # Menos de 10s entre fillers
            cluster_atual.append(fillers_found[i])
        else:
            if len(cluster_atual) >= 3:
                clusters.append({
                    "inicio": cluster_atual[0]["timestamp"],
                    "fim": cluster_atual[-1]["timestamp"],
                    "quantidade": len(cluster_atual),
                    "palavras": [f["word"] for f in cluster_atual],
                    "duracao": round(
                        cluster_atual[-1]["timestamp"] - cluster_atual[0]["timestamp"], 1
                    ),
                })
            cluster_atual = [fillers_found[i]]

    # Checar ultimo cluster
    if len(cluster_atual) >= 3:
        clusters.append({
            "inicio": cluster_atual[0]["timestamp"],
            "fim": cluster_atual[-1]["timestamp"],
            "quantidade": len(cluster_atual),
            "palavras": [f["word"] for f in cluster_atual],
            "duracao": round(
                cluster_atual[-1]["timestamp"] - cluster_atual[0]["timestamp"], 1
            ),
        })

    return clusters


def detect_fillers(transcription: dict) -> dict:
    """Detecta vicios de linguagem com classificacao por gravidade e clusters."""
    words = transcription.get("words", [])
    audio_duration = 0.0

    if words:
        audio_duration = words[-1].get("end", 0.0) - words[0].get("start", 0.0)

    fillers_found = []
    filler_counts: dict[str, int] = {}
    contagem_por_categoria = {"hesitacao": 0, "muleta_retorica": 0, "muleta_conexao": 0}

    for i, word_info in enumerate(words):
        word = word_info["word"]
        if ALL_FILLER_REGEX.search(word):
            categoria = _classificar_filler(word)
            contagem_por_categoria[categoria] += 1

            context_before = " ".join(w["word"] for w in words[max(0, i - 3) : i])
            context_after = " ".join(
                w["word"] for w in words[i + 1 : min(len(words), i + 4)]
            )

            filler_entry = {
                "word": word.lower().strip(),
                "timestamp": word_info.get("start", 0.0),
                "context": f"...{context_before} [{word}] {context_after}...",
                "categoria": categoria,
            }
            fillers_found.append(filler_entry)

            normalized = word.lower().strip()
            filler_counts[normalized] = filler_counts.get(normalized, 0) + 1

    # Metricas por minuto
    duration_minutes = audio_duration / 60 if audio_duration > 0 else 1
    fillers_per_minute = round(len(fillers_found) / duration_minutes, 1)
    hesitacoes_per_minute = round(
        contagem_por_categoria["hesitacao"] / duration_minutes, 1
    )
    muletas_per_minute = round(
        (contagem_por_categoria["muleta_retorica"] + contagem_por_categoria["muleta_conexao"])
        / duration_minutes,
        1,
    )

    # Top 3 fillers
    top_fillers = sorted(filler_counts.items(), key=lambda x: x[1], reverse=True)[:3]

    # Diversidade lexical
    all_words = [w["word"].lower().strip() for w in words if w["word"].strip()]
    unique_words = set(all_words)
    type_token_ratio = (
        round(len(unique_words) / len(all_words), 3) if all_words else 0.0
    )

    # Clusters de fillers (red flags)
    clusters = _detectar_clusters(fillers_found)

    # =============================================
    # SCORE DE FILLERS (0-100) — FORMULA MELHORADA
    # =============================================
    # Hesitacoes pesam 2x mais que muletas retoricas
    # Clusters sao penalidade extra

    # Score base: fillers ponderados por gravidade
    fillers_ponderados_por_min = (
        hesitacoes_per_minute * 2.0  # Hesitacoes pesam dobro
        + contagem_por_categoria["muleta_conexao"] / duration_minutes * 1.0
        + contagem_por_categoria["muleta_retorica"] / duration_minutes * 0.5
    )

    # Escala: < 3 ponderado/min = 100, > 12 ponderado/min = 0
    if fillers_ponderados_por_min <= 3:
        filler_score = 100
    elif fillers_ponderados_por_min >= 12:
        filler_score = 0
    else:
        filler_score = round(100 - (fillers_ponderados_por_min - 3) * (100 / 9))

    # Penalidade por clusters (cada cluster = -5 pontos)
    penalidade_clusters = len(clusters) * 5
    filler_score = max(0, min(100, filler_score - penalidade_clusters))

    # Bonus diversidade lexical (compensacao parcial se vocabulario e rico)
    if type_token_ratio > 0.6:
        bonus_diversidade = 5
    elif type_token_ratio > 0.5:
        bonus_diversidade = 2
    else:
        bonus_diversidade = 0

    filler_score = min(100, filler_score + bonus_diversidade)

    logger.info(
        "filler_detection_complete",
        total_fillers=len(fillers_found),
        fillers_per_minute=fillers_per_minute,
        hesitacoes_per_minute=hesitacoes_per_minute,
        clusters=len(clusters),
        top_fillers=top_fillers,
    )

    return {
        "score": filler_score,
        "fillers_per_minute": fillers_per_minute,
        "total_fillers": len(fillers_found),
        "top_fillers": [{"word": w, "count": c} for w, c in top_fillers],
        "type_token_ratio": type_token_ratio,
        "fillers": fillers_found,
        # Metricas novas
        "por_categoria": {
            "hesitacao": contagem_por_categoria["hesitacao"],
            "muleta_retorica": contagem_por_categoria["muleta_retorica"],
            "muleta_conexao": contagem_por_categoria["muleta_conexao"],
        },
        "hesitacoes_per_minute": hesitacoes_per_minute,
        "muletas_per_minute": muletas_per_minute,
        "clusters": clusters,
        "total_clusters": len(clusters),
    }
