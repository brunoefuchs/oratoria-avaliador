"""Variety Analyzer — O Meta-Analyzer de Variacao Temporal.

Principio central: "Sempre que qualquer coisa se torna padrao, ela se torna nao-funcional."

Este analyzer mede a VARIACAO ao longo do tempo de TODAS as dimensoes.
Nao importa se o WPM medio e 150 (perfeito) — se e 150 do inicio ao fim,
e monotonia. O cerebro desliga quando consegue prever o que vem a seguir.

Dimensoes avaliadas:
- Variacao de velocidade (WPM entre janelas)
- Variacao de volume (dB entre janelas)
- Variacao de pitch (Hz entre janelas)
- Score de monotonia geral

Nota (2026-04-29): variacao gestual saiu desta dimensao — pertence a
"Gestos" (gesture_analyzer). Ver historico para justificativa.

Story 8.1 (Truth Contract — Fundacao):
- analyze_variety() retorna WorkerResult validado por Pydantic (path NOVO)
- analyze_variety_legacy() retorna dict (path LEGADO, usado quando feature
  flag TRUTH_CONTRACT_ENABLED=false)
- Detecta falha upstream (voice/gesture failed) e retorna WorkerFailure
  em vez de propagar score=0 fake
- Captura excecoes e retorna WorkerFailure(crashed) em vez de quebrar pipeline
"""

import structlog

from contracts import WorkerFailure, WorkerResult, WorkerSuccess

logger = structlog.get_logger()

# Ranges ideais de coeficiente de variacao (CV)
# CV = desvio padrao / media — quanto mais alto, mais variacao
# Muito baixo = monotono, muito alto = caotico
CV_RANGES = {
    # B12-real calibration: thresholds rebaixados pra AGC de smartphone
    # (AGC comprime dynamic range em 6-10dB → CV cai ~30-40% vs mic studio).
    # 2026-05-06: volume.min_ideal 0.015 → 0.010 apos validacao em 7 videos
    # bench. 4/5 mentores tinham cv_volume 0.012-0.013 (voz boa/otima) sendo
    # classificados como "pouca_variacao" (score ~44). Threshold 0.010 captura
    # disciplina vocal de mentor sem perder discriminacao vs ALUNO MONO (0.006).
    "velocidade": {"min_ideal": 0.05, "max_ideal": 0.30, "label": "Velocidade de Fala"},
    "volume": {"min_ideal": 0.010, "max_ideal": 0.25, "label": "Volume"},
    "pitch": {"min_ideal": 0.03, "max_ideal": 0.20, "label": "Entonacao"},
}


def _score_variacao(cv: float, dimensao: str) -> dict:
    """Calcula score de variacao para uma dimensao baseado no CV.

    Retorna score (0-100) e diagnostico textual.
    """
    config = CV_RANGES.get(dimensao, {"min_ideal": 0.05, "max_ideal": 0.30})
    min_ideal = config["min_ideal"]
    max_ideal = config["max_ideal"]

    if cv < min_ideal * 0.3:
        score = 10
        diagnostico = "travado"  # Quase zero variacao
    elif cv < min_ideal:
        # Abaixo do ideal — subindo linearmente
        score = round(10 + (cv / min_ideal) * 40)
        diagnostico = "pouca_variacao"
    elif cv <= max_ideal:
        # Range ideal — score alto
        posicao = (cv - min_ideal) / (max_ideal - min_ideal)
        # Pico no meio do range ideal
        if posicao <= 0.5:
            score = round(80 + posicao * 40)
        else:
            score = round(100 - (posicao - 0.5) * 20)
        diagnostico = "ideal"
    elif cv <= max_ideal * 1.5:
        # Acima do ideal — descendo
        excesso = (cv - max_ideal) / (max_ideal * 0.5)
        score = round(80 - excesso * 40)
        diagnostico = "excessiva"
    else:
        score = max(10, round(40 - (cv - max_ideal * 1.5) * 100))
        diagnostico = "caotica"

    return {
        "score": max(0, min(100, score)),
        "cv": round(cv, 4),
        "diagnostico": diagnostico,
        "range_ideal": f"{min_ideal:.2f}-{max_ideal:.2f}",
    }


def _detectar_trechos_monotonos(
    valores_janela: list,
    limiar_cv: float = 0.03,
    janela_segundos: float = 15.0,
) -> list:
    """Detecta trechos onde o orador ficou monotono (3+ janelas consecutivas sem variacao)."""
    if len(valores_janela) < 3:
        return []

    trechos = []
    inicio_monotono = None

    for i in range(1, len(valores_janela)):
        variacao = abs(valores_janela[i] - valores_janela[i - 1]) / (
            abs(valores_janela[i - 1]) + 1e-8
        )

        if variacao < limiar_cv:
            if inicio_monotono is None:
                inicio_monotono = i - 1
        else:
            if inicio_monotono is not None and (i - inicio_monotono) >= 3:
                trechos.append(
                    {
                        "inicio_segundos": inicio_monotono * janela_segundos,
                        "fim_segundos": i * janela_segundos,
                        "duracao_segundos": (i - inicio_monotono) * janela_segundos,
                        "num_janelas": i - inicio_monotono,
                    }
                )
            inicio_monotono = None

    # Checar se terminou monotono
    if inicio_monotono is not None and (len(valores_janela) - inicio_monotono) >= 3:
        trechos.append(
            {
                "inicio_segundos": inicio_monotono * janela_segundos,
                "fim_segundos": len(valores_janela) * janela_segundos,
                "duracao_segundos": (len(valores_janela) - inicio_monotono) * janela_segundos,
                "num_janelas": len(valores_janela) - inicio_monotono,
            }
        )
    return trechos


def _detectar_trechos_multidim(
    wpm_janelas: list,
    volume_janelas: list,
    pitch_janelas: list,
    janela_segundos: float = 15.0,
    min_dim_planas: int = 2,
    limiar_velocidade: float = 0.05,
    limiar_volume: float = 0.02,
    limiar_pitch: float = 0.03,
) -> list:
    """Detector multi-dimensional de monotonia perceptual.

    Diferenca vs _detectar_trechos_monotonos: aqui exigimos que MULTIPLAS
    dimensoes (volume + pitch + velocidade) estejam planas SIMULTANEAMENTE
    na mesma janela pra contar como monotono. Mentor com volume controlado
    mas pitch ativo + velocidade variada NAO eh monotono perceptual — sistema
    antigo punia esse caso (cv_volume baixo = "100% mono falso").

    min_dim_planas=2 (default): "AND-2" — 2 das 3 dim planas no mesmo trecho.
    min_dim_planas=3: "AND-3 estrito" — todas 3 planas (pega so mono extrema).

    Retorna lista de trechos com inicio/fim/duracao/dim_count/dim_planas.
    """
    n = min(len(wpm_janelas), len(volume_janelas), len(pitch_janelas))
    if n < 4:
        return []

    # Pra cada janela i (a partir de i=1), conta quantas dim sao planas
    # comparado com janela i-1.
    flags_por_janela = []
    for i in range(1, n):
        var_vel = abs(wpm_janelas[i] - wpm_janelas[i - 1]) / (
            abs(wpm_janelas[i - 1]) + 1e-8
        )
        var_vol = abs(volume_janelas[i] - volume_janelas[i - 1]) / (
            abs(volume_janelas[i - 1]) + 1e-8
        )
        var_pit = abs(pitch_janelas[i] - pitch_janelas[i - 1]) / (
            abs(pitch_janelas[i - 1]) + 1e-8
        )
        dims_planas = []
        if var_vel < limiar_velocidade:
            dims_planas.append("velocidade")
        if var_vol < limiar_volume:
            dims_planas.append("volume")
        if var_pit < limiar_pitch:
            dims_planas.append("pitch")
        flags_por_janela.append(dims_planas)

    # Encontra runs de janelas onde len(dims_planas) >= min_dim_planas
    trechos = []
    inicio = None
    dims_acumuladas = set()
    for i, dims in enumerate(flags_por_janela):
        if len(dims) >= min_dim_planas:
            if inicio is None:
                inicio = i
                dims_acumuladas = set(dims)
            else:
                dims_acumuladas |= set(dims)
        else:
            if inicio is not None and (i - inicio) >= 3:
                trechos.append(
                    {
                        "inicio_segundos": inicio * janela_segundos,
                        "fim_segundos": (i + 1) * janela_segundos,
                        "duracao_segundos": (i - inicio + 1) * janela_segundos,
                        "num_janelas": i - inicio + 1,
                        "dim_planas": sorted(dims_acumuladas),
                    }
                )
            inicio = None
            dims_acumuladas = set()

    # trecho terminando no fim
    if inicio is not None and (len(flags_por_janela) - inicio) >= 3:
        trechos.append(
            {
                "inicio_segundos": inicio * janela_segundos,
                "fim_segundos": (len(flags_por_janela) + 1) * janela_segundos,
                "duracao_segundos": (len(flags_por_janela) - inicio + 1)
                * janela_segundos,
                "num_janelas": len(flags_por_janela) - inicio + 1,
                "dim_planas": sorted(dims_acumuladas),
            }
        )
    return trechos


def _compute_variety_metrics(voice_result: dict, gesture_result: dict) -> dict:
    """Core compute — extrai metricas de variacao. Compartilhado por
    analyze_variety() (Truth Contract) e analyze_variety_legacy() (legacy).

    Args:
        voice_result: Resultado do voice_analyzer (com janelas temporais)
        gesture_result: Resultado do gesture_analyzer

    Returns:
        Dict com `score`, `confidence`, `metrics` (formato legacy compativel).
    """
    logger.info("variety_analysis_start")

    # Truth Contract: voice_result/gesture_result podem ser WorkerSuccess (pydantic)
    # ou dict (legacy). Normaliza pra extrair metrics dict em ambos casos.
    def _extract_metrics(r):
        if hasattr(r, "metrics"):
            return r.metrics or {}
        if isinstance(r, dict):
            return r.get("metrics", r) or {}
        return {}

    voice = _extract_metrics(voice_result)
    wpm_janelas = voice.get("wpm_por_janela", [])
    pitch_janelas = voice.get("pitch_por_janela", [])
    volume_janelas = voice.get("volume_por_janela", [])
    cv_velocidade = voice.get("cv_velocidade", 0.0)
    cv_pitch = voice.get("cv_pitch", 0.0)
    cv_volume = voice.get("cv_volume", 0.0)
    audio_quality_low = voice.get("audio_quality_low", False)
    snr_estimated_db = voice.get("snr_estimated_db", None)
    babble_suspected = voice.get("babble_suspected", False)

    # =============================================
    # SCORES POR DIMENSAO (puramente vocais)
    # Gesto saiu daqui (2026-04-29): "Variedade Vocal" mistura conceitual +
    # double counting com a dimensao Gestos propria. Variacao gestual
    # permanece dentro da dimensao Gestos via gesture_analyzer.
    # =============================================
    variacao_velocidade = _score_variacao(cv_velocidade, "velocidade")
    variacao_volume = _score_variacao(cv_volume, "volume")
    variacao_pitch = _score_variacao(cv_pitch, "pitch")

    # Detectar trechos monotonos — usa janela real do voice_analyzer
    # 2026-04-29: skip detecao quando CV global > 1.5x piso ideal.
    # Speaker que varia globalmente tem direito a platos locais (estabilidade
    # tematica intencional). Sem isso, mentor TEDx era marcado tao monotono
    # quanto aluno iniciante por causa de 3 janelas estaveis no meio.
    janela_segundos = voice.get("janela_size_seconds") or 15.0
    # 2026-05-06: gate por qualidade de audio. SNR baixo distorce cv_volume e
    # cv_pitch (caso Gui 0f776d94: SNR 9.3dB → 100% monotono falso). Quando
    # audio_quality_low, pular deteccao de monotonia pra evitar falso positivo.
    #
    # 2026-05-06: SKIP_FACTOR ajustado de 1.5 → 3.0. Antes 1.5x piso era muito
    # permissivo (5 de 7 videos zeravam monotono). 3.0x preserva mentor
    # calibrado (cv >> piso = nao detecta) mas roda deteccao em medianos.
    # Penalidades tambem suavizadas (local 0.5→0.3 max 20, global 0.4→0.3
    # max 15) pra evitar tombo draconiano de 26pts num video de score 92.
    # 2026-05-06 v4: detector MULTI-DIMENSIONAL substitui detector per-dim.
    # Razao: cv_volume baixo isolado NAO indica monotonia perceptual. Mentor
    # com controle de volume + pitch ativo + velocidade variada nao soa
    # monotono. Sistema antigo punia esse caso (GUI WENDEL/PRIME: 100% mono FP).
    # Multi-dim so marca trecho quando >= 2 dimensoes estao planas SIMULTANEAS
    # na mesma janela — captura monotonia perceptual real (ALUNO MONO) sem FP.
    if audio_quality_low or babble_suspected:
        trechos_multidim = []
    else:
        trechos_multidim = _detectar_trechos_multidim(
            wpm_janelas,
            volume_janelas,
            pitch_janelas,
            janela_segundos=janela_segundos,
            min_dim_planas=2,
        )

    # Por compatibilidade com codigo downstream (penalidade local per-dim,
    # UI mostra trechos_monotonos.{volume,entonacao,velocidade}), decompoe
    # os trechos multidim por dimensao — cada trecho aparece nas dim que
    # estavam planas naquele intervalo.
    def _split_dim(trechos_md: list, dim: str) -> list:
        return [
            {
                k: v
                for k, v in t.items()
                if k != "dim_planas"
            }
            for t in trechos_md
            if dim in t.get("dim_planas", [])
        ]

    trechos_monotonos_velocidade = _split_dim(trechos_multidim, "velocidade")
    trechos_monotonos_volume = _split_dim(trechos_multidim, "volume")
    trechos_monotonos_pitch = _split_dim(trechos_multidim, "pitch")

    todos_trechos = (
        trechos_monotonos_velocidade + trechos_monotonos_volume + trechos_monotonos_pitch
    )

    # Tempo total monotono (segundos) — UNIAO de intervalos, nao soma.
    # Soma double-contava overlap entre dimensoes (3x mesmo instante = 3x tempo)
    # gerando pct > 100% capped artificialmente.
    intervalos = sorted(
        [(t["inicio_segundos"], t["fim_segundos"]) for t in todos_trechos]
    )
    merged: list[tuple[float, float]] = []
    for start, end in intervalos:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    tempo_monotono_total = sum(end - start for start, end in merged)
    duracao_audio = voice.get("audio_duration_seconds", 1)
    pct_tempo_monotono = round(min(100, tempo_monotono_total / max(1, duracao_audio) * 100), 1)

    # =============================================
    # PENALIDADE LOCAL POR DIMENSAO (2026-04-29)
    # =============================================
    # Sub-score baseava-se em CV global, ignorando trechos monotonos locais.
    # Cliente via "ideal" + 54% monotono = contradicao. Agora cada dimensao
    # com trecho monotono tem score reduzido proporcional ao tempo plano.
    # Substitui penalidade global de pct_tempo_monotono (que penalizava o
    # variety_score sem mostrar onde o problema estava).

    def _aplicar_penalidade_local(resultado: dict, trechos: list, dur: float) -> dict:
        if not trechos or dur <= 0:
            return resultado
        tempo_plano = sum(t["duracao_segundos"] for t in trechos)
        pct_dim = (tempo_plano / dur) * 100
        # 2026-05-06: penalidade suavizada (0.5 → 0.3, max 30 → 20).
        penalidade = min(20, pct_dim * 0.3)
        novo_score = max(0, round(resultado["score"] - penalidade))
        return {
            **resultado,
            "score": novo_score,
            "diagnostico": "atencao" if penalidade > 5 else resultado["diagnostico"],
            "tempo_plano_segundos": round(tempo_plano, 1),
            "pct_dimensao_plana": round(pct_dim, 1),
        }

    variacao_velocidade = _aplicar_penalidade_local(
        variacao_velocidade, trechos_monotonos_velocidade, duracao_audio
    )
    variacao_volume = _aplicar_penalidade_local(
        variacao_volume, trechos_monotonos_volume, duracao_audio
    )
    variacao_pitch = _aplicar_penalidade_local(
        variacao_pitch, trechos_monotonos_pitch, duracao_audio
    )

    # =============================================
    # SCORE GERAL DE VARIEDADE (0-100)
    # =============================================
    # "Sua voz e um instrumento com 88 teclas. A maioria das pessoas usa apenas 20."
    # Esse score mede quantas teclas voce esta usando.
    # Sem penalidade global de pct_tempo_monotono — substituida por penalidade
    # local em cada dimensao (vide bloco acima).

    variety_score = round(
        variacao_velocidade["score"] * 0.35  # Velocidade e o mais perceptivel
        + variacao_volume["score"] * 0.32  # Volume cria peaks and troughs
        + variacao_pitch["score"] * 0.33  # Entonacao da vida a fala
    )

    # Penalidade GLOBAL pct_tempo_monotono mantida — penalidade local mostra
    # onde, global mostra impacto no overall. Sozinha local nao puxa overall
    # forte o bastante por causa dos pesos 0.32-0.35 amortizando o tombo.
    # 2026-05-06: penalidade global suavizada (0.4 → 0.3, max 20 → 15).
    if pct_tempo_monotono > 30:
        penalidade_monotonia = min(15, (pct_tempo_monotono - 30) * 0.3)
        variety_score = max(0, round(variety_score - penalidade_monotonia))

    variety_score = max(0, min(100, variety_score))

    # Diagnostico geral
    if variety_score >= 80:
        diagnostico_geral = "excelente"
    elif variety_score >= 60:
        diagnostico_geral = "bom"
    elif variety_score >= 40:
        diagnostico_geral = "moderado"
    elif variety_score >= 20:
        diagnostico_geral = "monotono"
    else:
        diagnostico_geral = "muito_monotono"

    # Dimensoes com defaults detectados (travadas)
    defaults_detectados = []
    for nome, resultado in [
        ("velocidade", variacao_velocidade),
        ("volume", variacao_volume),
        ("entonacao", variacao_pitch),
    ]:
        if resultado["diagnostico"] in ("travado", "pouca_variacao"):
            defaults_detectados.append(nome)

    logger.info(
        "variety_analysis_complete",
        score=variety_score,
        diagnostico=diagnostico_geral,
        defaults=defaults_detectados,
        pct_monotono=pct_tempo_monotono,
    )

    return {
        "score": variety_score,
        "confidence": "high",
        "metrics": {
            "diagnostico_geral": diagnostico_geral,
            "defaults_detectados": defaults_detectados,
            "audio_quality_low": audio_quality_low,
            "snr_estimated_db": snr_estimated_db,
            "babble_suspected": babble_suspected,
            "pct_tempo_monotono": pct_tempo_monotono,
            "dimensoes": {
                "velocidade": variacao_velocidade,
                "volume": variacao_volume,
                "entonacao": variacao_pitch,
            },
            "trechos_monotonos": {
                "velocidade": trechos_monotonos_velocidade,
                "volume": trechos_monotonos_volume,
                "entonacao": trechos_monotonos_pitch,
                "total": len(todos_trechos),
                "tempo_total_segundos": round(tempo_monotono_total, 1),
            },
            "sub_scores": {
                "variacao_velocidade": variacao_velocidade["score"],
                "variacao_volume": variacao_volume["score"],
                "variacao_entonacao": variacao_pitch["score"],
            },
        },
    }


# ============================================================================
# Story 8.1 — Truth Contract: entry points publicos
# ============================================================================


def analyze_variety_legacy(voice_result: dict, gesture_result: dict) -> dict:
    """Path LEGADO — preserva comportamento pre-Truth-Contract.

    Usado quando feature flag TRUTH_CONTRACT_ENABLED=false. Nao detecta
    falha upstream nem captura excecoes — replica o pattern silencioso
    documentado no Epic 8.0 (audit pedro-valerio).

    Para codigo NOVO use analyze_variety() que retorna WorkerResult.
    """
    return _compute_variety_metrics(voice_result, gesture_result)


def _upstream_failed(result) -> bool:
    """Detecta falha upstream em todos schemas (legacy, novo, Truth Contract).

    Schema legacy: confidence == 'failed'
    Schema novo (facial/tonality/opening): disponivel == False
    Schema Truth Contract: WorkerFailure OR dict com dimension_status != 'ok'
    Schema Truth Contract success: WorkerSuccess (pydantic) → checa dimension_status='ok'
    """
    if result is None:
        return True

    # Pydantic WorkerSuccess/WorkerFailure (Truth Contract — Epic 8)
    if hasattr(result, "dimension_status"):
        return result.dimension_status != "ok"

    # Dict-like (legacy + schema novo)
    if not isinstance(result, dict):
        return True
    if not result:  # empty dict = sem dados upstream
        return True
    if result.get("confidence") == "failed":
        return True
    if result.get("disponivel") is False:
        return True
    status = result.get("dimension_status")
    if status and status != "ok":
        return True
    return False


def analyze_variety(voice_result: dict, gesture_result: dict) -> WorkerResult:
    """Truth Contract path — retorna WorkerResult validado por Pydantic.

    Failure conditions:
    - voice_result ou gesture_result indica falha (qualquer schema) → SKIPPED
    - audio_duration_seconds ausente ou <= 0 → INSUFFICIENT_DATA
    - excecao nao tratada durante compute → CRASHED

    Nunca retorna score=0 fake. Score eh None em qualquer Failure.
    """
    try:
        if _upstream_failed(voice_result):
            return WorkerFailure(
                dimension="variety",
                dimension_status="skipped",
                failure_reason=(
                    "upstream_dependency_failed: voice_analyzer nao produziu dados validos"
                ),
            )
        if _upstream_failed(gesture_result):
            return WorkerFailure(
                dimension="variety",
                dimension_status="skipped",
                failure_reason=(
                    "upstream_dependency_failed: gesture_analyzer nao produziu dados validos"
                ),
            )

        # Truth Contract: WorkerSuccess tem .metrics attr; legacy dict tem "metrics" key
        if hasattr(voice_result, "metrics"):
            voice = voice_result.metrics
        elif isinstance(voice_result, dict):
            voice = voice_result.get("metrics", voice_result)
        else:
            voice = {}
        audio_duration = voice.get("audio_duration_seconds") if isinstance(voice, dict) else None
        if not audio_duration or audio_duration <= 0:
            return WorkerFailure(
                dimension="variety",
                dimension_status="insufficient_data",
                failure_reason=(
                    "audio_duration_seconds ausente ou zero — analise temporal impossivel"
                ),
            )

        result_dict = _compute_variety_metrics(voice_result, gesture_result)

        return WorkerSuccess(
            dimension="variety",
            score=result_dict["score"],
            metrics=result_dict["metrics"],
            confidence=0.95,
        )

    except Exception as e:
        logger.error(
            "variety_analysis_crashed",
            error_type=type(e).__name__,
            error=str(e),
            exc_info=True,
        )
        return WorkerFailure(
            dimension="variety",
            dimension_status="crashed",
            failure_reason=f"{type(e).__name__}: {str(e)}",
        )
