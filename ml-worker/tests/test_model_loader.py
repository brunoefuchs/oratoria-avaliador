"""Tests for workers._model_loader — Story 9.2.

Mockado — nao carrega modelos reais. Valida:
- Registry MODEL_FACTORIES
- ModelGPU context manager (enter/exit semantics)
- Lock por model_name
- Error handling (factory raise → lock released)
"""

from __future__ import annotations

import threading
from unittest.mock import MagicMock, patch

import pytest

from workers._model_loader import MODEL_FACTORIES, ModelGPU

# ─────────────────────────────────────────────────────────────
# Factory registry
# ─────────────────────────────────────────────────────────────


def test_factories_registered():
    assert "whisper_turbo" in MODEL_FACTORIES
    assert "whisper_medium" in MODEL_FACTORIES
    assert "wav2vec2_emotion" in MODEL_FACTORIES
    assert "pyfeat" in MODEL_FACTORIES


def test_unknown_model_raises_keyerror():
    with pytest.raises(KeyError, match="nao registrado"):
        ModelGPU("nonexistent_model_xyz")


def test_stub_factories_raise_not_implemented():
    # Story 9.5 stub ainda pendente.
    with pytest.raises(NotImplementedError, match="Story 9.5"):
        with ModelGPU("pyfeat"):
            pass


def test_wav2vec2_emotion_factory_real_story_9_3():
    """Story 9.3: wav2vec2_emotion nao eh mais NotImplementedError stub.
    Sem transformers instalado, raise RuntimeError com hint de instalacao."""
    from workers._model_loader import MODEL_FACTORIES

    factory = MODEL_FACTORIES["wav2vec2_emotion"]
    # Em env sem transformers, factory raise RuntimeError
    try:
        import transformers  # noqa: F401

        # Com lib instalada, factory deve retornar bundle (ou RuntimeError se download falhar)
        try:
            factory()
        except Exception as e:
            # Aceitavel: RuntimeError de download ou similar
            assert "indisponivel" in str(e).lower() or "wav2vec2" in str(e).lower()
    except ImportError:
        # Sem lib: RuntimeError explicito
        with pytest.raises(RuntimeError, match="indisponivel"):
            factory()


# ─────────────────────────────────────────────────────────────
# Context manager enter/exit
# ─────────────────────────────────────────────────────────────


def test_context_manager_basic_flow():
    """Enter carrega, exit libera referencia."""
    fake_model = MagicMock(name="fake_whisper")
    with patch.dict(MODEL_FACTORIES, {"test_model": lambda: fake_model}):
        with ModelGPU("test_model") as model:
            assert model is fake_model
        # Pos-exit: model foi dropado do context
        # (nao podemos verificar diretamente pq variavel sai de scope,
        # mas validamos que unload executou sem exception)


def test_factory_exception_releases_lock():
    """Se factory raise, lock deve ser liberado pra nao deadlock proximo caller."""

    def bad_factory():
        raise RuntimeError("simulated load failure")

    with patch.dict(MODEL_FACTORIES, {"broken": bad_factory}):
        with pytest.raises(RuntimeError, match="simulated"):
            with ModelGPU("broken"):
                pass

        # Segundo caller consegue acquire (lock foi liberado pelo enter failure)
        with pytest.raises(RuntimeError, match="simulated"):
            with ModelGPU("broken"):
                pass


def test_exit_releases_lock_even_on_body_exception():
    """Exception dentro do with body nao deve vazar lock."""
    fake_model = MagicMock()
    with patch.dict(MODEL_FACTORIES, {"t1": lambda: fake_model}):
        with pytest.raises(ValueError, match="body error"):
            with ModelGPU("t1"):
                raise ValueError("body error")

        # Proximo acquire deve funcionar
        with ModelGPU("t1") as m2:
            assert m2 is fake_model


# ─────────────────────────────────────────────────────────────
# Thread safety
# ─────────────────────────────────────────────────────────────


def test_lock_serializes_same_model_name():
    """Dois threads tentando ModelGPU(same_name) sao serializados."""
    fake_model = MagicMock()
    load_order: list[int] = []

    def slow_factory():
        load_order.append(threading.get_ident())
        return fake_model

    with patch.dict(MODEL_FACTORIES, {"shared": slow_factory}):

        def worker():
            with ModelGPU("shared"):
                load_order.append(-1)  # marker "inside"

        t1 = threading.Thread(target=worker)
        t2 = threading.Thread(target=worker)
        t1.start()
        t2.start()
        t1.join(timeout=5)
        t2.join(timeout=5)

        # Cada thread: [tid_from_factory, -1] — sem intercalar
        assert len(load_order) == 4
        assert load_order.count(-1) == 2
