"""Story 7.5 — Tonality Analyzer (5a Vocal Foundation).

Mede textura emocional vocal via VAD (Valence/Arousal/Dominance) usando
parselmouth (Praat) para extrair features acusticas avancadas:
- Jitter (variacao de pitch ciclo-a-ciclo) — sinal de tensao
- Shimmer (variacao de amplitude ciclo-a-ciclo)
- HNR (harmonics-to-noise ratio) — clareza vocal
- Pitch mean/range (ja extraido por voice_analyzer)
- Intensity mean/range

Mapeamento heuristico inspirado em eGeMAPS (Eyben et al. 2016) — modelo academico
de mapeamento features → afeto. Sem ML pesado; thresholds e formulas validados.

Output alimenta `congruence_analyzer` (cruzamento facial-voz-corpo).

Decisao do spike Task 0: parselmouth (zero nova dependencia, sem licenca comercial).
"""

import time

import numpy as np
import parselmouth
import structlog
from parselmouth.praat import call

logger = structlog.get_logger()

WINDOW_SECONDS = 5.0  # Janelas de 5s para distribuicao temporal de texturas
MIN_AUDIO_DURATION = 10.0  # AC-10: audio < 10s = indisponivel

# Thresholds calibrados via literatura (eGeMAPS norms para fala adulta).
# Ajustar via Task 8 se 5 videos de calibracao divergirem.
# B9-real-v2: Mobile recordings tem ruido ambiente que infla jitter tambem
# (literatura diz que jitter eh estavel pro MESMO falante repetindo palavra,
# mas em fala continua + ruido, elevated jitter eh comum).
JITTER_NEUTRAL = 0.020  # era 0.012 — mobile real-world jitter baseline
SHIMMER_NEUTRAL = 0.10  # era 0.06 — AGC mobile infla mais do que pensavamos
HNR_GOOD = 10.0  # era 18.0 — voz mobile masc normal ~8-12 dB
PITCH_MIN_HZ = 75
PITCH_MAX_HZ = 500


def _extract_features_window(sound: parselmouth.Sound, t_start: float, t_end: float) -> dict | None:
    """Extrai features acusticas de uma janela temporal.

    Retorna None se janela muito curta ou sem voiced frames.
    """
    try:
        trecho = sound.extract_part(from_time=t_start, to_time=t_end)
    except Exception:
        return None
    if trecho.get_total_duration() < 0.5:
        return None

    # Pitch
    pitch = trecho.to_pitch(time_step=0.01, pitch_floor=PITCH_MIN_HZ, pitch_ceiling=PITCH_MAX_HZ)
    pitch_values = pitch.selected_array["frequency"]
    voiced = pitch_values[pitch_values > 0]
    if len(voiced) < 5:
        return None
    pitch_mean = float(np.mean(voiced))
    pitch_std = float(np.std(voiced))
    pitch_range = float(np.max(voiced) - np.min(voiced))

    # Intensity (loudness)
    try:
        intensity = trecho.to_intensity()
        int_values = intensity.values[0]
        intensity_mean = float(np.mean(int_values))
        intensity_std = float(np.std(int_values))
    except Exception:
        intensity_mean = 60.0
        intensity_std = 5.0

    # Jitter + Shimmer (precisam de PointProcess)
    try:
        point_process = call(trecho, "To PointProcess (periodic, cc)", PITCH_MIN_HZ, PITCH_MAX_HZ)
        jitter_local = call(point_process, "Get jitter (local)", 0, 0, 0.0001, 0.02, 1.3)
        shimmer_local = call(
            [trecho, point_process], "Get shimmer (local)", 0, 0, 0.0001, 0.02, 1.3, 1.6
        )
        jitter_local = float(jitter_local) if not np.isnan(jitter_local) else JITTER_NEUTRAL
        shimmer_local = float(shimmer_local) if not np.isnan(shimmer_local) else SHIMMER_NEUTRAL
    except Exception:
        jitter_local = JITTER_NEUTRAL
        shimmer_local = SHIMMER_NEUTRAL

    # HNR
    try:
        harmonicity = trecho.to_harmonicity_cc()
        hnr_mean = float(call(harmonicity, "Get mean", 0, 0))
        if np.isnan(hnr_mean):
            hnr_mean = HNR_GOOD
    except Exception:
        hnr_mean = HNR_GOOD

    return {
        "pitch_mean": pitch_mean,
        "pitch_std": pitch_std,
        "pitch_range": pitch_range,
        "intensity_mean": intensity_mean,
        "intensity_std": intensity_std,
        "jitter": jitter_local,
        "shimmer": shimmer_local,
        "hnr": hnr_mean,
    }


def _compute_vad(features: dict, global_baseline: dict) -> dict:
    """Mapeia features acusticas para Valence/Arousal/Dominance.

    Heuristica derivada de eGeMAPS (Eyben et al. 2016). Saida normalizada:
    - Valence: -1 (negativo) a +1 (positivo)
    - Arousal: 0 (calmo) a 1 (excitado)
    - Dominance: 0 (submisso) a 1 (autoritario)
    """
    p_baseline = global_baseline["pitch_mean"]
    i_baseline = global_baseline["intensity_mean"]

    # Valence: HNR alto + jitter baixo = positivo. Pitch acima da media tambem.
    jitter_score = max(-0.5, min(0.5, (JITTER_NEUTRAL - features["jitter"]) / JITTER_NEUTRAL))
    hnr_score = max(-0.5, min(0.5, (features["hnr"] - HNR_GOOD) / 10))
    pitch_pos = max(-0.3, min(0.3, (features["pitch_mean"] - p_baseline) / max(p_baseline, 1)))
    valence = max(-1.0, min(1.0, jitter_score + hnr_score + pitch_pos))

    # Arousal: intensidade + range de pitch + std de intensidade
    intensity_rel = (features["intensity_mean"] - i_baseline) / max(i_baseline, 1)
    pitch_range_norm = min(1.0, features["pitch_range"] / 250)  # 250Hz = range expressivo
    intensity_var = min(1.0, features["intensity_std"] / 10)
    arousal = max(
        0.0, min(1.0, 0.4 + intensity_rel * 0.3 + pitch_range_norm * 0.4 + intensity_var * 0.2)
    )

    # Dominance: pitch medio (mais baixo = mais dominante) + intensidade estavel + HNR alto
    pitch_low_score = max(
        0.0, min(0.4, (p_baseline - features["pitch_mean"]) / max(p_baseline, 1) + 0.2)
    )
    intensity_stable = max(0.0, min(0.3, 0.3 - intensity_var * 0.3))
    hnr_dominance = max(0.0, min(0.3, features["hnr"] / 30))
    dominance = max(0.0, min(1.0, pitch_low_score + intensity_stable + hnr_dominance))

    return {
        "v": round(valence, 2),
        "a": round(arousal, 2),
        "d": round(dominance, 2),
    }


def _classify_textura(vad: dict) -> str:
    """Classifica VAD em uma das 6 texturas interpretaveis.

    Texturas ortogonais (NAO emocoes explicitas — abstratas por design).
    """
    v, a, d = vad["v"], vad["a"], vad["d"]

    # B9-real-v2: thresholds relaxados pra real-world mobile audio
    # (valence fica negativa por default em mobile devido a jitter/HNR)
    if v > 0.3 and a > 0.5 and d > 0.3:
        return "entusiasmado"
    if v < -0.4 and a > 0.6 and d <= 0.5:
        return "tenso"
    if v < -0.3 and a < 0.3 and d < 0.3:
        return "apatico"
    if -0.3 <= v < 0.1 and a < 0.4 and d < 0.4:
        return "hesitante"
    if v >= -0.2 and 0.3 <= a <= 0.7 and d > 0.4:
        return "confiante"
    return "neutro"


def _generate_feedback(distribuicao: dict, textura_dominante: str) -> str:
    """Gera feedback textual baseado na distribuicao de texturas."""
    pct_dominante = distribuicao.get(textura_dominante, 0)

    if textura_dominante == "neutro" and pct_dominante > 70:
        return (
            "Sua voz manteve textura constante (neutra) por quase todo o video. "
            "Aumentar variacao no tom emocional aumenta o engajamento. "
            "Trabalhe variacao consciente — fale com mais energia em pontos-chave."
        )
    if distribuicao.get("tenso", 0) > 30:
        return (
            "Pontos de tensao detectados em mais de 30% do tempo. "
            "Respirar antes de momentos criticos e ancorar pausas estrategicas pode reduzir essa tensao percebida."
        )
    if distribuicao.get("apatico", 0) > 50:
        return (
            "Energia baixa predominante (apatico em mais de 50%). "
            "Trabalhe generosidade de energia — sua voz precisa transmitir mais vitalidade."
        )
    if textura_dominante == "confiante" and distribuicao.get("confiante", 0) > 50:
        return (
            "Voz transmite confianca consistente — bom posicionamento autoral. "
            "Cuidado para nao virar default: alterne com texturas mais quentes em momentos de conexao."
        )
    if textura_dominante == "entusiasmado" and distribuicao.get("entusiasmado", 0) > 60:
        return (
            "Entusiasmo dominante na voz. Otimo para inspirar, mas alterne com momentos calmos "
            "para criar contraste e dar peso aos pontos importantes."
        )
    if distribuicao.get("hesitante", 0) > 30:
        return (
            "Marcas de hesitacao em mais de 30% do tempo. "
            "Esse padrao costuma vir junto com inseguranca — trabalhar respiracao e pausas estrategicas ajuda."
        )
    return (
        "Variacao saudavel de textura emocional vocal. "
        "Continue alternando entre texturas conforme o conteudo demanda."
    )


def _compute_tonality_metrics(audio_path: str) -> dict:
    """Analisa textura emocional vocal via VAD em janelas de 5s.

    Pipeline:
    1. Carrega audio
    2. Calcula features globais (baseline)
    3. Itera janelas de 5s, extrai features + VAD por janela
    4. Classifica textura por janela
    5. Agrega: distribuicao temporal + textura dominante + score
    """
    start = time.time()
    logger.info("tonality_analysis_start", audio_path=audio_path)

    try:
        sound = parselmouth.Sound(audio_path)
    except Exception as e:
        logger.error("tonality_load_failed", error=str(e))
        return _disponivel_false(f"Falha ao carregar audio: {e}")

    duration = sound.get_total_duration()
    if duration < MIN_AUDIO_DURATION:
        return _disponivel_false(
            f"Audio muito curto ({round(duration, 1)}s). Minimo {MIN_AUDIO_DURATION}s."
        )

    # Baseline global (toda a janela)
    global_features = _extract_features_window(sound, 0, duration)
    if global_features is None:
        return _disponivel_false("Sem voiced frames suficientes para analise")

    # Janelas de 5s
    n_windows = max(1, int(duration / WINDOW_SECONDS))
    window_dur = duration / n_windows

    vad_temporal = []
    texturas_count = {
        "neutro": 0,
        "entusiasmado": 0,
        "confiante": 0,
        "apatico": 0,
        "tenso": 0,
        "hesitante": 0,
    }
    successful_windows = 0

    for w in range(n_windows):
        t_start = w * window_dur
        t_end = (w + 1) * window_dur
        features = _extract_features_window(sound, t_start, t_end)
        if features is None:
            continue
        vad = _compute_vad(features, global_features)
        textura = _classify_textura(vad)
        texturas_count[textura] += 1
        successful_windows += 1
        vad_temporal.append(
            {
                "start": round(t_start, 1),
                "end": round(t_end, 1),
                "v": vad["v"],
                "a": vad["a"],
                "d": vad["d"],
                "textura": textura,
            }
        )

    if successful_windows == 0:
        return _disponivel_false("Nenhuma janela de audio teve features extraiveis")

    # Distribuicao percentual
    distribuicao = {
        textura: round(count / successful_windows * 100, 1)
        for textura, count in texturas_count.items()
    }
    textura_dominante = max(texturas_count, key=texturas_count.get)

    # VAD medio
    vad_medio = {
        "valence": round(float(np.mean([v["v"] for v in vad_temporal])), 2),
        "arousal": round(float(np.mean([v["a"] for v in vad_temporal])), 2),
        "dominance": round(float(np.mean([v["d"] for v in vad_temporal])), 2),
    }

    # =============================================
    # SCORE 0-100
    # =============================================
    # Variacao saudavel = score alto. Default = score baixo.
    pct_dominante = distribuicao[textura_dominante]
    num_texturas_usadas = sum(1 for c in texturas_count.values() if c > 0)

    # Diversidade base
    # B9-real-v2: sobe baseline — 1 textura=45, 6=95
    score = 45 + (num_texturas_usadas - 1) * 10

    # Penalty se >70% em uma textura (default)
    if pct_dominante > 80:
        score -= 25
    elif pct_dominante > 70:
        score -= 15

    # Penalty se dominante é negativo (apatico/tenso > 50%)
    if distribuicao["apatico"] > 50 or distribuicao["tenso"] > 50:
        score -= 15

    # Bonus se variacao boa entre 3+ texturas em proporcao saudavel
    if num_texturas_usadas >= 3 and pct_dominante < 60:
        score += 15

    score = max(0, min(100, round(score)))

    feedback = _generate_feedback(distribuicao, textura_dominante)

    # Diagnostico
    if score >= 75:
        diagnostico = "tonalidade_rica"
    elif score >= 50:
        diagnostico = "tonalidade_funcional"
    elif distribuicao["apatico"] > 40:
        diagnostico = "tonalidade_apatica"
    elif distribuicao["tenso"] > 30:
        diagnostico = "tonalidade_tensa"
    elif pct_dominante > 70:
        diagnostico = "tonalidade_uniforme"
    else:
        diagnostico = "tonalidade_limitada"

    elapsed = round(time.time() - start, 2)
    logger.info(
        "tonality_analysis_complete",
        score=score,
        diagnostico=diagnostico,
        textura_dominante=textura_dominante,
        n_texturas_usadas=num_texturas_usadas,
        duration_seconds=elapsed,
    )

    result = {
        "disponivel": True,
        "score": score,
        "diagnostico": diagnostico,
        "vad_medio": vad_medio,
        "vad_temporal": vad_temporal,
        "textura_distribuicao": distribuicao,
        "textura_dominante": textura_dominante,
        "feedback": feedback,
        "warnings": [],
    }

    # Story 9.3: enriquecimento ML opcional (flag TONALITY_ML_ENABLED).
    # Graceful fallback — se falhar, preserva path heuristico + metric counter.
    from config import is_tonality_ml_enabled

    if is_tonality_ml_enabled():
        try:
            from workers._emotion_ml import infer_emotions
            from workers._model_loader import ModelGPU

            with ModelGPU("wav2vec2_emotion") as bundle:
                ml_result = infer_emotions(bundle, audio_path)
                if ml_result is not None:
                    result.update(ml_result)
                    logger.info(
                        "tonality_ml_enriched",
                        emocao_dominante=ml_result.get("emocao_dominante_ml"),
                    )

                    # B9 calibration: reconcile heuristic "tenso" vs ML positive valence.
                    # Heuristica confunde intensidade de palestrante (alta energia,
                    # pitch variado) com tensao real. Quando ML indica valence neutra
                    # ou positiva, reclassifica tenso → intenso (alta energia saudavel).
                    vad_ml = ml_result.get("vad_ml", {})
                    ml_valence = vad_ml.get("valence", 0.0)
                    emocao_ml = ml_result.get("emocao_dominante_ml", "").lower()
                    heuristic_says_tense = (
                        distribuicao.get("tenso", 0) > 30
                        or textura_dominante == "tenso"
                    )
                    ml_says_positive = ml_valence > 0.1 or emocao_ml in {
                        "hap", "happy", "neu", "neutral"
                    }
                    if heuristic_says_tense and ml_says_positive:
                        # Revert score penalty aplicada em "tenso > 50" se houver
                        if distribuicao.get("tenso", 0) > 50:
                            result["score"] = min(100, result["score"] + 15)
                        # Reframe feedback
                        result["feedback"] = (
                            "Heuristica detectou intensidade vocal alta (jitter/arousal), "
                            "mas modelo ML indica valence positiva/neutra — sinal de "
                            "palestrante engajado, nao tensao real. Continue assim."
                        )
                        result["ml_reconciled"] = True
                        result["diagnostico"] = "tonalidade_intensa"
                        logger.info(
                            "tonality_ml_reconciled_tenso_to_intenso",
                            heuristic_tenso_pct=distribuicao.get("tenso", 0),
                            ml_valence=ml_valence,
                            emocao_ml=emocao_ml,
                        )
                else:
                    logger.warning("tonality_ml_inference_returned_none")
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "tonality_ml_fallback_triggered",
                error=str(e),
                error_type=type(e).__name__,
            )

    return result


def _disponivel_false(motivo: str) -> dict:
    return {
        "disponivel": False,
        "score": 0,
        "diagnostico": "indisponivel",
        "vad_medio": {"valence": 0.0, "arousal": 0.0, "dominance": 0.0},
        "vad_temporal": [],
        "textura_distribuicao": {
            "neutro": 0,
            "entusiasmado": 0,
            "confiante": 0,
            "apatico": 0,
            "tenso": 0,
            "hesitante": 0,
        },
        "textura_dominante": "indisponivel",
        "feedback": motivo,
        "warnings": [motivo],
    }


# Story 8.3 — Truth Contract
from contracts import WorkerFailure, WorkerResult, WorkerSuccess  # noqa: E402


def analyze_tonality_legacy(audio_path: str) -> dict:
    """Legacy path (TRUTH_CONTRACT_ENABLED=false)."""
    return _compute_tonality_metrics(audio_path)


def analyze_tonality(audio_path: str) -> "WorkerResult":
    """Truth Contract path — retorna WorkerResult (Pydantic).

    Adapta disponivel:bool pattern:
    - disponivel=True + score → WorkerSuccess
    - disponivel=False → WorkerFailure(skipped)
    - Exception → WorkerFailure(crashed)
    """
    try:
        result = _compute_tonality_metrics(audio_path)
        if not result.get("disponivel", True):
            return WorkerFailure(
                dimension="tonality",
                dimension_status="skipped",
                failure_reason=result.get("feedback", "analise de tonalidade indisponivel"),
                metrics=result,
            )
        score = result.get("score")
        if score is None:
            return WorkerFailure(
                dimension="tonality",
                dimension_status="insufficient_data",
                failure_reason="score is None after tonality analysis",
            )
        metrics = {k: v for k, v in result.items() if k not in ("score", "disponivel")}
        return WorkerSuccess(
            dimension="tonality",
            score=max(0, min(100, int(score))),
            metrics=metrics,
            confidence=1.0,
        )
    except Exception as e:
        logger.error("tonality_crashed", error_type=type(e).__name__, error=str(e), exc_info=True)
        return WorkerFailure(
            dimension="tonality",
            dimension_status="crashed",
            failure_reason=f"{type(e).__name__}: {str(e)}",
        )
