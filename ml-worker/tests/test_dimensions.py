"""Tests for contracts.dimensions — Story 8.1 Truth Contract Fundacao (T2)."""

from contracts.dimensions import (
    ALL_DIMENSIONS,
    AUGMENTATION_DIMENSIONS,
    DIMENSION_TO_WORKER_MODULE,
    SCORING_DIMENSIONS,
)


def test_scoring_dimensions_count():
    assert len(SCORING_DIMENSIONS) == 10


def test_augmentation_dimensions_count():
    assert len(AUGMENTATION_DIMENSIONS) == 3


def test_all_dimensions_is_union():
    assert set(ALL_DIMENSIONS) == set(SCORING_DIMENSIONS) | set(AUGMENTATION_DIMENSIONS)


def test_all_dimensions_no_duplicates():
    assert len(ALL_DIMENSIONS) == len(set(ALL_DIMENSIONS))


def test_dimension_to_worker_module_complete():
    """Veto T2 — Literal e fonte unica de verdade. Map deve cobrir todas as dimensoes."""
    assert set(DIMENSION_TO_WORKER_MODULE.keys()) == set(ALL_DIMENSIONS)


def test_worker_modules_follow_convention():
    """Modulos seguem padrao workers.{nome}_analyzer ou workers.{nome}_detector."""
    for dim, mod in DIMENSION_TO_WORKER_MODULE.items():
        assert mod.startswith("workers."), f"{dim} → {mod} nao esta em workers/"
        assert mod.endswith(("_analyzer", "_detector", "_classifier")), (
            f"{dim} → {mod} nao segue convencao de naming"
        )


def test_scoring_includes_known_dimensions():
    """Smoke check: dimensoes core do MVP estao em scoring."""
    for required in ("voice", "gesture", "posture", "fillers", "variety"):
        assert required in SCORING_DIMENSIONS
