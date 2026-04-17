"""Tests for contracts.dimensions — Story 9.1 (Epic 9 — State of the Art).

Extende os smoke tests da Story 8.1 para cobrir a nova topologia:
- SCORING_DIMENSIONS reduz para 6 (v0.7.0 canonical)
- SCORING_DIMENSIONS_V060 preserva 10 (rollback flag OFF)
- SECONDARY_DIMENSIONS nova (7)
- DIMENSION_CONFIDENCE mapping (5 alta, 4 media, 4 baixa)
- SCHEMA_VERSION_V060 / SCHEMA_VERSION_V070
"""

from contracts.dimensions import (
    ALL_DIMENSIONS,
    AUGMENTATION_DIMENSIONS,
    DIMENSION_CONFIDENCE,
    DIMENSION_TO_WORKER_MODULE,
    SCHEMA_VERSION_V060,
    SCHEMA_VERSION_V070,
    SCORING_DIMENSIONS,
    SCORING_DIMENSIONS_V060,
    SECONDARY_DIMENSIONS,
)


# ─────────────────────────────────────────────────────────────
# V0.7.0 canonical sets (Epic 9)
# ─────────────────────────────────────────────────────────────


def test_scoring_dimensions_count_v070():
    """Story 9.1 AC3: SCORING reduz de 10 para 6."""
    assert len(SCORING_DIMENSIONS) == 6


def test_scoring_dimensions_content_v070():
    assert set(SCORING_DIMENSIONS) == {
        "posture",
        "gesture",
        "voice",
        "fillers",
        "variety",
        "facial",
    }


def test_secondary_dimensions_count():
    """Story 9.1 AC3: 7 secondary dims nova constante."""
    assert len(SECONDARY_DIMENSIONS) == 7


def test_secondary_dimensions_content():
    assert set(SECONDARY_DIMENSIONS) == {
        "archetypes",
        "tonality",
        "opening",
        "identity",
        "storytelling",
        "temporal",
        "congruence",
    }


def test_scoring_and_secondary_disjoint():
    """SCORING e SECONDARY nao podem compartilhar dims."""
    assert set(SCORING_DIMENSIONS).isdisjoint(set(SECONDARY_DIMENSIONS))


# ─────────────────────────────────────────────────────────────
# V0.6.0 legacy preservado (flag OFF)
# ─────────────────────────────────────────────────────────────


def test_scoring_dimensions_v060_count():
    """Rollback safety: preservar 10 dims pre-Epic 9."""
    assert len(SCORING_DIMENSIONS_V060) == 10


def test_scoring_dimensions_v060_contains_v070():
    """V060 contem superset de V070 (diferenca = dims promovidas para SECONDARY)."""
    assert set(SCORING_DIMENSIONS).issubset(set(SCORING_DIMENSIONS_V060))


# ─────────────────────────────────────────────────────────────
# AUGMENTATION preservada (subset de SECONDARY, alias compat)
# ─────────────────────────────────────────────────────────────


def test_augmentation_dimensions_count():
    assert len(AUGMENTATION_DIMENSIONS) == 3


def test_augmentation_is_subset_of_secondary():
    """AUGMENTATION e subset de SECONDARY consumido pelo report_generator."""
    assert set(AUGMENTATION_DIMENSIONS).issubset(set(SECONDARY_DIMENSIONS))


# ─────────────────────────────────────────────────────────────
# ALL_DIMENSIONS = union sem duplicatas (13 total)
# ─────────────────────────────────────────────────────────────


def test_all_dimensions_is_complete_union():
    expected = set(SCORING_DIMENSIONS) | set(SECONDARY_DIMENSIONS)
    assert set(ALL_DIMENSIONS) == expected
    assert len(ALL_DIMENSIONS) == 13


def test_all_dimensions_no_duplicates():
    assert len(ALL_DIMENSIONS) == len(set(ALL_DIMENSIONS))


# ─────────────────────────────────────────────────────────────
# Confidence mapping (Story 9.1 AC5)
# ─────────────────────────────────────────────────────────────


def test_confidence_covers_all_dimensions():
    """Toda dim declarada precisa ter confidence — falha de tipagem se faltar."""
    assert set(DIMENSION_CONFIDENCE.keys()) == set(ALL_DIMENSIONS)


def test_confidence_values_valid():
    valid = {"alta", "media", "baixa"}
    for dim, conf in DIMENSION_CONFIDENCE.items():
        assert conf in valid, f"{dim} tem confidence invalido: {conf}"


def test_confidence_distribution():
    """Validacao da classificacao inicial do diagnostico Vinh."""
    alta = {d for d, c in DIMENSION_CONFIDENCE.items() if c == "alta"}
    media = {d for d, c in DIMENSION_CONFIDENCE.items() if c == "media"}
    baixa = {d for d, c in DIMENSION_CONFIDENCE.items() if c == "baixa"}

    assert alta == {"posture", "gesture", "voice", "fillers", "facial"}
    assert media == {"variety", "archetypes", "tonality", "temporal"}
    assert baixa == {"opening", "identity", "storytelling", "congruence"}


def test_scoring_dims_are_all_alta_confianca():
    """Principio: scoring dims devem ser 🟢 Alta (excecao documentada: variety meta-dim)."""
    for dim in SCORING_DIMENSIONS:
        conf = DIMENSION_CONFIDENCE[dim]
        if dim == "variety":
            # Excecao: variety e meta-dim sobre outputs Alta, herda confianca.
            assert conf == "media"
        else:
            assert conf == "alta", (
                f"scoring dim {dim} deveria ser 'alta' mas e '{conf}'"
            )


# ─────────────────────────────────────────────────────────────
# Schema versioning (Story 9.1 AC7)
# ─────────────────────────────────────────────────────────────


def test_schema_versions_defined():
    assert SCHEMA_VERSION_V060 == "1.1.0"
    assert SCHEMA_VERSION_V070 == "1.2.0"


# ─────────────────────────────────────────────────────────────
# Worker module map (preservado da Story 8.1)
# ─────────────────────────────────────────────────────────────


def test_dimension_to_worker_module_complete():
    assert set(DIMENSION_TO_WORKER_MODULE.keys()) == set(ALL_DIMENSIONS)


def test_worker_modules_follow_convention():
    for dim, mod in DIMENSION_TO_WORKER_MODULE.items():
        assert mod.startswith("workers."), f"{dim} → {mod} nao esta em workers/"
        assert mod.endswith(("_analyzer", "_detector", "_classifier")), (
            f"{dim} → {mod} nao segue convencao de naming"
        )
