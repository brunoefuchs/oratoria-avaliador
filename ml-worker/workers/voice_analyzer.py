import time

import numpy as np
import parselmouth
import structlog
import whisper

logger = structlog.get_logger()


def transcribe_audio(audio_path: str, model_name: str = "medium") -> dict:
    """Transcribe audio using Whisper with word-level timestamps."""
    start = time.time()
    logger.info("whisper_transcribe_start", audio_path=audio_path, model=model_name)

    model = whisper.load_model(model_name)
    result = model.transcribe(
        audio_path,
        language="pt",
        word_timestamps=True,
    )

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
        "model": model_name,
    }


def analyze_prosody(audio_path: str) -> dict:
    """Extract prosodic features using Parselmouth (Praat)."""
    start = time.time()
    logger.info("prosody_analysis_start", audio_path=audio_path)

    sound = parselmouth.Sound(audio_path)
    duration_s = sound.get_total_duration()

    # Pitch (F0)
    pitch = sound.to_pitch()
    pitch_values = pitch.selected_array["frequency"]
    pitch_values = pitch_values[pitch_values > 0]  # Remove unvoiced frames

    pitch_mean = float(np.mean(pitch_values)) if len(pitch_values) > 0 else 0.0
    pitch_std = float(np.std(pitch_values)) if len(pitch_values) > 0 else 0.0
    pitch_min = float(np.min(pitch_values)) if len(pitch_values) > 0 else 0.0
    pitch_max = float(np.max(pitch_values)) if len(pitch_values) > 0 else 0.0

    # Pitch variation in semitones
    if pitch_min > 0 and pitch_max > 0:
        pitch_range_semitones = 12 * np.log2(pitch_max / pitch_min)
    else:
        pitch_range_semitones = 0.0

    # Intensity (volume)
    intensity = sound.to_intensity()
    intensity_values = intensity.values[0]
    intensity_mean = float(np.mean(intensity_values))

    # Speech rate and silence detection
    # Use intensity threshold to detect speech vs silence
    intensity_threshold = intensity_mean - 10  # dB below mean
    speech_frames = np.sum(intensity_values > intensity_threshold)
    total_frames = len(intensity_values)
    speech_ratio = speech_frames / total_frames if total_frames > 0 else 0.0

    elapsed = time.time() - start
    logger.info(
        "prosody_analysis_complete",
        duration_seconds=round(elapsed, 2),
        pitch_mean=round(pitch_mean, 1),
    )

    return {
        "pitch_mean_hz": round(pitch_mean, 1),
        "pitch_std_hz": round(pitch_std, 1),
        "pitch_min_hz": round(pitch_min, 1),
        "pitch_max_hz": round(pitch_max, 1),
        "pitch_range_semitones": round(float(pitch_range_semitones), 1),
        "intensity_mean_db": round(intensity_mean, 1),
        "speech_silence_ratio": round(speech_ratio, 3),
        "audio_duration_seconds": round(duration_s, 2),
    }


def calculate_voice_metrics(transcription: dict, prosody: dict) -> dict:
    """Calculate combined voice metrics from transcription and prosody."""
    words = transcription.get("words", [])
    audio_duration = prosody.get("audio_duration_seconds", 0)

    # WPM
    word_count = len(words)
    duration_minutes = audio_duration / 60 if audio_duration > 0 else 1
    wpm = round(word_count / duration_minutes)

    # Voice score (0-100)
    # Based on: WPM in ideal range (130-170), pitch variation, speech ratio
    wpm_score = max(0, 100 - abs(wpm - 150) * 2)
    pitch_score = min(100, prosody["pitch_range_semitones"] * 8)
    ratio_score = min(100, prosody["speech_silence_ratio"] * 120)

    voice_score = round((wpm_score * 0.4 + pitch_score * 0.35 + ratio_score * 0.25))
    voice_score = max(0, min(100, voice_score))

    return {
        "score": voice_score,
        "wpm": wpm,
        "word_count": word_count,
        **prosody,
    }
