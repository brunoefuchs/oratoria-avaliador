"""Tests for Story 8.2 — Truth Contract migration of 6 scoring workers.

Cobre:
- Cada worker: analyze_X() retorna WorkerSuccess ou WorkerFailure (nao dict)
- Identity: score=50 fake REMOVIDO (empty transcript → score=None/WorkerFailure)
- Legacy: analyze_X_legacy() ainda retorna dict
- Exception captura: analyze_X() nunca propaga, retorna WorkerFailure(crashed)
"""

import pytest

from contracts import WorkerFailure, WorkerResult, WorkerSuccess


# ==============================================================================
# POSTURE
# ==============================================================================


class TestPostureMigration:
    def test_analyze_posture_returns_worker_result(self, monkeypatch):
        """analyze_posture() retorna WorkerResult (nao dict)."""
        from workers import posture_analyzer

        def fake_compute(video_path):
            return {"score": 75, "confidence": "high", "metrics": {"alignment_score": 80}}

        monkeypatch.setattr(posture_analyzer, "_compute_posture_metrics", fake_compute)
        result = posture_analyzer.analyze_posture("fake_video.mp4")
        assert isinstance(result, (WorkerSuccess, WorkerFailure))
        assert not isinstance(result, dict)

    def test_analyze_posture_success_values(self, monkeypatch):
        from workers import posture_analyzer

        def fake_compute(video_path):
            return {"score": 75, "confidence": "high", "metrics": {"alignment_score": 80}}

        monkeypatch.setattr(posture_analyzer, "_compute_posture_metrics", fake_compute)
        result = posture_analyzer.analyze_posture("fake_video.mp4")
        assert isinstance(result, WorkerSuccess)
        assert result.dimension == "posture"
        assert result.score == 75

    def test_analyze_posture_failure_propagates(self, monkeypatch):
        from workers import posture_analyzer

        def fake_compute(video_path):
            return {"score": 0, "confidence": "failed", "metrics": {}}

        monkeypatch.setattr(posture_analyzer, "_compute_posture_metrics", fake_compute)
        result = posture_analyzer.analyze_posture("fake_video.mp4")
        assert isinstance(result, WorkerFailure)
        assert result.score is None

    def test_analyze_posture_exception_captured(self, monkeypatch):
        from workers import posture_analyzer

        def boom(video_path):
            raise RuntimeError("simulated crash in posture")

        monkeypatch.setattr(posture_analyzer, "_compute_posture_metrics", boom)
        result = posture_analyzer.analyze_posture("fake_video.mp4")
        assert isinstance(result, WorkerFailure)
        assert result.dimension_status == "crashed"
        assert "RuntimeError" in result.failure_reason

    def test_analyze_posture_legacy_returns_dict(self, monkeypatch):
        """analyze_posture_legacy() ainda retorna dict."""
        from workers import posture_analyzer

        def fake_compute(video_path):
            return {"score": 75, "confidence": "high", "metrics": {}}

        monkeypatch.setattr(posture_analyzer, "_compute_posture_metrics", fake_compute)
        result = posture_analyzer.analyze_posture_legacy("fake_video.mp4")
        assert isinstance(result, dict)
        assert "score" in result


# ==============================================================================
# GESTURE
# ==============================================================================


class TestGestureMigration:
    def test_analyze_gestures_returns_worker_result(self, monkeypatch):
        from workers import gesture_analyzer

        def fake_compute(video_path):
            return {"score": 68, "confidence": "high", "metrics": {"eye_contact_pct": 80}}

        monkeypatch.setattr(gesture_analyzer, "_compute_gesture_metrics", fake_compute)
        result = gesture_analyzer.analyze_gestures("fake_video.mp4")
        assert isinstance(result, (WorkerSuccess, WorkerFailure))
        assert not isinstance(result, dict)

    def test_analyze_gestures_success_values(self, monkeypatch):
        from workers import gesture_analyzer

        def fake_compute(video_path):
            return {"score": 68, "confidence": "high", "metrics": {"eye_contact_pct": 80}}

        monkeypatch.setattr(gesture_analyzer, "_compute_gesture_metrics", fake_compute)
        result = gesture_analyzer.analyze_gestures("fake_video.mp4")
        assert isinstance(result, WorkerSuccess)
        assert result.dimension == "gesture"
        assert result.score == 68

    def test_analyze_gestures_exception_captured(self, monkeypatch):
        from workers import gesture_analyzer

        def boom(video_path):
            raise ValueError("simulated crash in gesture")

        monkeypatch.setattr(gesture_analyzer, "_compute_gesture_metrics", boom)
        result = gesture_analyzer.analyze_gestures("fake_video.mp4")
        assert isinstance(result, WorkerFailure)
        assert result.dimension_status == "crashed"

    def test_analyze_gestures_legacy_returns_dict(self, monkeypatch):
        from workers import gesture_analyzer

        def fake_compute(video_path):
            return {"score": 68, "confidence": "high", "metrics": {}}

        monkeypatch.setattr(gesture_analyzer, "_compute_gesture_metrics", fake_compute)
        result = gesture_analyzer.analyze_gestures_legacy("fake_video.mp4")
        assert isinstance(result, dict)
        assert "score" in result


# ==============================================================================
# VOICE
# ==============================================================================


@pytest.fixture
def voice_inputs():
    transcription = {
        "full_text": "Ola mundo",
        "words": [
            {"word": "Ola", "start": 0.0, "end": 0.3, "confidence": 0.9},
            {"word": "mundo", "start": 0.4, "end": 0.8, "confidence": 0.95},
        ],
        "language": "pt-BR",
        "model": "medium",
    }
    prosody = {
        "pitch_mean_hz": 150.0,
        "pitch_std_hz": 20.0,
        "pitch_min_hz": 100.0,
        "pitch_max_hz": 250.0,
        "pitch_range_semitones": 16.0,
        "cv_pitch": 0.12,
        "intensity_mean_db": 65.0,
        "intensity_std_db": 5.0,
        "intensity_min_db": 50.0,
        "intensity_max_db": 75.0,
        "cv_volume": 0.08,
        "volume_base_1_10": 6.5,
        "speech_silence_ratio": 0.8,
        "audio_duration_seconds": 60.0,
        "pitch_por_janela": [150.0, 155.0, 148.0, 160.0],
        "volume_por_janela": [65.0, 63.0, 67.0, 64.0],
        "num_janelas": 4,
        "janela_size_seconds": 15.0,
    }
    return transcription, prosody


class TestVoiceMigration:
    def test_analyze_voice_returns_worker_result(self, monkeypatch, voice_inputs):
        from workers import voice_analyzer

        transcription, prosody = voice_inputs

        def fake_compute(t, p):
            return {"score": 72, "confidence": "high", "metrics": {"wpm": 145}}

        monkeypatch.setattr(voice_analyzer, "_compute_voice_metrics", fake_compute)
        result = voice_analyzer.analyze_voice(transcription, prosody)
        assert isinstance(result, (WorkerSuccess, WorkerFailure))
        assert not isinstance(result, dict)

    def test_analyze_voice_success_values(self, monkeypatch, voice_inputs):
        from workers import voice_analyzer

        transcription, prosody = voice_inputs

        def fake_compute(t, p):
            return {"score": 72, "confidence": "high", "metrics": {"wpm": 145}}

        monkeypatch.setattr(voice_analyzer, "_compute_voice_metrics", fake_compute)
        result = voice_analyzer.analyze_voice(transcription, prosody)
        assert isinstance(result, WorkerSuccess)
        assert result.dimension == "voice"
        assert result.score == 72

    def test_analyze_voice_exception_captured(self, monkeypatch, voice_inputs):
        from workers import voice_analyzer

        transcription, prosody = voice_inputs

        def boom(t, p):
            raise RuntimeError("boom in voice")

        monkeypatch.setattr(voice_analyzer, "_compute_voice_metrics", boom)
        result = voice_analyzer.analyze_voice(transcription, prosody)
        assert isinstance(result, WorkerFailure)
        assert result.dimension_status == "crashed"

    def test_analyze_voice_legacy_returns_dict(self, monkeypatch, voice_inputs):
        from workers import voice_analyzer

        transcription, prosody = voice_inputs

        def fake_compute(t, p):
            return {"score": 72, "confidence": "high", "metrics": {"wpm": 145}}

        monkeypatch.setattr(voice_analyzer, "_compute_voice_metrics", fake_compute)
        result = voice_analyzer.analyze_voice_legacy(transcription, prosody)
        assert isinstance(result, dict)
        assert "score" in result

    def test_calculate_voice_metrics_still_works(self, monkeypatch, voice_inputs):
        """calculate_voice_metrics() backwards compat alias ainda funciona."""
        from workers import voice_analyzer

        transcription, prosody = voice_inputs

        def fake_compute(t, p):
            return {"score": 72, "confidence": "high", "metrics": {"wpm": 145}}

        monkeypatch.setattr(voice_analyzer, "_compute_voice_metrics", fake_compute)
        result = voice_analyzer.calculate_voice_metrics(transcription, prosody)
        assert isinstance(result, dict)
        assert result["score"] == 72


# ==============================================================================
# FILLERS
# ==============================================================================


@pytest.fixture
def filler_transcription():
    return {
        "full_text": "Entao eu acho que tipo isso e muito importante ne",
        "words": [
            {"word": "Entao", "start": 0.0, "end": 0.3},
            {"word": "eu", "start": 0.4, "end": 0.5},
            {"word": "acho", "start": 0.6, "end": 0.8},
            {"word": "que", "start": 0.9, "end": 1.0},
            {"word": "tipo", "start": 1.1, "end": 1.3},
            {"word": "isso", "start": 1.4, "end": 1.6},
            {"word": "e", "start": 1.7, "end": 1.8},
            {"word": "muito", "start": 1.9, "end": 2.1},
            {"word": "importante", "start": 2.2, "end": 2.7},
            {"word": "ne", "start": 2.8, "end": 3.0},
        ],
    }


class TestFillersMigration:
    def test_analyze_fillers_returns_worker_result(self, monkeypatch, filler_transcription):
        from workers import filler_detector

        def fake_compute(t):
            return {"score": 80, "confidence": "high", "metrics": {"fillers_per_minute": 2.0}}

        monkeypatch.setattr(filler_detector, "_compute_filler_metrics", fake_compute)
        result = filler_detector.analyze_fillers(filler_transcription)
        assert isinstance(result, (WorkerSuccess, WorkerFailure))
        assert not isinstance(result, dict)

    def test_analyze_fillers_success_values(self, monkeypatch, filler_transcription):
        from workers import filler_detector

        def fake_compute(t):
            return {"score": 80, "confidence": "high", "metrics": {"fillers_per_minute": 2.0}}

        monkeypatch.setattr(filler_detector, "_compute_filler_metrics", fake_compute)
        result = filler_detector.analyze_fillers(filler_transcription)
        assert isinstance(result, WorkerSuccess)
        assert result.dimension == "fillers"
        assert result.score == 80

    def test_analyze_fillers_exception_captured(self, monkeypatch, filler_transcription):
        from workers import filler_detector

        def boom(t):
            raise RuntimeError("boom in fillers")

        monkeypatch.setattr(filler_detector, "_compute_filler_metrics", boom)
        result = filler_detector.analyze_fillers(filler_transcription)
        assert isinstance(result, WorkerFailure)
        assert result.dimension_status == "crashed"

    def test_detect_fillers_legacy_returns_dict(self, monkeypatch, filler_transcription):
        """detect_fillers_legacy() ainda retorna dict."""
        from workers import filler_detector

        def fake_compute(t):
            return {"score": 80, "confidence": "high", "metrics": {}}

        monkeypatch.setattr(filler_detector, "_compute_filler_metrics", fake_compute)
        result = filler_detector.detect_fillers_legacy(filler_transcription)
        assert isinstance(result, dict)
        assert "score" in result

    def test_detect_fillers_alias_returns_dict(self, monkeypatch, filler_transcription):
        """detect_fillers() backwards compat alias ainda retorna dict."""
        from workers import filler_detector

        def fake_compute(t):
            return {"score": 80, "confidence": "high", "metrics": {}}

        monkeypatch.setattr(filler_detector, "_compute_filler_metrics", fake_compute)
        result = filler_detector.detect_fillers(filler_transcription)
        assert isinstance(result, dict)
        assert "score" in result


# ==============================================================================
# ARCHETYPES
# ==============================================================================


class TestArchetypesMigration:
    def test_analyze_archetypes_returns_worker_result(self, monkeypatch):
        from workers import archetype_classifier

        def fake_compute(audio_path):
            return {
                "score": 65,
                "confidence": "high",
                "metrics": {"arquetipo_dominante": "educador"},
            }

        monkeypatch.setattr(archetype_classifier, "_compute_archetype_metrics", fake_compute)
        result = archetype_classifier.analyze_archetypes("fake_audio.wav")
        assert isinstance(result, (WorkerSuccess, WorkerFailure))
        assert not isinstance(result, dict)

    def test_analyze_archetypes_success_values(self, monkeypatch):
        from workers import archetype_classifier

        def fake_compute(audio_path):
            return {
                "score": 65,
                "confidence": "high",
                "metrics": {"arquetipo_dominante": "educador"},
            }

        monkeypatch.setattr(archetype_classifier, "_compute_archetype_metrics", fake_compute)
        result = archetype_classifier.analyze_archetypes("fake_audio.wav")
        assert isinstance(result, WorkerSuccess)
        assert result.dimension == "archetypes"
        assert result.score == 65

    def test_analyze_archetypes_exception_captured(self, monkeypatch):
        from workers import archetype_classifier

        def boom(audio_path):
            raise RuntimeError("boom in archetypes")

        monkeypatch.setattr(archetype_classifier, "_compute_archetype_metrics", boom)
        result = archetype_classifier.analyze_archetypes("fake_audio.wav")
        assert isinstance(result, WorkerFailure)
        assert result.dimension_status == "crashed"

    def test_classify_archetypes_legacy_returns_dict(self, monkeypatch):
        """classify_archetypes_legacy() ainda retorna dict."""
        from workers import archetype_classifier

        def fake_compute(audio_path):
            return {"score": 65, "confidence": "high", "metrics": {}}

        monkeypatch.setattr(archetype_classifier, "_compute_archetype_metrics", fake_compute)
        result = archetype_classifier.classify_archetypes_legacy("fake_audio.wav")
        assert isinstance(result, dict)
        assert "score" in result

    def test_classify_archetypes_alias_returns_dict(self, monkeypatch):
        """classify_archetypes() backwards compat alias ainda retorna dict."""
        from workers import archetype_classifier

        def fake_compute(audio_path):
            return {"score": 65, "confidence": "high", "metrics": {}}

        monkeypatch.setattr(archetype_classifier, "_compute_archetype_metrics", fake_compute)
        result = archetype_classifier.classify_archetypes("fake_audio.wav")
        assert isinstance(result, dict)
        assert "score" in result


# ==============================================================================
# IDENTITY — CRITICAL: score=50 fake bug fix
# ==============================================================================


class TestIdentityMigration:
    def test_analyze_identity_tc_returns_worker_result(self, monkeypatch):
        """analyze_identity_tc() retorna WorkerResult (nao dict)."""
        from workers import identity_analyzer

        transcription = {
            "full_text": "Eu sei que funciona assim, vamos la",
            "words": [{"word": "Eu", "start": 0.0, "end": 0.2}],
        }

        def fake_compute(t):
            return {"score": 70, "confidence": "high", "diagnostico": "identidade_media"}

        monkeypatch.setattr(identity_analyzer, "_compute_identity_metrics", fake_compute)
        result = identity_analyzer.analyze_identity_tc(transcription)
        assert isinstance(result, (WorkerSuccess, WorkerFailure))
        assert not isinstance(result, dict)

    def test_analyze_identity_tc_success_values(self, monkeypatch):
        from workers import identity_analyzer

        transcription = {"full_text": "Eu sei que funciona assim", "words": []}

        def fake_compute(t):
            return {"score": 70, "confidence": "high", "diagnostico": "identidade_media"}

        monkeypatch.setattr(identity_analyzer, "_compute_identity_metrics", fake_compute)
        result = identity_analyzer.analyze_identity_tc(transcription)
        assert isinstance(result, WorkerSuccess)
        assert result.dimension == "identity"
        assert result.score == 70

    def test_score_50_fake_is_gone_empty_transcript(self):
        """CRITICAL BUG FIX: score=50 fake removido.

        Empty transcript deve retornar score=None + confidence="failed"
        em vez do antigo score=50 hardcoded.
        """
        from workers.identity_analyzer import _compute_identity_metrics

        result = _compute_identity_metrics({"full_text": "", "words": []})
        # Bug antigo: score=50 hardcoded mesmo sem dados
        # Correto: score=None + confidence="failed"
        assert result.get("score") is None, (
            f"score=50 fake nao foi removido! Retornou score={result.get('score')}"
        )
        assert result.get("confidence") == "failed"
        assert result.get("failure_reason") is not None

    def test_score_50_fake_via_tc_path(self):
        """TC path com transcript vazio retorna WorkerFailure, nao WorkerSuccess(score=50)."""
        from workers.identity_analyzer import analyze_identity_tc

        result = analyze_identity_tc({"full_text": "", "words": []})
        assert isinstance(result, WorkerFailure), (
            f"Esperado WorkerFailure para transcript vazio, mas recebeu {type(result).__name__}"
        )
        assert result.score is None

    def test_analyze_identity_tc_exception_captured(self, monkeypatch):
        from workers import identity_analyzer

        def boom(t):
            raise RuntimeError("boom in identity")

        monkeypatch.setattr(identity_analyzer, "_compute_identity_metrics", boom)
        result = identity_analyzer.analyze_identity_tc({"full_text": "teste", "words": []})
        assert isinstance(result, WorkerFailure)
        assert result.dimension_status == "crashed"

    def test_analyze_identity_legacy_returns_dict(self, monkeypatch):
        """analyze_identity_legacy() ainda retorna dict."""
        from workers import identity_analyzer

        def fake_compute(t):
            return {
                "score": 65,
                "confidence": "high",
                "diagnostico": "identidade_media",
                "vicios_emocionais": {},
                "total_vicios": 0,
                "autoridade_count": 3,
                "vitima_count": 1,
                "autoridade_ratio": 0.75,
                "exemplos": [],
            }

        monkeypatch.setattr(identity_analyzer, "_compute_identity_metrics", fake_compute)
        result = identity_analyzer.analyze_identity_legacy(
            {"full_text": "teste", "words": []}
        )
        assert isinstance(result, dict)
        assert "score" in result

    def test_analyze_identity_alias_returns_dict(self, monkeypatch):
        """analyze_identity() backwards compat alias ainda retorna dict."""
        from workers import identity_analyzer

        def fake_compute(t):
            return {
                "score": 65,
                "confidence": "high",
                "diagnostico": "identidade_media",
                "vicios_emocionais": {},
                "total_vicios": 0,
                "autoridade_count": 3,
                "vitima_count": 1,
                "autoridade_ratio": 0.75,
                "exemplos": [],
            }

        monkeypatch.setattr(identity_analyzer, "_compute_identity_metrics", fake_compute)
        result = identity_analyzer.analyze_identity({"full_text": "teste", "words": []})
        assert isinstance(result, dict)
        assert "score" in result


# ==============================================================================
# CROSS-WORKER: wrap_worker_result integration
# ==============================================================================


class TestWrapWorkerResultIntegration:
    """Verifica que wrap_worker_result mapeia corretamente os casos basicos."""

    def test_success_maps_score(self):
        from workers._truth_contract_helpers import wrap_worker_result

        def compute():
            return {"score": 85, "confidence": "high", "metrics": {"x": 1}}

        result = wrap_worker_result("posture", compute)
        assert isinstance(result, WorkerSuccess)
        assert result.score == 85
        assert result.dimension == "posture"

    def test_failed_confidence_maps_to_failure(self):
        from workers._truth_contract_helpers import wrap_worker_result

        def compute():
            return {"score": 0, "confidence": "failed", "metrics": {}}

        result = wrap_worker_result("posture", compute)
        assert isinstance(result, WorkerFailure)
        assert result.score is None

    def test_none_score_maps_to_insufficient_data(self):
        from workers._truth_contract_helpers import wrap_worker_result

        def compute():
            return {"score": None, "confidence": "failed", "failure_reason": "no data"}

        result = wrap_worker_result("posture", compute)
        assert isinstance(result, WorkerFailure)
        assert result.score is None

    def test_exception_maps_to_crashed(self):
        from workers._truth_contract_helpers import wrap_worker_result

        def compute():
            raise ValueError("boom")

        result = wrap_worker_result("posture", compute)
        assert isinstance(result, WorkerFailure)
        assert result.dimension_status == "crashed"
        assert "ValueError" in result.failure_reason
