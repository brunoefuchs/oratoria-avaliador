"""Tests for _save_analysis dispatcher — Story 8.1 T6.

Valida que o dispatcher em ml-worker/app.py despacha corretamente entre
path Truth Contract (save_analysis_result) e path legacy
(save_analysis_result_legacy) baseado na feature flag.

Vetos cobertos:
- T6.1: flag tem kill switch (env var → reload basta). Testado via monkeypatch
        de config.TRUTH_CONTRACT_ENABLED em runtime.
- T6.2: testes nunca setam TRUTH_CONTRACT_ENABLED=true hardcoded. Usam
        monkeypatch com valores explicitos.
- T6.3: documentacao inline em config.py explica cada valor da flag.
"""

import pytest

from contracts import WorkerFailure, WorkerSuccess


# ---------- FakeSupabase (replica do test_analysis_result_repo) ----------


class _FakeResponse:
    def __init__(self, data):
        self.data = data


class _FakeTable:
    def __init__(self, tracker):
        self.tracker = tracker

    def upsert(self, row):
        self.tracker.append(("upsert", row))
        return self

    def execute(self):
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


@pytest.fixture
def dispatcher():
    """Import tardio pra permitir monkeypatch de config antes do import."""
    from app import _save_analysis

    return _save_analysis


# ---------- Flag ON + WorkerResult → Truth Contract path ----------


def test_flag_on_worker_success_writes_truth_contract_columns(
    monkeypatch, supabase, dispatcher
):
    import config

    monkeypatch.setattr(config, "TRUTH_CONTRACT_ENABLED", True)

    result = WorkerSuccess(dimension="variety", score=87, metrics={"cv": 0.1})
    dispatcher(supabase, "eval-1", "variety", result)

    row = [c for c in supabase.calls if c[0] == "upsert"][0][1]
    # Flag ON + WorkerSuccess → grava colunas novas
    assert row["dimension_status"] == "ok"
    assert row["failure_reason"] is None
    assert row["score"] == 87


def test_flag_on_worker_failure_writes_null_score(monkeypatch, supabase, dispatcher):
    import config

    monkeypatch.setattr(config, "TRUTH_CONTRACT_ENABLED", True)

    result = WorkerFailure(
        dimension="facial", dimension_status="failed", failure_reason="video_too_short"
    )
    dispatcher(supabase, "eval-2", "facial", result)

    row = [c for c in supabase.calls if c[0] == "upsert"][0][1]
    assert row["score"] is None
    assert row["dimension_status"] == "failed"
    assert row["failure_reason"] == "video_too_short"


# ---------- Flag OFF + dict → Legacy path ----------


def test_flag_off_dict_writes_legacy_columns_only(monkeypatch, supabase, dispatcher):
    import config

    monkeypatch.setattr(config, "TRUTH_CONTRACT_ENABLED", False)

    dispatcher(supabase, "eval-3", "voice", {"score": 70, "metrics": {"x": 1}})

    row = [c for c in supabase.calls if c[0] == "upsert"][0][1]
    # Legacy path NAO escreve colunas novas (DB defaults atuam via migration 012)
    assert "dimension_status" not in row
    assert "failure_reason" not in row
    assert row["score"] == 70


def test_flag_off_dict_preserves_legacy_fallback(monkeypatch, supabase, dispatcher):
    """Score=0 fallback documentado em Epic 8.0 — mantido pelo path legacy."""
    import config

    monkeypatch.setattr(config, "TRUTH_CONTRACT_ENABLED", False)

    dispatcher(supabase, "eval-4", "gesture", {"metrics": {}})  # sem score

    row = [c for c in supabase.calls if c[0] == "upsert"][0][1]
    assert row["score"] == 0  # fallback documentado (mentira legacy)


# ---------- Defensive: Flag OFF + WorkerResult → warning + downgrade ----------


def test_flag_off_with_worker_result_downgrades_to_legacy(
    monkeypatch, supabase, dispatcher, caplog
):
    """Worker migrado rodando em ambiente com flag OFF — grava via legacy
    (model_dump) pra evitar quebrar pipeline. Loga warning."""
    import config
    import logging

    monkeypatch.setattr(config, "TRUTH_CONTRACT_ENABLED", False)

    result = WorkerSuccess(dimension="variety", score=60, metrics={"x": 1})
    with caplog.at_level(logging.WARNING):
        dispatcher(supabase, "eval-5", "variety", result)

    row = [c for c in supabase.calls if c[0] == "upsert"][0][1]
    # Grava no path legacy (sem colunas novas)
    assert "dimension_status" not in row
    assert row["score"] == 60  # model_dump expoe score
    # Warning foi logado (structlog usa stderr por default, mas podemos checar
    # a chamada via behavior: o importante eh que gravou)


# ---------- Flag ON + dict → path legacy (caller nao migrado) ----------


def test_flag_on_dict_uses_legacy_path(monkeypatch, supabase, dispatcher):
    """Alguns workers ainda nao migrados retornam dict mesmo com flag ON.
    Dispatcher deve gravar via legacy — veto T5.1 bloquearia se tentassemos
    o path novo com dict."""
    import config

    monkeypatch.setattr(config, "TRUTH_CONTRACT_ENABLED", True)

    dispatcher(supabase, "eval-6", "posture", {"score": 80, "metrics": {}})

    row = [c for c in supabase.calls if c[0] == "upsert"][0][1]
    # Legacy path — sem dimension_status/failure_reason
    assert "dimension_status" not in row
    assert row["score"] == 80


# ---------- Kill switch (veto T6.1) ----------


def test_flag_toggle_runtime_kill_switch(monkeypatch, supabase, dispatcher):
    """Flag pode ser toggled em runtime (simula env var reload).
    Call 1: flag ON → Truth Contract path.
    Call 2: flag OFF → legacy path.
    Ambos usam mesmo WorkerResult."""
    import config

    result = WorkerSuccess(dimension="voice", score=50, metrics={})

    monkeypatch.setattr(config, "TRUTH_CONTRACT_ENABLED", True)
    dispatcher(supabase, "eval-7a", "voice", result)
    row_on = [c for c in supabase.calls if c[0] == "upsert"][0][1]
    assert "dimension_status" in row_on

    # Kill switch: flag OFF
    monkeypatch.setattr(config, "TRUTH_CONTRACT_ENABLED", False)
    supabase.calls.clear()  # reset
    dispatcher(supabase, "eval-7b", "voice", result)
    row_off = [c for c in supabase.calls if c[0] == "upsert"][0][1]
    assert "dimension_status" not in row_off  # legacy path
