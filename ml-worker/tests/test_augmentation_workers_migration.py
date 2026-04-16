"""Tests for Story 8.3 — Truth Contract migration of 6 augmentation workers.

Cobre:
- Cada worker: analyze_X() retorna WorkerSuccess ou WorkerFailure (nao dict)
- Cada worker: legacy path retorna dict
- disponivel=False → WorkerFailure(skipped)
- Exception capturada → WorkerFailure(crashed)
- Flag flip: config.TRUTH_CONTRACT_ENABLED default agora e True
"""

import pytest

from contracts import WorkerFailure, WorkerResult, WorkerSuccess


# ==============================================================================
# FACIAL
# ==============================================================================


class TestFacialMigration:
    def test_analyze_facial_returns_worker_result(self, monkeypatch):
        """analyze_facial() retorna WorkerResult (nao dict)."""
        from workers import facial_analyzer

        def fake_compute(video_path):
            return {
                "disponivel": True,
                "score": 72,
                "diagnostico": "expressao_equilibrada",
                "smile_frequency_percent": 35.0,
                "smile_variability": 0.01,
                "brow_raises_per_minute": 2.5,
                "eye_openness_stddev": 0.025,
                "emocional_texture": {"neutro_percent": 50, "positivo_percent": 40, "tenso_percent": 10},
                "feedback": "Variacao facial saudavel",
                "detection_pct": 95.0,
                "warnings": [],
            }

        monkeypatch.setattr(facial_analyzer, "_compute_facial_metrics", fake_compute)
        result = facial_analyzer.analyze_facial("fake_video.mp4")
        assert isinstance(result, (WorkerSuccess, WorkerFailure))
        assert not isinstance(result, dict)

    def test_analyze_facial_success_values(self, monkeypatch):
        from workers import facial_analyzer

        def fake_compute(video_path):
            return {
                "disponivel": True,
                "score": 72,
                "diagnostico": "expressao_equilibrada",
                "smile_frequency_percent": 35.0,
                "smile_variability": 0.01,
                "brow_raises_per_minute": 2.5,
                "eye_openness_stddev": 0.025,
                "emocional_texture": {},
                "feedback": "ok",
                "detection_pct": 95.0,
                "warnings": [],
            }

        monkeypatch.setattr(facial_analyzer, "_compute_facial_metrics", fake_compute)
        result = facial_analyzer.analyze_facial("fake_video.mp4")
        assert isinstance(result, WorkerSuccess)
        assert result.dimension == "facial"
        assert result.score == 72

    def test_analyze_facial_disponivel_false_is_failure(self, monkeypatch):
        """disponivel=False → WorkerFailure(skipped)."""
        from workers import facial_analyzer

        def fake_compute(video_path):
            return {
                "disponivel": False,
                "score": 0,
                "diagnostico": "indisponivel",
                "feedback": "Rosto nao detectado em frames suficientes",
                "detection_pct": 10.0,
                "warnings": ["rosto nao detectado"],
            }

        monkeypatch.setattr(facial_analyzer, "_compute_facial_metrics", fake_compute)
        result = facial_analyzer.analyze_facial("fake_video.mp4")
        assert isinstance(result, WorkerFailure)
        assert result.dimension_status == "skipped"
        assert result.score is None

    def test_analyze_facial_exception_captured(self, monkeypatch):
        from workers import facial_analyzer

        def boom(video_path):
            raise RuntimeError("simulated crash in facial")

        monkeypatch.setattr(facial_analyzer, "_compute_facial_metrics", boom)
        result = facial_analyzer.analyze_facial("fake_video.mp4")
        assert isinstance(result, WorkerFailure)
        assert result.dimension_status == "crashed"
        assert "RuntimeError" in result.failure_reason

    def test_analyze_facial_legacy_returns_dict(self, monkeypatch):
        """analyze_facial_legacy() retorna dict."""
        from workers import facial_analyzer

        def fake_compute(video_path):
            return {
                "disponivel": True,
                "score": 72,
                "diagnostico": "expressao_equilibrada",
                "smile_frequency_percent": 35.0,
                "smile_variability": 0.01,
                "brow_raises_per_minute": 2.5,
                "eye_openness_stddev": 0.025,
                "emocional_texture": {},
                "feedback": "ok",
                "detection_pct": 95.0,
                "warnings": [],
            }

        monkeypatch.setattr(facial_analyzer, "_compute_facial_metrics", fake_compute)
        result = facial_analyzer.analyze_facial_legacy("fake_video.mp4")
        assert isinstance(result, dict)
        assert result["disponivel"] is True
        assert result["score"] == 72


# ==============================================================================
# TONALITY
# ==============================================================================


class TestTonalityMigration:
    def test_analyze_tonality_returns_worker_result(self, monkeypatch):
        """analyze_tonality() retorna WorkerResult (nao dict)."""
        from workers import tonality_analyzer

        def fake_compute(audio_path):
            return {
                "disponivel": True,
                "score": 68,
                "diagnostico": "tonalidade_funcional",
                "vad_medio": {"valence": 0.3, "arousal": 0.5, "dominance": 0.4},
                "vad_temporal": [],
                "textura_distribuicao": {
                    "neutro": 40, "entusiasmado": 30, "confiante": 20,
                    "apatico": 5, "tenso": 5, "hesitante": 0,
                },
                "textura_dominante": "neutro",
                "feedback": "Variacao saudavel",
                "warnings": [],
            }

        monkeypatch.setattr(tonality_analyzer, "_compute_tonality_metrics", fake_compute)
        result = tonality_analyzer.analyze_tonality("fake_audio.wav")
        assert isinstance(result, (WorkerSuccess, WorkerFailure))
        assert not isinstance(result, dict)

    def test_analyze_tonality_success_values(self, monkeypatch):
        from workers import tonality_analyzer

        def fake_compute(audio_path):
            return {
                "disponivel": True,
                "score": 68,
                "diagnostico": "tonalidade_funcional",
                "vad_medio": {"valence": 0.3, "arousal": 0.5, "dominance": 0.4},
                "vad_temporal": [],
                "textura_distribuicao": {"neutro": 100, "entusiasmado": 0, "confiante": 0, "apatico": 0, "tenso": 0, "hesitante": 0},
                "textura_dominante": "neutro",
                "feedback": "ok",
                "warnings": [],
            }

        monkeypatch.setattr(tonality_analyzer, "_compute_tonality_metrics", fake_compute)
        result = tonality_analyzer.analyze_tonality("fake_audio.wav")
        assert isinstance(result, WorkerSuccess)
        assert result.dimension == "tonality"
        assert result.score == 68

    def test_analyze_tonality_disponivel_false_is_failure(self, monkeypatch):
        """disponivel=False → WorkerFailure(skipped)."""
        from workers import tonality_analyzer

        def fake_compute(audio_path):
            return {
                "disponivel": False,
                "score": 0,
                "diagnostico": "indisponivel",
                "feedback": "Audio muito curto",
                "warnings": ["audio muito curto"],
            }

        monkeypatch.setattr(tonality_analyzer, "_compute_tonality_metrics", fake_compute)
        result = tonality_analyzer.analyze_tonality("fake_audio.wav")
        assert isinstance(result, WorkerFailure)
        assert result.dimension_status == "skipped"
        assert result.score is None

    def test_analyze_tonality_exception_captured(self, monkeypatch):
        from workers import tonality_analyzer

        def boom(audio_path):
            raise ValueError("simulated crash in tonality")

        monkeypatch.setattr(tonality_analyzer, "_compute_tonality_metrics", boom)
        result = tonality_analyzer.analyze_tonality("fake_audio.wav")
        assert isinstance(result, WorkerFailure)
        assert result.dimension_status == "crashed"

    def test_analyze_tonality_legacy_returns_dict(self, monkeypatch):
        """analyze_tonality_legacy() retorna dict."""
        from workers import tonality_analyzer

        def fake_compute(audio_path):
            return {
                "disponivel": True,
                "score": 68,
                "diagnostico": "tonalidade_funcional",
                "vad_medio": {},
                "vad_temporal": [],
                "textura_distribuicao": {"neutro": 100, "entusiasmado": 0, "confiante": 0, "apatico": 0, "tenso": 0, "hesitante": 0},
                "textura_dominante": "neutro",
                "feedback": "ok",
                "warnings": [],
            }

        monkeypatch.setattr(tonality_analyzer, "_compute_tonality_metrics", fake_compute)
        result = tonality_analyzer.analyze_tonality_legacy("fake_audio.wav")
        assert isinstance(result, dict)
        assert result["disponivel"] is True
        assert result["score"] == 68


# ==============================================================================
# OPENING
# ==============================================================================


@pytest.fixture
def opening_inputs():
    transcription = {
        "full_text": "Ja parou para pensar por que 93% das pessoas tem medo de falar?",
        "words": [
            {"word": w, "start": i * 0.3, "end": (i + 1) * 0.3}
            for i, w in enumerate("Ja parou para pensar por que 93% das pessoas tem medo".split())
        ],
    }
    voice_metrics = {"volume_por_janela": [60.0, 65.0, 63.0]}
    return transcription, voice_metrics


class TestOpeningMigration:
    def test_analyze_opening_returns_worker_result(self, monkeypatch, opening_inputs):
        """analyze_opening() retorna WorkerResult (nao dict)."""
        from workers import opening_analyzer

        transcription, voice_metrics = opening_inputs

        def fake_compute(t, v, d):
            return {
                "disponivel": True,
                "score": 60,
                "diagnostico": "abertura_razoavel",
                "feedback": "Boa abertura",
                "tecnicas_detectadas": [],
                "tecnicas_ausentes": [],
                "opening_text": "ja parou para pensar",
                "opening_duration_seconds": 5.0,
            }

        monkeypatch.setattr(opening_analyzer, "_compute_opening_metrics", fake_compute)
        result = opening_analyzer.analyze_opening(transcription, voice_metrics, 60.0)
        assert isinstance(result, (WorkerSuccess, WorkerFailure))
        assert not isinstance(result, dict)

    def test_analyze_opening_success_values(self, monkeypatch, opening_inputs):
        from workers import opening_analyzer

        transcription, voice_metrics = opening_inputs

        def fake_compute(t, v, d):
            return {
                "disponivel": True,
                "score": 60,
                "diagnostico": "abertura_razoavel",
                "feedback": "ok",
                "tecnicas_detectadas": [],
                "tecnicas_ausentes": [],
                "opening_text": "ja parou",
                "opening_duration_seconds": 5.0,
            }

        monkeypatch.setattr(opening_analyzer, "_compute_opening_metrics", fake_compute)
        result = opening_analyzer.analyze_opening(transcription, voice_metrics, 60.0)
        assert isinstance(result, WorkerSuccess)
        assert result.dimension == "opening"
        assert result.score == 60

    def test_analyze_opening_disponivel_false_is_failure(self, monkeypatch, opening_inputs):
        """disponivel=False → WorkerFailure(skipped)."""
        from workers import opening_analyzer

        transcription, voice_metrics = opening_inputs

        def fake_compute(t, v, d):
            return {"disponivel": False, "motivo": "Video muito curto para analise de abertura"}

        monkeypatch.setattr(opening_analyzer, "_compute_opening_metrics", fake_compute)
        result = opening_analyzer.analyze_opening(transcription, voice_metrics, 5.0)
        assert isinstance(result, WorkerFailure)
        assert result.dimension_status == "skipped"
        assert result.score is None

    def test_analyze_opening_exception_captured(self, monkeypatch, opening_inputs):
        from workers import opening_analyzer

        transcription, voice_metrics = opening_inputs

        def boom(t, v, d):
            raise RuntimeError("boom in opening")

        monkeypatch.setattr(opening_analyzer, "_compute_opening_metrics", boom)
        result = opening_analyzer.analyze_opening(transcription, voice_metrics, 60.0)
        assert isinstance(result, WorkerFailure)
        assert result.dimension_status == "crashed"

    def test_analyze_opening_legacy_returns_dict(self, monkeypatch, opening_inputs):
        """analyze_opening_legacy() retorna dict."""
        from workers import opening_analyzer

        transcription, voice_metrics = opening_inputs

        def fake_compute(t, v, d):
            return {
                "disponivel": True,
                "score": 60,
                "diagnostico": "abertura_razoavel",
                "feedback": "ok",
                "tecnicas_detectadas": [],
                "tecnicas_ausentes": [],
                "opening_text": "ja parou",
                "opening_duration_seconds": 5.0,
            }

        monkeypatch.setattr(opening_analyzer, "_compute_opening_metrics", fake_compute)
        result = opening_analyzer.analyze_opening_legacy(transcription, voice_metrics, 60.0)
        assert isinstance(result, dict)
        assert result["disponivel"] is True
        assert result["score"] == 60


# ==============================================================================
# STORYTELLING
# ==============================================================================


@pytest.fixture
def storytelling_transcription():
    return {
        "full_text": (
            "Quando eu tinha 23 anos subi num palco pela primeira vez. "
            "A razao de eu estar te contando isso e porque voce tambem pode superar o medo. "
            "Comece hoje mesmo, o proximo passo e so dar o primeiro passo."
        ),
        "words": [{"word": "Quando", "start": 0.0, "end": 0.3}],
    }


class TestStorytellingMigration:
    def test_analyze_storytelling_returns_worker_result(self, monkeypatch, storytelling_transcription):
        """analyze_storytelling() retorna WorkerResult (nao dict)."""
        from workers import storytelling_analyzer

        def fake_compute(t, variety_metrics=None, opening_result=None):
            return {
                "disponivel": True,
                "score": 65,
                "diagnostico": "narrativa_solida",
                "bridge_sentence": {"detected": True, "count": 1, "excerpts": []},
                "opening_hook": {"type": "story", "strength": "strong"},
                "cta": {"detected": True, "excerpt": "comece hoje"},
                "chemicals": {"dopamine": {"detected": False, "examples": []}, "oxytocin": {"detected": False, "examples": []}, "endorphins": "not_yet_implemented", "cortisol_risk": {"detected": False, "reason": ""}},
                "suggestions": [],
            }

        monkeypatch.setattr(storytelling_analyzer, "_compute_storytelling_metrics", fake_compute)
        result = storytelling_analyzer.analyze_storytelling(storytelling_transcription)
        assert isinstance(result, (WorkerSuccess, WorkerFailure))
        assert not isinstance(result, dict)

    def test_analyze_storytelling_success_values(self, monkeypatch, storytelling_transcription):
        from workers import storytelling_analyzer

        def fake_compute(t, variety_metrics=None, opening_result=None):
            return {
                "disponivel": True,
                "score": 65,
                "diagnostico": "narrativa_solida",
                "bridge_sentence": {"detected": True, "count": 1, "excerpts": []},
                "opening_hook": {"type": "story", "strength": "strong"},
                "cta": {"detected": True, "excerpt": None},
                "chemicals": {"dopamine": {"detected": False, "examples": []}, "oxytocin": {"detected": False, "examples": []}, "endorphins": "not_yet_implemented", "cortisol_risk": {"detected": False, "reason": ""}},
                "suggestions": [],
            }

        monkeypatch.setattr(storytelling_analyzer, "_compute_storytelling_metrics", fake_compute)
        result = storytelling_analyzer.analyze_storytelling(storytelling_transcription)
        assert isinstance(result, WorkerSuccess)
        assert result.dimension == "storytelling"
        assert result.score == 65

    def test_analyze_storytelling_disponivel_false_is_failure(self, monkeypatch):
        """disponivel=False (transcript curto) → WorkerFailure(skipped)."""
        from workers import storytelling_analyzer

        def fake_compute(t, variety_metrics=None, opening_result=None):
            return {
                "disponivel": False,
                "score": 0,
                "diagnostico": "indisponivel",
                "suggestions": ["Transcript muito curto para analise narrativa"],
            }

        monkeypatch.setattr(storytelling_analyzer, "_compute_storytelling_metrics", fake_compute)
        result = storytelling_analyzer.analyze_storytelling({"full_text": "curto", "words": []})
        assert isinstance(result, WorkerFailure)
        assert result.dimension_status == "skipped"
        assert result.score is None

    def test_analyze_storytelling_exception_captured(self, monkeypatch, storytelling_transcription):
        from workers import storytelling_analyzer

        def boom(t, variety_metrics=None, opening_result=None):
            raise RuntimeError("boom in storytelling")

        monkeypatch.setattr(storytelling_analyzer, "_compute_storytelling_metrics", boom)
        result = storytelling_analyzer.analyze_storytelling(storytelling_transcription)
        assert isinstance(result, WorkerFailure)
        assert result.dimension_status == "crashed"

    def test_analyze_storytelling_legacy_returns_dict(self, monkeypatch, storytelling_transcription):
        """analyze_storytelling_legacy() retorna dict."""
        from workers import storytelling_analyzer

        def fake_compute(t, variety_metrics=None, opening_result=None):
            return {
                "disponivel": True,
                "score": 65,
                "diagnostico": "narrativa_solida",
                "bridge_sentence": {"detected": True, "count": 1, "excerpts": []},
                "opening_hook": {"type": "story", "strength": "strong"},
                "cta": {"detected": False, "excerpt": None},
                "chemicals": {"dopamine": {"detected": False, "examples": []}, "oxytocin": {"detected": False, "examples": []}, "endorphins": "not_yet_implemented", "cortisol_risk": {"detected": False, "reason": ""}},
                "suggestions": [],
            }

        monkeypatch.setattr(storytelling_analyzer, "_compute_storytelling_metrics", fake_compute)
        result = storytelling_analyzer.analyze_storytelling_legacy(storytelling_transcription)
        assert isinstance(result, dict)
        assert result["disponivel"] is True
        assert result["score"] == 65


# ==============================================================================
# TEMPORAL
# ==============================================================================


@pytest.fixture
def temporal_inputs():
    voice_result = {
        "metrics": {
            "audio_duration_seconds": 90.0,
            "pitch_por_janela": [150.0, 155.0, 148.0, 160.0, 152.0, 158.0],
            "volume_por_janela": [65.0, 63.0, 67.0, 64.0, 66.0, 65.0],
            "num_janelas": 6,
            "janela_size_seconds": 15.0,
        }
    }
    variety_result = {"metrics": {"trechos_monotonos": []}}
    filler_result = {"fillers": [], "clusters": []}
    return voice_result, variety_result, filler_result


class TestTemporalMigration:
    def test_analyze_temporal_returns_worker_result(self, monkeypatch, temporal_inputs):
        """analyze_temporal() retorna WorkerResult (nao dict)."""
        from workers import temporal_analyzer

        voice_result, variety_result, filler_result = temporal_inputs

        def fake_compute(vr, var, fr, duration_seconds):
            return {
                "disponivel": True,
                "por_terco": {
                    "abertura": {"label": "abertura", "score": 75, "pitch_medio": 150.0, "volume_medio": 65.0, "trechos_monotonos": 0, "fillers": 0, "clusters": 0},
                    "meio": {"label": "meio", "score": 70, "pitch_medio": 155.0, "volume_medio": 64.0, "trechos_monotonos": 0, "fillers": 0, "clusters": 0},
                    "fechamento": {"label": "fechamento", "score": 80, "pitch_medio": 158.0, "volume_medio": 65.0, "trechos_monotonos": 0, "fillers": 0, "clusters": 0},
                },
                "padrao": "crescente",
                "padrao_descricao": "Constroi energia",
                "duracao_terco_segundos": 30.0,
            }

        monkeypatch.setattr(temporal_analyzer, "_compute_temporal_metrics", fake_compute)
        result = temporal_analyzer.analyze_temporal(voice_result, variety_result, filler_result, 90.0)
        assert isinstance(result, (WorkerSuccess, WorkerFailure))
        assert not isinstance(result, dict)

    def test_analyze_temporal_success_values(self, monkeypatch, temporal_inputs):
        from workers import temporal_analyzer

        voice_result, variety_result, filler_result = temporal_inputs

        def fake_compute(vr, var, fr, duration_seconds):
            return {
                "disponivel": True,
                "por_terco": {
                    "abertura": {"label": "abertura", "score": 75},
                    "meio": {"label": "meio", "score": 70},
                    "fechamento": {"label": "fechamento", "score": 80},
                },
                "padrao": "crescente",
                "padrao_descricao": "Constroi energia",
                "duracao_terco_segundos": 30.0,
            }

        monkeypatch.setattr(temporal_analyzer, "_compute_temporal_metrics", fake_compute)
        result = temporal_analyzer.analyze_temporal(voice_result, variety_result, filler_result, 90.0)
        assert isinstance(result, WorkerSuccess)
        assert result.dimension == "temporal"
        # Score sintetico: media de 75+70+80 = 75
        assert result.score == 75

    def test_analyze_temporal_disponivel_false_is_failure(self, monkeypatch, temporal_inputs):
        """Video curto (< 45s) → WorkerFailure(skipped)."""
        from workers import temporal_analyzer

        voice_result, variety_result, filler_result = temporal_inputs

        def fake_compute(vr, var, fr, duration_seconds):
            return {"disponivel": False, "motivo": "Video muito curto para analise temporal (minimo 45s)"}

        monkeypatch.setattr(temporal_analyzer, "_compute_temporal_metrics", fake_compute)
        result = temporal_analyzer.analyze_temporal(voice_result, variety_result, filler_result, 30.0)
        assert isinstance(result, WorkerFailure)
        assert result.dimension_status == "skipped"
        assert result.score is None

    def test_analyze_temporal_exception_captured(self, monkeypatch, temporal_inputs):
        from workers import temporal_analyzer

        voice_result, variety_result, filler_result = temporal_inputs

        def boom(vr, var, fr, duration_seconds):
            raise RuntimeError("boom in temporal")

        monkeypatch.setattr(temporal_analyzer, "_compute_temporal_metrics", boom)
        result = temporal_analyzer.analyze_temporal(voice_result, variety_result, filler_result, 90.0)
        assert isinstance(result, WorkerFailure)
        assert result.dimension_status == "crashed"

    def test_analyze_temporal_legacy_returns_dict(self, monkeypatch, temporal_inputs):
        """analyze_temporal_legacy() retorna dict."""
        from workers import temporal_analyzer

        voice_result, variety_result, filler_result = temporal_inputs

        def fake_compute(vr, var, fr, duration_seconds):
            return {
                "disponivel": True,
                "por_terco": {},
                "padrao": "estavel",
                "padrao_descricao": "ok",
                "duracao_terco_segundos": 30.0,
            }

        monkeypatch.setattr(temporal_analyzer, "_compute_temporal_metrics", fake_compute)
        result = temporal_analyzer.analyze_temporal_legacy(voice_result, variety_result, filler_result, 90.0)
        assert isinstance(result, dict)
        assert result["disponivel"] is True


# ==============================================================================
# CONGRUENCE
# ==============================================================================


@pytest.fixture
def detailed_metrics_fixture():
    return {
        "voice": {
            "pitch_range_semitones": 12.0,
            "intensity_mean_db": 68.0,
            "wpm": 145.0,
        },
        "posture": {
            "open_posture_pct": 75.0,
        },
        "gesture": {
            "olhar_baixo_pct": 10.0,
            "gesticulation_pct": 60.0,
        },
    }


class TestCongruenceMigration:
    def test_analyze_congruence_returns_worker_result(self, monkeypatch, detailed_metrics_fixture):
        """analyze_congruence() retorna WorkerResult (nao dict)."""
        from workers import congruence_analyzer

        def fake_compute(dm):
            return {
                "score": 85,
                "diagnostico": "alta_congruencia",
                "contradicoes": [],
                "total_contradicoes": 0,
            }

        monkeypatch.setattr(congruence_analyzer, "_compute_congruence_metrics", fake_compute)
        result = congruence_analyzer.analyze_congruence(detailed_metrics_fixture)
        assert isinstance(result, (WorkerSuccess, WorkerFailure))
        assert not isinstance(result, dict)

    def test_analyze_congruence_success_values(self, monkeypatch, detailed_metrics_fixture):
        from workers import congruence_analyzer

        def fake_compute(dm):
            return {
                "score": 85,
                "diagnostico": "alta_congruencia",
                "contradicoes": [],
                "total_contradicoes": 0,
            }

        monkeypatch.setattr(congruence_analyzer, "_compute_congruence_metrics", fake_compute)
        result = congruence_analyzer.analyze_congruence(detailed_metrics_fixture)
        assert isinstance(result, WorkerSuccess)
        assert result.dimension == "congruence"
        assert result.score == 85

    def test_analyze_congruence_with_contradicoes(self, monkeypatch, detailed_metrics_fixture):
        """Contradicoes detectadas reduzem score mas ainda retorna WorkerSuccess."""
        from workers import congruence_analyzer

        def fake_compute(dm):
            return {
                "score": 73,
                "diagnostico": "congruencia_moderada",
                "contradicoes": [{"id": "entusiasmo_vs_postura", "descricao": "Voz entusiasmada mas postura fechada", "penalidade": 15}],
                "total_contradicoes": 1,
            }

        monkeypatch.setattr(congruence_analyzer, "_compute_congruence_metrics", fake_compute)
        result = congruence_analyzer.analyze_congruence(detailed_metrics_fixture)
        assert isinstance(result, WorkerSuccess)
        assert result.score == 73

    def test_analyze_congruence_exception_captured(self, monkeypatch, detailed_metrics_fixture):
        from workers import congruence_analyzer

        def boom(dm):
            raise RuntimeError("boom in congruence")

        monkeypatch.setattr(congruence_analyzer, "_compute_congruence_metrics", boom)
        result = congruence_analyzer.analyze_congruence(detailed_metrics_fixture)
        assert isinstance(result, WorkerFailure)
        assert result.dimension_status == "crashed"

    def test_analyze_congruence_legacy_returns_dict(self, monkeypatch, detailed_metrics_fixture):
        """analyze_congruence_legacy() retorna dict."""
        from workers import congruence_analyzer

        def fake_compute(dm):
            return {
                "score": 85,
                "diagnostico": "alta_congruencia",
                "contradicoes": [],
                "total_contradicoes": 0,
            }

        monkeypatch.setattr(congruence_analyzer, "_compute_congruence_metrics", fake_compute)
        result = congruence_analyzer.analyze_congruence_legacy(detailed_metrics_fixture)
        assert isinstance(result, dict)
        assert "score" in result
        assert result["score"] == 85


# ==============================================================================
# FLAG FLIP: default agora e True
# ==============================================================================


class TestFlagFlip:
    def test_truth_contract_enabled_default_is_true(self):
        """CRITICAL: default do TRUTH_CONTRACT_ENABLED agora e True (Story 8.3)."""
        import os

        # Garantir que env var nao esta setada
        env_val = os.environ.get("TRUTH_CONTRACT_ENABLED", "true")
        # Se nao esta setada, o default do config deve ser True
        assert env_val.lower() == "true", (
            f"TRUTH_CONTRACT_ENABLED default nao e 'true'. "
            f"Valor atual: {env_val}"
        )

    def test_config_truth_contract_default_true(self, monkeypatch):
        """config.TRUTH_CONTRACT_ENABLED e True quando env nao esta setada."""
        import importlib
        import os

        # Simular ambiente sem env var
        monkeypatch.delenv("TRUTH_CONTRACT_ENABLED", raising=False)

        import config as cfg

        importlib.reload(cfg)
        assert cfg.TRUTH_CONTRACT_ENABLED is True, (
            f"config.TRUTH_CONTRACT_ENABLED deveria ser True mas e {cfg.TRUTH_CONTRACT_ENABLED}"
        )

    def test_config_truth_contract_can_be_disabled_via_env(self, monkeypatch):
        """Kill switch: TRUTH_CONTRACT_ENABLED=false desabilita o contrato."""
        import importlib

        monkeypatch.setenv("TRUTH_CONTRACT_ENABLED", "false")

        import config as cfg

        importlib.reload(cfg)
        assert cfg.TRUTH_CONTRACT_ENABLED is False, (
            "Kill switch TRUTH_CONTRACT_ENABLED=false nao funcionou"
        )


# ==============================================================================
# CROSS-WORKER: disponivel pattern integration
# ==============================================================================


class TestDisponivePatternIntegration:
    """Verifica que o pattern disponivel:bool mapeia corretamente em todos os workers."""

    @pytest.mark.parametrize("module_name,func_name,args", [
        ("facial_analyzer", "analyze_facial", ("fake_video.mp4",)),
        ("tonality_analyzer", "analyze_tonality", ("fake_audio.wav",)),
        ("storytelling_analyzer", "analyze_storytelling", ({"full_text": "x" * 100, "words": []},)),
    ])
    def test_disponivel_false_always_gives_worker_failure(self, monkeypatch, module_name, func_name, args):
        """Para qualquer worker augmentation, disponivel=False → WorkerFailure."""
        import importlib

        module = importlib.import_module(f"workers.{module_name}")
        compute_fn_name = f"_compute_{module_name.replace('_analyzer', '').replace('_detector', '')}_metrics"

        def fake_compute(*a, **kw):
            return {
                "disponivel": False,
                "score": 0,
                "diagnostico": "indisponivel",
                "feedback": "indisponivel",
                "motivo": "indisponivel",
                "suggestions": ["indisponivel"],
                "warnings": ["indisponivel"],
            }

        if hasattr(module, compute_fn_name):
            monkeypatch.setattr(module, compute_fn_name, fake_compute)

        func = getattr(module, func_name)
        result = func(*args)
        assert isinstance(result, WorkerFailure), (
            f"{func_name} com disponivel=False deveria retornar WorkerFailure, "
            f"mas retornou {type(result).__name__}"
        )
        assert result.score is None
