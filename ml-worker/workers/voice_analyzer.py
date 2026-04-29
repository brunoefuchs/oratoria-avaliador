import os
import time

import numpy as np
import parselmouth
import structlog
import whisper

from config import is_whisper_turbo_enabled
from contracts import WorkerResult
from workers._truth_contract_helpers import wrap_worker_result

logger = structlog.get_logger()

# Tamanho da janela temporal adaptativo (2026-04-29):
# - Curtos (<60s): janelas pequenas (5s) capturam dinamica intra-frase
# - Longos (>2min): janelas maiores (~12s) reduzem ruido/AGC
# Alvo: ~12 janelas minimo, clamp 5-12s.
JANELA_SEGUNDOS_MIN = 5
JANELA_SEGUNDOS_MAX = 12
JANELA_COUNT_TARGET = 12
# Range ideal de palavras por minuto (PT-BR conversacional)
WPM_IDEAL_MIN = 130
WPM_IDEAL_MAX = 170
WPM_IDEAL_CENTRO = 150

# Story 9.2: default model preservado para rollback via WHISPER_TURBO_ENABLED=false.
_WHISPER_FALLBACK_MODEL = "medium"


def _resolve_whisper_model(model_name: str | None = None) -> str:
    """Seleciona model name conforme flag + env override.

    Prioridade:
      1. Argumento explicito (caller override — mantido pra compat de testes)
      2. WHISPER_MODEL env var (debug manual)
      3. WHISPER_TURBO_ENABLED=true → "turbo"
      4. Fallback medium
    """
    if model_name is not None:
        return model_name
    env_override = os.getenv("WHISPER_MODEL")
    if env_override:
        return env_override
    if is_whisper_turbo_enabled():
        return "turbo"
    return _WHISPER_FALLBACK_MODEL


def _load_whisper_with_fallback(model_name: str):
    """Carrega Whisper com fallback automatico pra medium se falhar.

    Story 9.2 AC2: turbo pode falhar (download indisponivel, VRAM OOM, etc).
    Nunca quebra pipeline — fallback medium + log.
    """
    try:
        return whisper.load_model(model_name)
    except Exception as e:  # noqa: BLE001 — queremos fallback em qualquer erro de load
        if model_name == _WHISPER_FALLBACK_MODEL:
            raise  # medium ja falhou, sem recurso
        logger.warning(
            "whisper_turbo_fallback_triggered",
            requested_model=model_name,
            fallback_model=_WHISPER_FALLBACK_MODEL,
            error=str(e),
            error_type=type(e).__name__,
        )
        return whisper.load_model(_WHISPER_FALLBACK_MODEL)


def transcribe_audio(audio_path: str, model_name: str | None = None) -> dict:
    """Transcreve audio usando Whisper com timestamps por palavra.

    Story 7.1 fix (2026-04-14): preservar fillers PT-BR.
    - initial_prompt informa o modelo para nao "limpar" muletas/hesitacoes
    - condition_on_previous_text=False evita "alucinacao corretiva" baseada em contexto

    Story 9.2 (Epic 9): model_name=None → resolve via flag/env. turbo (default)
    com fallback medium se load falhar.
    """
    resolved_model = _resolve_whisper_model(model_name)
    start = time.time()
    logger.info("whisper_transcribe_start", audio_path=audio_path, model=resolved_model)

    model = _load_whisper_with_fallback(resolved_model)
    try:
        result = model.transcribe(
            audio_path,
            language="pt",
            word_timestamps=True,
            initial_prompt=(
                "Esta e uma transcricao fiel de oratoria em portugues brasileiro. "
                "Preserve TODOS os vicios de linguagem como ne, tipo, ai, sabe, entao, ahn, eh, hum. "
                "Nao corrija nem omita marcadores de hesitacao."
            ),
            condition_on_previous_text=False,
        )
    finally:
        # Story 9.2: unload explicito quando orchestrator ativo, libera VRAM
        # pros workers MediaPipe + ML novos (9.3/9.5) nao estourarem 8.6GB.
        from config import is_orchestrator_enabled

        if is_orchestrator_enabled():
            import gc

            del model
            gc.collect()
            try:
                import torch

                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    logger.info(
                        "whisper_vram_unloaded",
                        peak_gb=round(torch.cuda.max_memory_allocated() / 1e9, 2),
                    )
            except (ImportError, RuntimeError):
                pass

    words = []
    for segment in result.get("segments", []):
        for word_info in segment.get("words", []):
            words.append(
                {
                    "word": word_info["word"].strip(),
                    "start": round(word_info["start"], 3),
                    "end": round(word_info["end"], 3),
                    "confidence": round(word_info.get("probability", 0.0), 3),
                }
            )

    duration = time.time() - start
    logger.info(
        "whisper_transcribe_complete",
        word_count=len(words),
        duration_seconds=round(duration, 2),
    )

    return {
        "full_text": result.get("text", "").strip(),
        "words": words,
        "language": "pt-BR",
        "model": resolved_model,  # bug fix: era model_name (None quando caller passa None)
    }


def analyze_prosody(audio_path: str) -> dict:
    """Extrai features prosodicas usando Parselmouth (Praat)."""
    start = time.time()
    logger.info("prosody_analysis_start", audio_path=audio_path)

    sound = parselmouth.Sound(audio_path)
    duration_s = sound.get_total_duration()

    # Pitch (F0)
    pitch = sound.to_pitch()
    pitch_values = pitch.selected_array["frequency"]
    pitch_values = pitch_values[pitch_values > 0]

    pitch_mean = float(np.mean(pitch_values)) if len(pitch_values) > 0 else 0.0
    pitch_std = float(np.std(pitch_values)) if len(pitch_values) > 0 else 0.0
    pitch_min = float(np.min(pitch_values)) if len(pitch_values) > 0 else 0.0
    pitch_max = float(np.max(pitch_values)) if len(pitch_values) > 0 else 0.0

    if pitch_min > 0 and pitch_max > 0:
        pitch_range_semitones = 12 * np.log2(pitch_max / pitch_min)
    else:
        pitch_range_semitones = 0.0

    # Intensity (volume)
    intensity = sound.to_intensity()
    intensity_values = intensity.values[0]
    intensity_mean = float(np.mean(intensity_values))
    intensity_std = float(np.std(intensity_values))
    intensity_min = float(np.min(intensity_values))
    intensity_max = float(np.max(intensity_values))

    # Speech rate and silence detection
    intensity_threshold = intensity_mean - 10
    speech_frames = np.sum(intensity_values > intensity_threshold)
    total_frames = len(intensity_values)
    speech_ratio = speech_frames / total_frames if total_frames > 0 else 0.0

    # Analise por janela temporal
    pitch_timestamps = pitch.xs()
    pitch_all = pitch.selected_array["frequency"]

    # N janelas uniformes cobrindo 100% da duracao (evita cauda ignorada).
    # Adaptativo: alvo ~12 janelas, clamp 5-12s.
    janela_size_target = max(
        JANELA_SEGUNDOS_MIN, min(JANELA_SEGUNDOS_MAX, duration_s / JANELA_COUNT_TARGET)
    )
    janela_count = max(1, round(duration_s / janela_size_target))
    janela_size = duration_s / janela_count
    pitch_por_janela = []
    volume_por_janela = []

    for j in range(janela_count):
        t_start = j * janela_size
        t_end = (j + 1) * janela_size

        # Pitch medio na janela
        mask_pitch = (pitch_timestamps >= t_start) & (pitch_timestamps < t_end)
        janela_pitch = pitch_all[mask_pitch]
        janela_pitch = janela_pitch[janela_pitch > 0]
        pitch_por_janela.append(
            round(float(np.mean(janela_pitch)), 1) if len(janela_pitch) > 0 else 0.0
        )

        # Volume medio na janela
        int_timestamps = intensity.xs()
        mask_int = (int_timestamps >= t_start) & (int_timestamps < t_end)
        janela_int = intensity_values[mask_int]
        volume_por_janela.append(
            round(float(np.mean(janela_int)), 1) if len(janela_int) > 0 else 0.0
        )

    # CV de pitch e volume calculados a partir das MEDIAS POR JANELA (nao valores brutos)
    # Isso garante que medimos variacao TEMPORAL, nao variacao frame-a-frame
    if len(pitch_por_janela) >= 2:
        valid_pitch = [p for p in pitch_por_janela if p > 0]
        cv_pitch = (
            round(float(np.std(valid_pitch) / (abs(np.mean(valid_pitch)) + 1e-8)), 4)
            if valid_pitch
            else 0.0
        )
    else:
        cv_pitch = 0.0

    if len(volume_por_janela) >= 2:
        cv_volume = round(
            float(np.std(volume_por_janela) / (abs(np.mean(volume_por_janela)) + 1e-8)), 4
        )
    else:
        cv_volume = 0.0

    # Volume base (1-10 scale)
    volume_base_1_10 = (
        round(min(10, max(1, (intensity_mean - 40) / 4)), 1) if intensity_mean > 40 else 1.0
    )

    elapsed = time.time() - start
    logger.info(
        "prosody_analysis_complete",
        duration_seconds=round(elapsed, 2),
        pitch_mean=round(pitch_mean, 1),
        cv_pitch=cv_pitch,
        cv_volume=cv_volume,
    )

    result = {
        "pitch_mean_hz": round(pitch_mean, 1),
        "pitch_std_hz": round(pitch_std, 1),
        "pitch_min_hz": round(pitch_min, 1),
        "pitch_max_hz": round(pitch_max, 1),
        "pitch_range_semitones": round(float(pitch_range_semitones), 1),
        "cv_pitch": cv_pitch,
        "intensity_mean_db": round(intensity_mean, 1),
        "intensity_std_db": round(intensity_std, 1),
        "intensity_min_db": round(intensity_min, 1),
        "intensity_max_db": round(intensity_max, 1),
        "cv_volume": cv_volume,
        "volume_base_1_10": volume_base_1_10,
        "speech_silence_ratio": round(speech_ratio, 3),
        "audio_duration_seconds": round(duration_s, 2),
        "pitch_por_janela": pitch_por_janela,
        "volume_por_janela": volume_por_janela,
        "num_janelas": janela_count,
        "janela_size_seconds": round(janela_size, 2),
    }

    # Story 9.4: enriquecimento opcional via flags (graceful fallback se libs ausentes).
    from config import is_opensmile_enabled, is_pyannote_vad_enabled
    from workers._prosody_extras import detect_pauses, extract_egemaps

    if is_opensmile_enabled():
        egemaps = extract_egemaps(audio_path)
        if egemaps is not None:
            result["egemaps"] = egemaps
            logger.info("egemaps_extracted", feature_count=len(egemaps))

    if is_pyannote_vad_enabled():
        pauses_data = detect_pauses(audio_path)
        result["pauses_classified"] = pauses_data
        logger.info(
            "pauses_detected",
            total=sum(pauses_data["counts"].values()),
            retorical_ratio=pauses_data["total_retorical_ratio"],
            source=pauses_data["source"],
        )

    return result


CONTINUACAO_WORDS = {
    # Conectivos + muletas — pausa antes deles eh respiracao, nao retorica
    "e", "mas", "que", "ou", "então", "entao", "aí", "ai", "né", "ne",
    "um", "uma", "uns", "umas", "o", "a", "os", "as", "de", "do", "da",
    "dos", "das", "no", "na", "nos", "nas", "em", "pra", "para", "com",
    "sem", "por", "se", "quando", "onde", "enquanto", "porque", "pois",
    "sabe", "tipo", "assim",
}


def _classificar_pausas(words: list, prosody: dict) -> dict:
    """Classifica pausas em estrategicas, de hesitacao ou de respiracao."""
    pausas_estrategicas = []
    pausas_hesitacao = []
    pausas_respiracao = []

    # Apenas sons de hesitacao REAIS (nao muletas como "entao", "ai")
    # Muletas nao tornam a pausa antes delas uma "hesitacao"
    hesitacao_sounds = {
        "hum",
        "humm",
        "hummm",
        "eee",
        "eeee",
        "eeeee",
        "ãã",
        "aaa",
        "uhh",
        "éee",
    }

    for i in range(1, len(words)):
        gap = words[i]["start"] - words[i - 1]["end"]
        if gap < 0.2:
            continue

        words[i - 1]["word"].lower().strip(".,!?")
        next_word = words[i]["word"].lower().strip(".,!?")

        pausa = {
            "start": round(words[i - 1]["end"], 2),
            "end": round(words[i]["start"], 2),
            "duration": round(gap, 2),
        }

        # Classificacao sem depender de pontuacao (Whisper nao coloca nas words)
        # 1. Antes de som de hesitacao = hesitacao
        if next_word in hesitacao_sounds:
            pausas_hesitacao.append(pausa)
        # 2. Pausa estrategica longa: 0.5-3s (sempre retorica)
        elif 0.5 <= gap <= 3.0:
            pausas_estrategicas.append(pausa)
        # 3. Pausa curta 0.35-0.5s: retorica SE palavra seguinte for content-word
        # (validado 2026-04-18 — ouvido treinado capta pausas curtas antes de
        # palavra-chave; duracao sozinha eh feature insuficiente).
        elif 0.35 <= gap < 0.5 and next_word not in CONTINUACAO_WORDS:
            pausas_estrategicas.append(pausa)
        # 4. Micro-pausa 0.2-0.5s com continuacao = respiracao
        elif 0.2 <= gap < 0.5:
            pausas_respiracao.append(pausa)
        # 5. Pausa muito longa > 3s = hesitacao
        elif gap > 3.0:
            pausas_hesitacao.append(pausa)

    total_pausas = len(pausas_estrategicas) + len(pausas_hesitacao) + len(pausas_respiracao)
    duration_minutes = prosody.get("audio_duration_seconds", 1) / 60

    return {
        "qtd_estrategicas": len(pausas_estrategicas),
        "qtd_hesitacao": len(pausas_hesitacao),
        "qtd_respiracao": len(pausas_respiracao),
        "hesitacao_por_min": round(len(pausas_hesitacao) / max(duration_minutes, 0.1), 1),
        "estrategicas_por_min": round(len(pausas_estrategicas) / max(duration_minutes, 0.1), 1),
        "ratio_estrategicas": round(len(pausas_estrategicas) / max(total_pausas, 1), 3),
        "estrategicas": pausas_estrategicas,
        "hesitacao": pausas_hesitacao,
        "respiracao": pausas_respiracao,
    }


def _compute_voice_metrics(transcription: dict, prosody: dict) -> dict:
    """Calcula metricas de voz combinando transcricao e prosodia."""
    words = transcription.get("words", [])
    audio_duration = prosody.get("audio_duration_seconds", 0)

    # WPM
    word_count = len(words)
    duration_minutes = audio_duration / 60 if audio_duration > 0 else 1
    wpm = round(word_count / duration_minutes)

    # WPM por janela — usa o mesmo tamanho de janela real do prosody (cobre 100%).
    janela_count = prosody.get("num_janelas", 1)
    janela_size = prosody.get("janela_size_seconds") or (
        audio_duration / janela_count if janela_count > 0 else JANELA_SEGUNDOS_MIN
    )
    janela_dur_min = janela_size / 60
    wpm_por_janela = []
    for j in range(janela_count):
        t_start = j * janela_size
        t_end = (j + 1) * janela_size
        words_in_janela = [w for w in words if t_start <= w.get("start", 0) < t_end]
        wpm_por_janela.append(
            round(len(words_in_janela) / janela_dur_min) if janela_dur_min > 0 else 0
        )

    # CV de velocidade (entre janelas)
    if len(wpm_por_janela) >= 2:
        cv_velocidade = round(
            float(np.std(wpm_por_janela) / (abs(np.mean(wpm_por_janela)) + 1e-8)), 4
        )
    else:
        cv_velocidade = 0.0

    # Classificacao de pausas
    pausas = _classificar_pausas(words, prosody)

    # Score anti-monotonia
    prosody.get("pitch_por_janela", [])
    prosody.get("volume_por_janela", [])
    cv_pitch = prosody.get("cv_pitch", 0)
    cv_volume = prosody.get("cv_volume", 0)

    monotonia_score = 0
    if cv_pitch > 0.05:
        monotonia_score += 30
    if cv_volume > 0.03:
        monotonia_score += 30
    if cv_velocidade > 0.08:
        monotonia_score += 20
    if pausas["ratio_estrategicas"] > 0.15:
        monotonia_score += 20
    monotonia_score = min(100, monotonia_score)

    # =============================================
    # SCORE DE VOZ (0-100) — 5 componentes × 20%
    # =============================================

    # 1. WPM no range ideal (130-170) — peso 20%
    if WPM_IDEAL_MIN <= wpm <= WPM_IDEAL_MAX:
        wpm_score = 100 - abs(wpm - WPM_IDEAL_CENTRO)
    else:
        distancia = min(abs(wpm - WPM_IDEAL_MIN), abs(wpm - WPM_IDEAL_MAX))
        wpm_score = max(0, 80 - distancia * 2)

    # 2. Variacao de pitch — peso 20%
    pitch_range = prosody["pitch_range_semitones"]
    if pitch_range >= 15:
        pitch_score = 100
    elif pitch_range >= 10:
        pitch_score = 70 + (pitch_range - 10) * 6
    elif pitch_range >= 5:
        pitch_score = 40 + (pitch_range - 5) * 6
    else:
        pitch_score = pitch_range * 8

    # 3. Variacao de velocidade (CV entre janelas) — peso 20%
    # 2026-04-29: plato apertado (0.20-0.30) — janelas adaptativas (5-12s)
    # captam mais variacao, plato largo (0.12+) saturava CV moderado em 100
    # e perdia discriminacao. Rampa estendida 0.03-0.20 distingue melhor.
    if cv_velocidade < 0.03:
        velocidade_score = 20
    elif cv_velocidade <= 0.20:
        velocidade_score = 50 + (cv_velocidade - 0.03) * 294
    elif cv_velocidade <= 0.30:
        velocidade_score = 100
    elif cv_velocidade <= 0.45:
        velocidade_score = 100 - (cv_velocidade - 0.30) * 333
    else:
        velocidade_score = max(0, 50 - (cv_velocidade - 0.45) * 200)

    # 4. Variacao de volume (CV entre janelas) — peso 20%
    # B13-real calibration: AGC de smartphone comprime dinamica em 6-10 dB vs
    # mic condensador studio. Threshold antigo cv_vol<0.03 penalizava palestrantes
    # controlados gravando em celular. Piso rebaixado pra 0.015.
    cv_vol = prosody.get("cv_volume", 0)
    if cv_vol < 0.015:
        volume_score = 20
    elif cv_vol <= 0.08:
        volume_score = 50 + (cv_vol - 0.015) * 769
    elif cv_vol <= 0.25:
        volume_score = 100
    elif cv_vol <= 0.40:
        volume_score = 100 - (cv_vol - 0.25) * 333
    else:
        volume_score = max(0, 50 - (cv_vol - 0.40) * 200)

    # 5. Qualidade das pausas — peso 20%
    # Scoring por DENSIDADE absoluta (estrategicas/min), nao ratio.
    # Ratio penalizava palestrantes com boa respiracao (mais pausas totais).
    # Calibrado 2026-04-18 via Gui (6.67 estrategicas/min = tier TEDx).
    qtd_hesitacao_por_min = pausas["hesitacao_por_min"]
    qtd_estrategicas_por_min = pausas["estrategicas_por_min"]
    ratio_estrategicas = pausas["ratio_estrategicas"]

    # Densidade absoluta como score base (tier)
    if qtd_estrategicas_por_min >= 4:
        densidade_score = 100
    elif qtd_estrategicas_por_min >= 2:
        densidade_score = 85
    elif qtd_estrategicas_por_min >= 1:
        densidade_score = 70
    elif qtd_estrategicas_por_min > 0:
        densidade_score = 55
    else:
        densidade_score = 30

    # Quality modulator pela razao estrategicas/total. Ratio 0.5+ = full credit.
    # Protege contra sobre-deteccao em fala hesitante (pausas frequentes mas
    # curtas e pre-content-word podem passar por estrategicas sem serem).
    quality_factor = min(1.0, ratio_estrategicas * 2)
    pausa_score_base = densidade_score * quality_factor

    if qtd_hesitacao_por_min > 5:
        penalidade_hesitacao = min(40, (qtd_hesitacao_por_min - 5) * 8)
    else:
        penalidade_hesitacao = 0

    pausa_score = min(100, max(0, pausa_score_base - penalidade_hesitacao))

    # B11 calibration: pausa penalty condicional.
    # Ausencia de pausa retorica NAO e problema quando fala e calma (wpm<=180)
    # e sem muita hesitacao (<=5/min). Aplica baseline neutro 50 nesses casos.
    if pausa_score < 50 and wpm <= 180 and qtd_hesitacao_por_min <= 5:
        pausa_score = max(pausa_score, 50)

    # Score final ponderado
    voice_score = round(
        wpm_score * 0.20
        + pitch_score * 0.20
        + velocidade_score * 0.20
        + volume_score * 0.20
        + pausa_score * 0.20
    )
    voice_score = max(0, min(100, voice_score))

    logger.info(
        "voice_metrics_complete",
        score=voice_score,
        wpm=wpm,
        sub_scores={
            "wpm": round(wpm_score),
            "pitch": round(pitch_score),
            "velocidade": round(velocidade_score),
            "volume": round(volume_score),
            "pausa": round(pausa_score),
        },
    )

    return {
        "score": voice_score,
        "confidence": "high",
        "metrics": {
            "wpm": wpm,
            "word_count": word_count,
            "wpm_por_janela": wpm_por_janela,
            "cv_velocidade": cv_velocidade,
            "num_janelas": janela_count,
            "monotonia_score": monotonia_score,
            "volume_base_1_10": prosody.get("volume_base_1_10", 5),
            "pausas": pausas,
            "sub_scores": {
                "wpm_score": round(wpm_score),
                "pitch_score": round(pitch_score),
                "velocidade_score": round(velocidade_score),
                "volume_score": round(volume_score),
                "pausa_score": round(pausa_score),
            },
            # Prosodia
            **{k: v for k, v in prosody.items()},
            # Duracao
            "audio_duration_seconds": audio_duration,
        },
    }


def calculate_voice_metrics(transcription: dict, prosody: dict) -> dict:
    """Legacy path (TRUTH_CONTRACT_ENABLED=false). Kept for backwards compat with app.py."""
    return _compute_voice_metrics(transcription, prosody)


def analyze_voice_legacy(transcription: dict, prosody: dict) -> dict:
    """Legacy path alias (TRUTH_CONTRACT_ENABLED=false)."""
    return _compute_voice_metrics(transcription, prosody)


def analyze_voice(transcription: dict, prosody: dict) -> "WorkerResult":
    """Truth Contract path (TRUTH_CONTRACT_ENABLED=true)."""
    return wrap_worker_result("voice", _compute_voice_metrics, transcription, prosody)
