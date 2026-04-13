import time

import numpy as np
import parselmouth
import structlog
import whisper

logger = structlog.get_logger()

# Tamanho da janela temporal para analise de variacao (segundos)
JANELA_SEGUNDOS = 15
# Range ideal de palavras por minuto (PT-BR conversacional)
WPM_IDEAL_MIN = 130
WPM_IDEAL_MAX = 170
WPM_IDEAL_CENTRO = 150


def transcribe_audio(audio_path: str, model_name: str = "medium") -> dict:
    """Transcreve audio usando Whisper com timestamps por palavra."""
    start = time.time()
    logger.info("whisper_transcribe_start", audio_path=audio_path, model=model_name)

    model = whisper.load_model(model_name)
    result = model.transcribe(audio_path, language="pt", word_timestamps=True)

    words = []
    for segment in result.get("segments", []):
        for word_info in segment.get("words", []):
            words.append({
                "word": word_info["word"].strip(),
                "start": round(word_info["start"], 3),
                "end": round(word_info["end"], 3),
                "confidence": round(word_info.get("probability", 0.0), 3),
            })

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
        "model": model_name,
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

    janela_count = max(1, int(duration_s / JANELA_SEGUNDOS))
    pitch_por_janela = []
    volume_por_janela = []

    for j in range(janela_count):
        t_start = j * JANELA_SEGUNDOS
        t_end = (j + 1) * JANELA_SEGUNDOS

        # Pitch medio na janela
        mask_pitch = (pitch_timestamps >= t_start) & (pitch_timestamps < t_end)
        janela_pitch = pitch_all[mask_pitch]
        janela_pitch = janela_pitch[janela_pitch > 0]
        pitch_por_janela.append(round(float(np.mean(janela_pitch)), 1) if len(janela_pitch) > 0 else 0.0)

        # Volume medio na janela
        int_timestamps = intensity.xs()
        mask_int = (int_timestamps >= t_start) & (int_timestamps < t_end)
        janela_int = intensity_values[mask_int]
        volume_por_janela.append(round(float(np.mean(janela_int)), 1) if len(janela_int) > 0 else 0.0)

    # CV de pitch e volume calculados a partir das MEDIAS POR JANELA (nao valores brutos)
    # Isso garante que medimos variacao TEMPORAL, nao variacao frame-a-frame
    if len(pitch_por_janela) >= 2:
        valid_pitch = [p for p in pitch_por_janela if p > 0]
        cv_pitch = round(float(np.std(valid_pitch) / (abs(np.mean(valid_pitch)) + 1e-8)), 4) if valid_pitch else 0.0
    else:
        cv_pitch = 0.0

    if len(volume_por_janela) >= 2:
        cv_volume = round(float(np.std(volume_por_janela) / (abs(np.mean(volume_por_janela)) + 1e-8)), 4)
    else:
        cv_volume = 0.0

    # Volume base (1-10 scale)
    volume_base_1_10 = round(min(10, max(1, (intensity_mean - 40) / 4)), 1) if intensity_mean > 40 else 1.0

    elapsed = time.time() - start
    logger.info(
        "prosody_analysis_complete",
        duration_seconds=round(elapsed, 2),
        pitch_mean=round(pitch_mean, 1),
        cv_pitch=cv_pitch,
        cv_volume=cv_volume,
    )

    return {
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
    }


def _classificar_pausas(words: list, prosody: dict) -> dict:
    """Classifica pausas em estrategicas, de hesitacao ou de respiracao."""
    pausas_estrategicas = []
    pausas_hesitacao = []
    pausas_respiracao = []

    fillers_set = {
        "ne", "né", "tipo", "então", "entao", "hum", "humm",
        "ai", "aí", "assim", "basicamente", "ta", "tá", "eee", "eeee", "eeeee"
    }

    for i in range(1, len(words)):
        gap = words[i]["start"] - words[i - 1]["end"]
        if gap < 0.2:
            continue

        prev_word = words[i - 1]["word"].lower().strip(".,!?")
        next_word = words[i]["word"].lower().strip(".,!?")

        pausa = {
            "start": round(words[i - 1]["end"], 2),
            "end": round(words[i]["start"], 2),
            "duration": round(gap, 2),
        }

        # Classificacao sem depender de pontuacao (Whisper nao coloca nas words)
        # 1. Antes de filler = hesitacao
        if next_word in fillers_set:
            pausas_hesitacao.append(pausa)
        # 2. Pausa estrategica: 0.6-3s e NAO antes de filler
        elif 0.6 <= gap <= 3.0:
            pausas_estrategicas.append(pausa)
        # 3. Micro-pausa 0.2-0.6s = respiracao
        elif 0.2 <= gap < 0.6:
            pausas_respiracao.append(pausa)
        # 4. Pausa muito longa > 3s = hesitacao
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


def calculate_voice_metrics(transcription: dict, prosody: dict) -> dict:
    """Calcula metricas de voz combinando transcricao e prosodia."""
    words = transcription.get("words", [])
    audio_duration = prosody.get("audio_duration_seconds", 0)

    # WPM
    word_count = len(words)
    duration_minutes = audio_duration / 60 if audio_duration > 0 else 1
    wpm = round(word_count / duration_minutes)

    # WPM por janela
    janela_count = prosody.get("num_janelas", 1)
    wpm_por_janela = []
    for j in range(janela_count):
        t_start = j * JANELA_SEGUNDOS
        t_end = (j + 1) * JANELA_SEGUNDOS
        words_in_janela = [w for w in words if t_start <= w.get("start", 0) < t_end]
        janela_dur_min = JANELA_SEGUNDOS / 60
        wpm_por_janela.append(round(len(words_in_janela) / janela_dur_min))

    # CV de velocidade (entre janelas)
    if len(wpm_por_janela) >= 2:
        cv_velocidade = round(float(np.std(wpm_por_janela) / (abs(np.mean(wpm_por_janela)) + 1e-8)), 4)
    else:
        cv_velocidade = 0.0

    # Classificacao de pausas
    pausas = _classificar_pausas(words, prosody)

    # Score anti-monotonia
    pitch_janelas = prosody.get("pitch_por_janela", [])
    volume_janelas = prosody.get("volume_por_janela", [])
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
    if cv_velocidade < 0.05:
        velocidade_score = 20
    elif cv_velocidade <= 0.15:
        velocidade_score = 50 + (cv_velocidade - 0.05) * 500
    elif cv_velocidade <= 0.30:
        velocidade_score = 100
    elif cv_velocidade <= 0.45:
        velocidade_score = 100 - (cv_velocidade - 0.30) * 333
    else:
        velocidade_score = max(0, 50 - (cv_velocidade - 0.45) * 200)

    # 4. Variacao de volume (CV entre janelas) — peso 20%
    cv_vol = prosody.get("cv_volume", 0)
    if cv_vol < 0.03:
        volume_score = 20
    elif cv_vol <= 0.10:
        volume_score = 50 + (cv_vol - 0.03) * 714
    elif cv_vol <= 0.25:
        volume_score = 100
    elif cv_vol <= 0.40:
        volume_score = 100 - (cv_vol - 0.25) * 333
    else:
        volume_score = max(0, 50 - (cv_vol - 0.40) * 200)

    # 5. Qualidade das pausas — peso 20%
    ratio_estrategicas = pausas["ratio_estrategicas"]
    qtd_hesitacao_por_min = pausas["hesitacao_por_min"]

    pausa_score_base = ratio_estrategicas * 100
    if qtd_hesitacao_por_min > 5:
        penalidade_hesitacao = min(40, (qtd_hesitacao_por_min - 5) * 8)
    else:
        penalidade_hesitacao = 0

    qtd_estrategicas_por_min = pausas["estrategicas_por_min"]
    if qtd_estrategicas_por_min >= 2:
        bonus_pausa = 20
    elif qtd_estrategicas_por_min >= 1:
        bonus_pausa = 10
    else:
        bonus_pausa = 0

    pausa_score = min(100, max(0, pausa_score_base - penalidade_hesitacao + bonus_pausa))

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
