"""Integration tests E2E — Story 8.1 Truth Contract Fundacao (T8).

Roda contra Supabase LOCAL via psycopg2 (SQL direto) pra validar:
- Migration 012 aplicou corretamente (colunas + constraints existem)
- INSERT com Truth Contract columns funciona
- CHECK constraint rejeita status invalido
- Coherence constraint rejeita ok+reason / failed+no-reason
- Legacy INSERT (sem colunas novas) usa defaults corretos
- Mix de rows Truth Contract + legacy coexistem

Vetos:
- T8.1: teste roda contra DB real (Supabase local via psycopg2, nao mock)
- T8.2: cleanup das rows criadas no teardown (DELETE CASCADE via eval row)

Pre-requisito:
- supabase start rodando (DB em 127.0.0.1:54322)
- Migration 012_truth_contract_fundacao.sql aplicada

Executar:
    pytest tests/test_truth_contract_e2e.py -v
"""

import json
import os
import uuid

import pytest

DB_URL = os.environ.get(
    "TEST_DB_URL",
    "postgresql://postgres:postgres@127.0.0.1:54322/postgres",
)

try:
    import psycopg2

    _conn_test = psycopg2.connect(DB_URL)
    _conn_test.close()
    _DB_AVAILABLE = True
except Exception:
    _DB_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not _DB_AVAILABLE,
    reason=f"Supabase local DB nao disponivel em {DB_URL}",
)


@pytest.fixture
def conn():
    c = psycopg2.connect(DB_URL)
    c.autocommit = True
    yield c
    c.close()


@pytest.fixture
def eval_id():
    return str(uuid.uuid4())


@pytest.fixture(autouse=True)
def setup_and_cleanup(conn, eval_id):
    """Cria evaluation-pai e limpa tudo no teardown (CASCADE)."""
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO evaluations (id, video_url, status) VALUES (%s, %s, %s)",
        (eval_id, "https://test.local/video.mp4", "processing"),
    )
    yield
    cur.execute("DELETE FROM evaluations WHERE id = %s", (eval_id,))


def _insert_analysis(conn, eval_id, dimension, **kwargs):
    """Helper: insere row em analysis_results com campos opcionais."""
    defaults = {
        "score": 80,
        "metrics": json.dumps({}),
        "confidence": "high",
    }
    defaults.update(kwargs)
    # Construct dynamic SQL based on what columns are passed
    cols = ["evaluation_id", "dimension"] + list(defaults.keys())
    vals = [eval_id, dimension] + list(defaults.values())
    placeholders = ", ".join(["%s"] * len(vals))
    col_names = ", ".join(cols)
    cur = conn.cursor()
    cur.execute(
        f"INSERT INTO analysis_results ({col_names}) VALUES ({placeholders})",
        vals,
    )


def _get_analysis(conn, eval_id, dimension):
    cur = conn.cursor()
    cur.execute(
        "SELECT score, dimension_status, failure_reason, confidence "
        "FROM analysis_results WHERE evaluation_id = %s AND dimension = %s",
        (eval_id, dimension),
    )
    row = cur.fetchone()
    if row:
        return {
            "score": row[0],
            "dimension_status": row[1],
            "failure_reason": row[2],
            "confidence": row[3],
        }
    return None


# ---------- Migration 012 validation ----------


def test_columns_exist(conn, eval_id):
    """Migration 012 adicionou dimension_status + failure_reason."""
    _insert_analysis(
        conn,
        eval_id,
        "variety",
        score=80,
        dimension_status="ok",
        failure_reason=None,
    )
    row = _get_analysis(conn, eval_id, "variety")
    assert row["dimension_status"] == "ok"
    assert row["failure_reason"] is None


def test_check_constraint_rejects_invalid_status(conn, eval_id):
    """CHECK bloqueia dimension_status nao canonico."""
    with pytest.raises(psycopg2.errors.CheckViolation):
        _insert_analysis(
            conn, eval_id, "variety", dimension_status="banana_invalid"
        )


def test_coherence_rejects_ok_with_reason(conn, eval_id):
    """Coherence: status='ok' com failure_reason NAO eh permitido."""
    with pytest.raises(psycopg2.errors.CheckViolation):
        _insert_analysis(
            conn,
            eval_id,
            "variety",
            dimension_status="ok",
            failure_reason="should not exist",
        )


def test_coherence_rejects_failed_without_reason(conn, eval_id):
    """Coherence: status='failed' SEM failure_reason NAO eh permitido."""
    with pytest.raises(psycopg2.errors.CheckViolation):
        _insert_analysis(
            conn,
            eval_id,
            "variety",
            score=None,
            dimension_status="failed",
            failure_reason=None,
        )


def test_failed_with_reason_allowed(conn, eval_id):
    """Happy path failure: status='failed' COM reason eh valido."""
    _insert_analysis(
        conn,
        eval_id,
        "variety",
        score=None,
        confidence="failed",
        dimension_status="failed",
        failure_reason="video_too_short",
    )
    row = _get_analysis(conn, eval_id, "variety")
    assert row["score"] is None
    assert row["dimension_status"] == "failed"
    assert row["failure_reason"] == "video_too_short"


def test_all_failure_statuses_accepted(conn, eval_id):
    """Todos os 4 status de falha sao aceitos pelo CHECK."""
    for i, status in enumerate(["failed", "skipped", "insufficient_data", "crashed"]):
        dim = f"variety"  # unique constraint por (eval_id, dim), usar dims diferentes
        dims = ["variety", "voice", "gesture", "posture"]
        _insert_analysis(
            conn,
            eval_id,
            dims[i],
            score=None,
            confidence="failed",
            dimension_status=status,
            failure_reason=f"test_{status}",
        )
    # Verifica que 4 rows foram criadas
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM analysis_results WHERE evaluation_id = %s",
        (eval_id,),
    )
    assert cur.fetchone()[0] == 4


# ---------- Legacy coexistence ----------


def test_legacy_insert_uses_db_defaults(conn, eval_id):
    """INSERT sem colunas novas → DB defaults atuam (ok + NULL)."""
    _insert_analysis(conn, eval_id, "posture", score=72)
    row = _get_analysis(conn, eval_id, "posture")
    assert row["score"] == 72
    assert row["dimension_status"] == "ok"  # DB default
    assert row["failure_reason"] is None  # DB default


def test_mixed_truth_contract_and_legacy_coexist(conn, eval_id):
    """Variety (Truth Contract) + posture (legacy) coexistem na mesma evaluation."""
    # Truth Contract row
    _insert_analysis(
        conn,
        eval_id,
        "variety",
        score=85,
        dimension_status="ok",
        failure_reason=None,
    )
    # Legacy row (sem colunas novas)
    _insert_analysis(conn, eval_id, "posture", score=70)

    # Query ambas
    cur = conn.cursor()
    cur.execute(
        "SELECT dimension, score, dimension_status FROM analysis_results "
        "WHERE evaluation_id = %s ORDER BY dimension",
        (eval_id,),
    )
    rows = cur.fetchall()
    by_dim = {r[0]: {"score": r[1], "status": r[2]} for r in rows}

    assert by_dim["variety"]["score"] == 85
    assert by_dim["variety"]["status"] == "ok"
    assert by_dim["posture"]["score"] == 70
    assert by_dim["posture"]["status"] == "ok"  # DB default


# ---------- Score nullable validation ----------


def test_score_null_allowed_with_failure(conn, eval_id):
    """Score NULL eh valido quando dimension_status != 'ok'."""
    _insert_analysis(
        conn,
        eval_id,
        "variety",
        score=None,
        confidence="failed",
        dimension_status="skipped",
        failure_reason="upstream_dependency_failed",
    )
    row = _get_analysis(conn, eval_id, "variety")
    assert row["score"] is None
    assert row["dimension_status"] == "skipped"
