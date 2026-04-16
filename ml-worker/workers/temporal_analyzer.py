"""Analise temporal — divide a performance em 3 tercos (abertura, meio, fechamento).

Usa dados temporais ja existentes nos workers para estimar scores por terco.
"""

import structlog

logger = structlog.get_logger()

TERCO_LABELS = ["abertura", "meio", "fechamento"]


def _split_windows_by_terco(windows: list, duration: float, window_size: float = 15.0) -> dict:
    """Divide janelas temporais em 3 tercos pelo CENTRO da janela.

    Usar o centro (nao o inicio) evita que a ultima janela fique sem alocacao
    quando `duration` nao e multiplo exato de `window_size`.
    Tambem ignora valores zerados (janelas sem sinal de voz).
    """
    terco_dur = duration / 3
    tercos = {"abertura": [], "meio": [], "fechamento": []}

    for i, val in enumerate(windows):
        if val == 0:
            continue
        t = (i + 0.5) * window_size
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


def _compute_temporal_metrics(
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

    # Tamanho real da janela usada pelo voice_analyzer (pode nao ser 15s fixo)
    pitch_windows = voice_metrics.get("pitch_por_janela", [])
    volume_windows = voice_metrics.get("volume_por_janela", [])
    num_janelas = voice_metrics.get("num_janelas") or max(1, len(pitch_windows))
    janela_size = voice_metrics.get("janela_size_seconds") or (
        duration_seconds / num_janelas if num_janelas > 0 else 15.0
    )

    pitch_tercos = _split_windows_by_terco(pitch_windows, duration_seconds, janela_size)
    volume_tercos = _split_windows_by_terco(volume_windows, duration_seconds, janela_size)

    for i, label in enumerate(TERCO_LABELS):
        t_start = i * terco_dur
        t_end = (i + 1) * terco_dur

        terco_info: dict = {"label": label}

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


# Story 8.3 — Truth Contract
from contracts import WorkerFailure, WorkerResult, WorkerSuccess  # noqa: E402


def analyze_temporal_legacy(
    voice_result: dict,
    variety_result: dict,
    filler_result: dict,
    duration_seconds: float,
) -> dict:
    """Legacy path (TRUTH_CONTRACT_ENABLED=false)."""
    return _compute_temporal_metrics(voice_result, variety_result, filler_result, duration_seconds)


def analyze_temporal(
    voice_result: dict,
    variety_result: dict,
    filler_result: dict,
    duration_seconds: float,
) -> "WorkerResult":
    """Truth Contract path — retorna WorkerResult (Pydantic).

    Temporal e um worker de metadados — nao tem score proprio.
    Usa score medio dos tercos como score sintetico.
    - disponivel=True → WorkerSuccess com score medio
    - disponivel=False (video curto) → WorkerFailure(skipped)
    - Exception → WorkerFailure(crashed)
    """
    try:
        result = _compute_temporal_metrics(
            voice_result, variety_result, filler_result, duration_seconds
        )
        if not result.get("disponivel", True):
            return WorkerFailure(
                dimension="temporal",
                dimension_status="skipped",
                failure_reason=result.get("motivo", "analise temporal indisponivel"),
                metrics=result,
            )
        # Score sintetico: media dos tercos
        por_terco = result.get("por_terco", {})
        terco_scores = [v.get("score", 0) for v in por_terco.values() if isinstance(v, dict)]
        score = round(sum(terco_scores) / max(1, len(terco_scores))) if terco_scores else 50
        metrics = {k: v for k, v in result.items() if k not in ("disponivel",)}
        return WorkerSuccess(
            dimension="temporal",
            score=max(0, min(100, score)),
            metrics=metrics,
            confidence=1.0,
        )
    except Exception as e:
        logger.error("temporal_crashed", error_type=type(e).__name__, error=str(e), exc_info=True)
        return WorkerFailure(
            dimension="temporal",
            dimension_status="crashed",
            failure_reason=f"{type(e).__name__}: {str(e)}",
        )
