import re

import structlog

from contracts import WorkerResult
from workers._truth_contract_helpers import wrap_worker_result

logger = structlog.get_logger()

# Muletas retoticas (fim de frase, habito social — menos graves)
MULETAS_RETORICAS = [
    r"\bné\b",
    r"\bne\b",  # Whisper pode transcrever sem acento
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
    "|".join(p for patterns in CATEGORIAS.values() for p in patterns),
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
                clusters.append(
                    {
                        "inicio": cluster_atual[0]["timestamp"],
                        "fim": cluster_atual[-1]["timestamp"],
                        "quantidade": len(cluster_atual),
                        "palavras": [f["word"] for f in cluster_atual],
                        "duracao": round(
                            cluster_atual[-1]["timestamp"] - cluster_atual[0]["timestamp"], 1
                        ),
                    }
                )
            cluster_atual = [fillers_found[i]]

    # Checar ultimo cluster
    if len(cluster_atual) >= 3:
        clusters.append(
            {
                "inicio": cluster_atual[0]["timestamp"],
                "fim": cluster_atual[-1]["timestamp"],
                "quantidade": len(cluster_atual),
                "palavras": [f["word"] for f in cluster_atual],
                "duracao": round(cluster_atual[-1]["timestamp"] - cluster_atual[0]["timestamp"], 1),
            }
        )

    return clusters


def _has_hesitation_pause(words: list, filler: dict, all_fillers: list) -> bool:
    """Verifica se ha pausa de hesitacao (>1s) antes do filler."""
    ts = filler["timestamp"]
    for w in words:
        if abs(w.get("start", 0) - ts) < 0.1:
            idx = words.index(w)
            if idx > 0:
                prev_end = words[idx - 1].get("end", 0)
                gap = w.get("start", 0) - prev_end
                return gap > 1.0
    return False


def _compute_filler_metrics(transcription: dict) -> dict:
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
            context_after = " ".join(w["word"] for w in words[i + 1 : min(len(words), i + 4)])

            filler_entry = {
                "word": word.lower().strip(),
                "timestamp": word_info.get("start", 0.0),
                "context": f"...{context_before} [{word}] {context_after}...",
                "categoria": categoria,
            }
            fillers_found.append(filler_entry)

            # Story 7.1 fix QA — normalizar agressivamente para agrupar variantes:
            # 'aí' / 'ai' / 'então,' / 'então' / 'né?' / 'né' viram chaves unicas.
            normalized = word.lower().strip().rstrip(".,!?;:").strip()
            # Remove acentos para agrupar 'aí' com 'ai', 'né' com 'ne'
            import unicodedata

            normalized = "".join(
                c
                for c in unicodedata.normalize("NFD", normalized)
                if unicodedata.category(c) != "Mn"
            )
            filler_counts[normalized] = filler_counts.get(normalized, 0) + 1

    # Classificacao contextual (nervoso vs estilistico)
    clusters = _detectar_clusters(fillers_found)
    cluster_timestamps = set()
    for cl in clusters:
        for t in range(int(cl["inicio"]), int(cl["fim"]) + 1):
            cluster_timestamps.add(t)

    for filler in fillers_found:
        ts = filler["timestamp"]
        words_before_count = len(filler["context"].split("[")[0].strip().split())

        # Dentro de cluster → nervoso (peso 2x)
        if int(ts) in cluster_timestamps:
            filler["contexto_uso"] = "nervoso"
            filler["peso_contextual"] = 2.0
        # Apos pausa de hesitacao (gap > 1s com palavra anterior)
        elif _has_hesitation_pause(words, filler, fillers_found):
            filler["contexto_uso"] = "nervoso"
            filler["peso_contextual"] = 1.5
        # Fim de frase completa (5+ palavras antes) → estilistico
        elif words_before_count >= 5:
            filler["contexto_uso"] = "estilistico"
            filler["peso_contextual"] = 0.2
        else:
            filler["contexto_uso"] = "padrao"
            filler["peso_contextual"] = 1.0

    # Metricas por minuto
    duration_minutes = audio_duration / 60 if audio_duration > 0 else 1
    fillers_per_minute = round(len(fillers_found) / duration_minutes, 1)
    hesitacoes_per_minute = round(contagem_por_categoria["hesitacao"] / duration_minutes, 1)
    muletas_per_minute = round(
        (contagem_por_categoria["muleta_retorica"] + contagem_por_categoria["muleta_conexao"])
        / duration_minutes,
        1,
    )
    # Story 7.1 AC-2: consolidacao "Vicios de Linguagem por Minuto"
    # = fillers_per_minute (todos os tipos: hesitacoes + muletas).
    # Mantemos campos brutos para rastreabilidade interna.
    vicios_por_minuto = fillers_per_minute

    # Story 7.1 fix QA — antes era top 3, agora top 10 para o usuario ver TODOS os vicios
    top_fillers = sorted(filler_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    # Diversidade lexical
    all_words = [w["word"].lower().strip() for w in words if w["word"].strip()]
    unique_words = set(all_words)
    type_token_ratio = round(len(unique_words) / len(all_words), 3) if all_words else 0.0

    # Clusters de fillers (red flags)
    clusters = _detectar_clusters(fillers_found)

    # =============================================
    # SCORE DE FILLERS (0-100) — FORMULA MELHORADA
    # =============================================
    # Hesitacoes pesam 2x mais que muletas retoricas
    # Clusters sao penalidade extra

    # Score base: fillers ponderados por gravidade E contexto de uso
    peso_total_contextual = sum(f.get("peso_contextual", 1.0) for f in fillers_found)
    fillers_ponderados_por_min = (
        peso_total_contextual / duration_minutes if duration_minutes > 0 else 0
    )

    # Escala: < 3 ponderado/min = 100, > 12 ponderado/min = 0
    if fillers_ponderados_por_min <= 3:
        filler_score = 100
    elif fillers_ponderados_por_min >= 12:
        filler_score = 0
    else:
        filler_score = round(100 - (fillers_ponderados_por_min - 3) * (100 / 9))

    # Penalidade por clusters (cada cluster = -10 pontos)
    # Cluster = 3+ fillers em <10s = travamento cognitivo agudo, pior que
    # fillers distribuidos. Calibrado 2026-04-18 (Rodenburg audit).
    penalidade_clusters = len(clusters) * 10
    filler_score = max(0, min(100, filler_score - penalidade_clusters))

    # 2026-05-06: penalidade por REPETICAO da mesma muleta. Vinh: a
    # audiencia percebe muito mais quando voce repete a MESMA palavra
    # (ex: 5x "entao") do que quando varia (ex: 1 "ne", 1 "tipo", 1
    # "entao", etc). 60%+ concentracao = padrao notavel.
    total_count = len(fillers_found)
    if total_count >= 4:
        # Top filler com >= 60% do total
        from collections import Counter
        word_counts = Counter(f.get("word", "").lower().rstrip(",.") for f in fillers_found)
        top_word, top_n = word_counts.most_common(1)[0] if word_counts else ("", 0)
        if top_n / total_count >= 0.6:
            penalidade_repeticao = 10
            filler_score = max(0, min(100, filler_score - penalidade_repeticao))
            logger.info(
                "filler_repetition_penalty",
                top_word=top_word,
                top_count=top_n,
                total=total_count,
                penalty=penalidade_repeticao,
            )

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
        # Story 7.1 AC-2: campo consolidado para UI ("Vicios de Linguagem por Minuto")
        "vicios_por_minuto": vicios_por_minuto,
        "clusters": clusters,
        "total_clusters": len(clusters),
    }


# Story 8.2 — Truth Contract


def detect_fillers_legacy(transcription: dict) -> dict:
    """Legacy path (TRUTH_CONTRACT_ENABLED=false)."""
    return _compute_filler_metrics(transcription)


def detect_fillers(transcription: dict) -> dict:
    """Legacy alias kept for backwards compat with app.py callers."""
    return _compute_filler_metrics(transcription)


def analyze_fillers(transcription: dict) -> "WorkerResult":
    """Truth Contract path (TRUTH_CONTRACT_ENABLED=true)."""
    return wrap_worker_result("fillers", _compute_filler_metrics, transcription)
