"""Tests for repositories.analysis_result_repo — Story 8.1 T5.

Vetos cobertos:
- T5.1: save_analysis_result aceita apenas WorkerResult (TypeError em dict)
- T5.2: save_analysis_result_legacy existe pra flag OFF (path separado,
         testado com dict legacy replicando comportamento documentado)
"""

import pytest

from contracts import WorkerFailure, WorkerSuccess
from repositories.analysis_result_repo import (
    save_analysis_result,
    save_analysis_result_legacy,
)

# ---------- Fake Supabase client ----------


class _FakeResponse:
    def __init__(self, data):
        self.data = data


class _FakeTable:
    """Captura payloads enviados pra supabase.table().upsert().execute()."""

    def __init__(self, tracker):
        self.tracker = tracker

    def upsert(self, row):
        self.tracker.append(("upsert", row))
        return self

    def execute(self):
        # Simula Supabase devolvendo o row persistido com um id gerado
        last_row = self.tracker[-1][1]
        return _FakeResponse([{**last_row, "id": "fake-uuid-123"}])


class _FakeSupabase:
    def __init__(self):
        self.calls = []

    def table(self, name):
        self.calls.append(("table", name))
        return _FakeTable(self.calls)


@pytest.fixture
def supabase():
    return _FakeSupabase()


# ---------- save_analysis_result (Truth Contract path) ----------


def test_save_success_writes_all_truth_contract_columns(supabase):
    result = WorkerSuccess(
        dimension="variety",
        score=87,
        metrics={"cv_volume": 0.12},
    )
    save_analysis_result(supabase, "eval-1", result)

    # Encontra o upsert
    upsert_calls = [c for c in supabase.calls if c[0] == "upsert"]
    assert len(upsert_calls) == 1
    row = upsert_calls[0][1]

    assert row["evaluation_id"] == "eval-1"
    assert row["dimension"] == "variety"
    assert row["score"] == 87
    assert row["dimension_status"] == "ok"
    assert row["failure_reason"] is None
    assert row["metrics"] == {"cv_volume": 0.12}
    # Legacy confidence mantido pra consumers antigos
    assert row["confidence"] == "high"


def test_save_failure_writes_null_score_and_reason(supabase):
    result = WorkerFailure(
        dimension="facial",
        dimension_status="failed",
        failure_reason="video_too_short",
    )
    save_analysis_result(supabase, "eval-2", result)

    row = [c for c in supabase.calls if c[0] == "upsert"][0][1]

    assert row["evaluation_id"] == "eval-2"
    assert row["dimension"] == "facial"
    assert row["score"] is None
    assert row["dimension_status"] == "failed"
    assert row["failure_reason"] == "video_too_short"
    # Legacy: aggregator antigo reconhece 'failed'
    assert row["confidence"] == "failed"


def test_save_failure_preserves_metrics(supabase):
    result = WorkerFailure(
        dimension="voice",
        dimension_status="insufficient_data",
        failure_reason="audio under 5s",
        metrics={"audio_duration_s": 3.2},
    )
    save_analysis_result(supabase, "eval-3", result)
    row = [c for c in supabase.calls if c[0] == "upsert"][0][1]
    assert row["metrics"] == {"audio_duration_s": 3.2}


def test_save_rejects_dict_veto_t51(supabase):
    """Veto T5.1: save_analysis_result nao aceita dict solto."""
    legacy_dict = {"score": 80, "metrics": {}, "confidence": "high"}
    with pytest.raises(TypeError) as exc_info:
        save_analysis_result(supabase, "eval-4", legacy_dict)
    assert "WorkerResult" in str(exc_info.value)
    assert "legacy" in str(exc_info.value).lower()
    # E garante que nada foi escrito (falha antes de chamar supabase)
    assert not any(c[0] == "upsert" for c in supabase.calls)


def test_save_rejects_none(supabase):
    with pytest.raises(TypeError):
        save_analysis_result(supabase, "eval-5", None)


def test_save_success_returns_persisted_row(supabase):
    result = WorkerSuccess(dimension="voice", score=75, metrics={})
    row = save_analysis_result(supabase, "eval-6", result)
    # FakeSupabase retorna {...row, id: 'fake-uuid-123'}
    assert row["id"] == "fake-uuid-123"
    assert row["score"] == 75


def test_save_uses_upsert_not_insert(supabase):
    """Workers podem re-rodar — upsert evita conflito em UNIQUE(eval, dim)."""
    result = WorkerSuccess(dimension="gesture", score=60, metrics={})
    save_analysis_result(supabase, "eval-7", result)
    ops = [c[0] for c in supabase.calls]
    assert "upsert" in ops
    assert "insert" not in ops


# ---------- save_analysis_result_legacy (feature flag OFF) ----------


def test_legacy_accepts_dict(supabase):
    save_analysis_result_legacy(
        supabase,
        "eval-8",
        "variety",
        {"score": 65, "metrics": {"foo": "bar"}, "confidence": "medium"},
    )
    row = [c for c in supabase.calls if c[0] == "upsert"][0][1]
    assert row["score"] == 65
    assert row["metrics"] == {"foo": "bar"}
    assert row["confidence"] == "medium"


def test_legacy_preserves_score_zero_fallback(supabase):
    """Legacy REPLICA comportamento documentado em Epic 8.0 — score=0 fallback.
    NAO eh bug desta story corrigir; eh documentacao do bug que Truth Contract
    corrige via path novo (save_analysis_result)."""
    save_analysis_result_legacy(supabase, "eval-9", "voice", {"metrics": {}})
    row = [c for c in supabase.calls if c[0] == "upsert"][0][1]
    # Score vira 0 quando ausente — o bug que 8.1 corrige no path novo
    assert row["score"] == 0


def test_legacy_does_not_write_new_columns(supabase):
    """Legacy path NAO escreve dimension_status/failure_reason — deixa DB usar
    defaults ('ok' + NULL via migration 012). Isso permite backfill natural
    enquanto workers nao sao migrados."""
    save_analysis_result_legacy(supabase, "eval-10", "fillers", {"score": 80, "metrics": {}})
    row = [c for c in supabase.calls if c[0] == "upsert"][0][1]
    assert "dimension_status" not in row
    assert "failure_reason" not in row


def test_save_returns_payload_when_supabase_empty():
    """Quando Supabase retorna response.data vazio, retorna row construido."""

    class _EmptyTable:
        def upsert(self, row):
            self._row = row
            return self

        def execute(self):
            return _FakeResponse([])

    class _EmptySupa:
        def table(self, name):
            return _EmptyTable()

    result = WorkerSuccess(dimension="variety", score=50, metrics={})
    row = save_analysis_result(_EmptySupa(), "eval-empty", result)
    assert row["score"] == 50
    assert "id" not in row


def test_legacy_returns_payload_when_supabase_empty():
    class _EmptyTable:
        def upsert(self, row):
            return self

        def execute(self):
            return _FakeResponse([])

    class _EmptySupa:
        def table(self, name):
            return _EmptyTable()

    row = save_analysis_result_legacy(_EmptySupa(), "eval-e2", "voice", {"score": 30})
    assert row["score"] == 30
    assert "id" not in row


def test_legacy_metrics_fallback_to_full_dict(supabase):
    """Worker pode nao ter campo 'metrics' separado — cai pro dict inteiro."""
    save_analysis_result_legacy(
        supabase, "eval-11", "archetypes", {"score": 50, "extra_field": "x"}
    )
    row = [c for c in supabase.calls if c[0] == "upsert"][0][1]
    # Quando 'metrics' nao esta no dict, metrics = dict inteiro
    assert row["metrics"] == {"score": 50, "extra_field": "x"}
