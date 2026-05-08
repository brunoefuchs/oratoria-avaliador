import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
CALLBACK_SECRET = os.getenv("CALLBACK_SECRET", "dev-secret")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "medium")
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG")

# Feature flag: shadow mode do squad oratoria-avaliador.
# Quando true, o squad roda em paralelo ao report_generator existente.
# Não altera comportamento user-facing — só loga decisões para comparação.
# Default false. Ativar via env var ORATORIA_SHADOW_MODE_ENABLED=true.
ORATORIA_SHADOW_MODE_ENABLED = os.getenv("ORATORIA_SHADOW_MODE_ENABLED", "false").lower() == "true"

# Feature flag: Truth Contract (Story 8.1).
# Quando true, workers migrados retornam WorkerResult (Pydantic) e analysis_results
# grava dimension_status + failure_reason. Quando false, usa path legacy com
# score=0 fallback em falha (comportamento pre-Epic 8.0).
#
# Rollout seguro: env var → reload basta (sem restart). Kill switch imediato.
# Story 8.3: default AGORA e true — todos os 13 workers migrados.
# Kill switch: env var TRUTH_CONTRACT_ENABLED=false reverte pra legacy.
#
# Workers migrados (Story 8.2): posture, gesture, voice, fillers, archetypes, identity
# Workers migrados (Story 8.3): facial, tonality, opening, storytelling, temporal, congruence
# Total migrado: 13 workers (incluindo variety da Story 8.1)
TRUTH_CONTRACT_ENABLED = os.getenv("TRUTH_CONTRACT_ENABLED", "true").lower() == "true"

# Feature flag: Epic 9 State of the Art (Story 9.1).
# Quando true, aggregator usa nova formula de pesos (6 scoring dims) + SECONDARY_DIMENSIONS
# separadas + confidence badges no payload. Schema bump pra v1.2.0.
# Default false — rollback instantaneo garantido. v0.6.0 preservada bit-identica.
#
# Gate 2 antes de flip em prod: 10 videos smoke, delta overall_score <=15pt,
# rastreabilidade por fórmula, direção consistente (monotonicos ↓, variados ↑).
STATE_OF_ART_ENABLED = os.getenv("STATE_OF_ART_ENABLED", "false").lower() == "true"


def is_state_of_art_enabled() -> bool:
    """Helper testavel pra leitura da flag Epic 9.

    Usar este helper em vez de ler a constante diretamente quando precisar
    monkeypatchar em testes (pytest.MonkeyPatch.setenv + reimport).
    """
    return os.getenv("STATE_OF_ART_ENABLED", "false").strip().lower() == "true"


# Feature flag: Epic 9 Story 9.2 — Whisper large-v3-turbo.
# Quando true (default), voice_analyzer tenta "turbo" e faz fallback para WHISPER_MODEL
# (medium) se load falhar. Rollback explicito via WHISPER_TURBO_ENABLED=false.
WHISPER_TURBO_ENABLED = os.getenv("WHISPER_TURBO_ENABLED", "true").lower() == "true"


def is_whisper_turbo_enabled() -> bool:
    """Helper testavel pra flag Story 9.2."""
    return os.getenv("WHISPER_TURBO_ENABLED", "true").strip().lower() == "true"


# Feature flag: Epic 9 Story 9.2 — Model Orchestrator (VRAM management).
# AC9 flip 2026-04-17: default TRUE apos Gate 1 PASS (peak 4.93GB <= 7.5GB budget)
# e Gate 2 PASS (Story 9.1.1 replay em 5 evals reais).
# Habilita load/unload explicito via ModelGPU context manager, liberando VRAM
# entre whisper → mediapipe → ML novos (9.3 Wav2Vec2 / 9.5 py-feat).
# Rollback explicito via env var MODEL_ORCHESTRATOR_ENABLED=false.
MODEL_ORCHESTRATOR_ENABLED = os.getenv("MODEL_ORCHESTRATOR_ENABLED", "true").lower() == "true"


def is_orchestrator_enabled() -> bool:
    """Helper testavel pra flag Story 9.2."""
    return os.getenv("MODEL_ORCHESTRATOR_ENABLED", "true").strip().lower() == "true"


# Feature flags Story 9.4 — prosody deep dive (CPU-only).
# Independentes entre si — rollout granular.
OPENSMILE_ENABLED = os.getenv("OPENSMILE_ENABLED", "false").lower() == "true"
PYANNOTE_VAD_ENABLED = os.getenv("PYANNOTE_VAD_ENABLED", "false").lower() == "true"


def is_opensmile_enabled() -> bool:
    """Helper testavel pra flag openSMILE eGeMAPS (Story 9.4)."""
    return os.getenv("OPENSMILE_ENABLED", "false").strip().lower() == "true"


def is_pyannote_vad_enabled() -> bool:
    """Helper testavel pra flag pyannote VAD (Story 9.4)."""
    return os.getenv("PYANNOTE_VAD_ENABLED", "false").strip().lower() == "true"


# Feature flag Story 9.3 — Wav2Vec2-Emotion ML (promove tonality 🟡 → 🟢).
# Default false — requer pip install -e ".[emotion]" + ativacao explicita.
TONALITY_ML_ENABLED = os.getenv("TONALITY_ML_ENABLED", "false").lower() == "true"


def is_tonality_ml_enabled() -> bool:
    """Helper testavel pra flag Wav2Vec2 emotion (Story 9.3)."""
    return os.getenv("TONALITY_ML_ENABLED", "false").strip().lower() == "true"


# Feature flag Story 10.1 — WavLM-base+ infra (Path 1 v2).
# Default false — feature extractor only, sem consumer atual.
# Clientes futuros: vocal_resonance dim, speaker style, custom VAD head Epic 11+.
WAVLM_EMOTION_ENABLED = os.getenv("WAVLM_EMOTION_ENABLED", "false").lower() == "true"


def is_wavlm_emotion_enabled() -> bool:
    """Helper testavel pra flag WavLM-base+ infra (Story 10.1).

    NOTA: WavLM atualmente NÃO substitui wav2vec2-emotion no tonality_analyzer
    (não há classifier emotion drop-in pra PT/EN). Story 10.1 disponibiliza
    infra; consumers em Epic 11+.
    """
    return os.getenv("WAVLM_EMOTION_ENABLED", "false").strip().lower() == "true"


# Feature flag Story 10.3 — Família narrativa + dim discourse_arc.
# Default false — quando ON: (1) discourse_arc_analyzer roda via Gemini,
# (2) family_scores.narrativa entra em overall_score com weighted_avg,
# (3) frontend exibe family narrativa no report.
# Quando OFF: zero chamadas Gemini, comportamento idêntico v0.7.0 (AC7).
NARRATIVE_FAMILY_ENABLED = os.getenv("NARRATIVE_FAMILY_ENABLED", "false").lower() == "true"

# Pesos família-família pro overall_score quando flag ON.
# Default PM signoff (Story 10.3): 0.6 técnica / 0.4 narrativa.
WEIGHT_TECNICA = float(os.getenv("WEIGHT_TECNICA", "0.6"))
WEIGHT_NARRATIVA = float(os.getenv("WEIGHT_NARRATIVA", "0.4"))


def is_narrative_family_enabled() -> bool:
    """Helper testavel pra flag Story 10.3 (família narrativa + discourse_arc).

    Quando false: discourse_arc não roda, family narrativa não entra em
    overall_score. Comportamento bate exato v0.7.0-calibrated-bench (AC7).
    """
    return os.getenv("NARRATIVE_FAMILY_ENABLED", "false").strip().lower() == "true"


# Feature flag Story 9.5 — py-feat FACS (20 AUs + 6 emocoes).
# Default false — requer pip install -e ".[facs]".
PYFEAT_ENABLED = os.getenv("PYFEAT_ENABLED", "false").lower() == "true"


def is_pyfeat_enabled() -> bool:
    """Helper testavel pra flag py-feat FACS (Story 9.5)."""
    return os.getenv("PYFEAT_ENABLED", "false").strip().lower() == "true"


# Feature flag Story 9.6 — Gemini Vision gesture semantic (UNICO pago ~$0.015/video).
# Default false + budget guard hard cap pra evitar runaway cost.
GESTURE_SEMANTIC_ENABLED = os.getenv("GESTURE_SEMANTIC_ENABLED", "false").lower() == "true"
GESTURE_SEMANTIC_MAX_COST_PER_EVAL = float(os.getenv("GESTURE_SEMANTIC_MAX_COST_PER_EVAL", "0.10"))
GESTURE_SEMANTIC_FPS = float(os.getenv("GESTURE_SEMANTIC_FPS", "0.5"))  # 1 frame/2s
GESTURE_SEMANTIC_MAX_FRAMES = int(os.getenv("GESTURE_SEMANTIC_MAX_FRAMES", "120"))
GEMINI_VISION_MODEL = os.getenv("GEMINI_VISION_MODEL", "gemini-2.5-flash")


def is_gesture_semantic_enabled() -> bool:
    """Helper testavel pra flag Gemini Vision (Story 9.6)."""
    return os.getenv("GESTURE_SEMANTIC_ENABLED", "false").strip().lower() == "true"


# Validação Story 10.3: pesos overall família-família somam 1.0 quando flag ON.
if NARRATIVE_FAMILY_ENABLED:
    _total = WEIGHT_TECNICA + WEIGHT_NARRATIVA
    if abs(_total - 1.0) > 0.001:
        raise ValueError(
            f"WEIGHT_TECNICA + WEIGHT_NARRATIVA deve somar 1.0, got {_total}. "
            f"Atual: tecnica={WEIGHT_TECNICA}, narrativa={WEIGHT_NARRATIVA}"
        )
