"""Analise temporal — divide a performance em 3 tercos (abertura, meio, fechamento).

Usa dados temporais ja existentes nos workers para estimar scores por terco.
"""

import structlog

logger = structlog.get_logger()

TERCO_LABELS = ["abertura", "meio", "fechamento"]


def _split_windows_by_terco(windows: list, duration: float) -> dict:
    """Divide janelas temporais em 3 tercos baseado no timestamp."""
    terco_dur = duration / 3
    tercos = {"abertura": [], "meio": [], "fechamento": []}

    for i, val in enumerate(windows):
        # Estima timestamp pelo indice (janelas de ~15s)
        t = i * 15.0
        if t < terco_dur:
            tercos["abertura"].append(val)
        elif t < terco_dur * 2:
            tercos["meio"].append(val)
        else:
            tercos["fechamento"].append(val)

    return tercos


def _avg(values: list) -> float:
    return round(sum(values) / max(1, len(values)), 1)


def _count_in_range(items, start: float, end: float, key: str = "inicio") -> int:
    """Conta itens cujo timestamp cai dentro de um range.

    Aceita lista de dicts OU dict de listas (flatten automatico).
    """
    if isinstance(items, dict):
        # Flatten dict de listas (ex: {"velocidade": [...], "volume": [...]})
        flat = []
        for v in items.values():
            if isinstance(v, list):
                flat.extend(v)
        items = flat

    if not isinstance(items, list):
        return 0

    count = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        ts = item.get(key, item.get("start", 0))
        if isinstance(ts, (int, float)) and start <= ts < end:
            count += 1
    return count


def analyze_temporal(
    voice_result: dict,
    variety_result: dict,
    filler_result: dict,
    duration_seconds: float,
) -> dict:
    """Gera analise por terco temporal a partir dos dados dos workers."""
    if duration_seconds < 45:
        return {
            "disponivel": False,
            "motivo": "Video muito curto para analise temporal (minimo 45s)",
        }

    terco_dur = duration_seconds / 3
    voice_metrics = voice_result.get("metrics", voice_result)
    variety_metrics = variety_result.get("metrics", variety_result)
    filler_data = filler_result

    por_terco = {}

    for i, label in enumerate(TERCO_LABELS):
        t_start = i * terco_dur
        t_end = (i + 1) * terco_dur

        terco_info: dict = {"label": label}

        # Voz: pitch e volume por janela
        pitch_windows = voice_metrics.get("pitch_por_janela", [])
        volume_windows = voice_metrics.get("volume_por_janela", [])

        pitch_tercos = _split_windows_by_terco(pitch_windows, duration_seconds)
        volume_tercos = _split_windows_by_terco(volume_windows, duration_seconds)

        terco_info["pitch_medio"] = _avg(pitch_tercos.get(label, [0]))
        terco_info["volume_medio"] = _avg(volume_tercos.get(label, [0]))

        # Variedade: trechos monotonos neste terco
        trechos = variety_metrics.get("trechos_monotonos", [])
        monotonos_neste_terco = _count_in_range(trechos, t_start, t_end)
        terco_info["trechos_monotonos"] = monotonos_neste_terco

        # Fillers neste terco
        fillers = filler_data.get("fillers", [])
        fillers_neste_terco = _count_in_range(fillers, t_start, t_end, key="timestamp")
        terco_info["fillers"] = fillers_neste_terco

        # Clusters neste terco
        clusters = filler_data.get("clusters", [])
        clusters_neste_terco = _count_in_range(clusters, t_start, t_end)
        terco_info["clusters"] = clusters_neste_terco

        # Score estimado do terco (heuristica simples)
        # Menos monotonia + menos fillers = melhor
        monotonia_penalty = min(30, monotonos_neste_terco * 10)
        filler_penalty = min(20, fillers_neste_terco * 3)
        terco_score = max(0, min(100, 80 - monotonia_penalty - filler_penalty))
        terco_info["score"] = terco_score

        por_terco[label] = terco_info

    # Detectar padrao temporal
    scores = [por_terco[t]["score"] for t in TERCO_LABELS]
    if scores[0] > scores[1] and scores[0] > scores[2]:
        padrao = "decrescente"
        descricao = "Comeca forte e perde energia ao longo da apresentacao"
    elif scores[2] > scores[0] and scores[2] > scores[1]:
        padrao = "crescente"
        descricao = "Constroi energia ao longo da apresentacao — bom crescendo"
    elif scores[1] < scores[0] and scores[1] < scores[2]:
        padrao = "vale"
        descricao = "Abre e fecha bem, mas perde forca no meio"
    elif scores[1] > scores[0] and scores[1] > scores[2]:
        padrao = "pico"
        descricao = "Maior energia no meio — bom para desenvolvimento de argumento"
    else:
        padrao = "estavel"
        descricao = "Performance consistente ao longo da apresentacao"

    logger.info(
        "temporal_analysis_complete",
        padrao=padrao,
        scores=scores,
    )

    return {
        "disponivel": True,
        "por_terco": por_terco,
        "padrao": padrao,
        "padrao_descricao": descricao,
        "duracao_terco_segundos": round(terco_dur, 1),
    }
