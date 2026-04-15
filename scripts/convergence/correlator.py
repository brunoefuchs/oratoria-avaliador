"""Pearson r + top-3 concordance — AC-2, AC-3, AC-4 of Story 7.6."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass


DIMENSIONS = ["voz", "clareza", "presenca", "gestos", "arquetipos", "congruencia"]

R_TARGET_OVERALL = 0.85
R_TARGET_DIMENSION = 0.75
TOP3_TARGET = 2  # at least 2 of 3 items coincide


@dataclass
class ConvergenceReport:
    pairwise_r_overall: dict[str, float]
    mean_r_overall: float
    pairwise_r_per_dimension: dict[str, dict[str, float]]  # dim -> {pair: r}
    top3_fortes_concordance: dict[str, int]  # pair -> count (0..3)
    top3_fracos_concordance: dict[str, int]
    alerts: list[dict]


def pearson_r(xs: list[float], ys: list[float]) -> float:
    """Classic Pearson correlation. Returns 0.0 if stdev is 0 on either side."""
    if len(xs) != len(ys) or len(xs) < 2:
        raise ValueError("Need same-length lists with at least 2 points")
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    var_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    var_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    if var_x == 0 or var_y == 0:
        return 0.0
    return cov / (var_x * var_y)


def _pairs(llms: list[str]) -> list[tuple[str, str]]:
    return [(a, b) for i, a in enumerate(llms) for b in llms[i + 1 :]]


def pairwise_r(scores_per_llm: dict[str, list[float]]) -> dict[str, float]:
    """For each LLM pair, compute Pearson r across the given score vectors."""
    out: dict[str, float] = {}
    llms = list(scores_per_llm.keys())
    for a, b in _pairs(llms):
        out[f"{a}-{b}"] = pearson_r(scores_per_llm[a], scores_per_llm[b])
    return out


def _tokenize(text: str) -> set[str]:
    """Lowercased tokens of length >= 3. Cheap proxy for semantic overlap.

    Trade-off vs embeddings: faster, no extra dependency, lower recall on
    semantic equivalence ("voz monocórdia" vs "pouca variação de pitch" won't
    match). Documented in convergence-harness.md — iterate threshold or plug
    sentence-transformers if this becomes a bottleneck.
    """
    return {t for t in re.findall(r"\w+", text.lower()) if len(t) >= 3}


def jaccard_similarity(a: str, b: str) -> float:
    ta, tb = _tokenize(a), _tokenize(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def top3_concordance(
    pontos_per_llm: dict[str, list[str]],
    threshold: float = 0.3,
) -> dict[str, int]:
    """Count how many of top-3 pontos match across each LLM pair.

    A "match" means any point from A has Jaccard similarity >= threshold
    with any point from B. Threshold 0.3 is conservative — tune per use.
    """
    out: dict[str, int] = {}
    llms = list(pontos_per_llm.keys())
    for a, b in _pairs(llms):
        matches = 0
        pts_a = pontos_per_llm[a][:3]
        pts_b = pontos_per_llm[b][:3]
        used_b: set[int] = set()
        for pa in pts_a:
            best_idx, best_sim = -1, threshold
            for j, pb in enumerate(pts_b):
                if j in used_b:
                    continue
                sim = jaccard_similarity(pa, pb)
                if sim >= best_sim:
                    best_idx, best_sim = j, sim
            if best_idx >= 0:
                matches += 1
                used_b.add(best_idx)
        out[f"{a}-{b}"] = matches
    return out


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def build_report(evaluations: dict) -> ConvergenceReport:
    """Build full convergence report from {llm: EvaluationResult}.

    Accepts either EvaluationResult objects (with attributes) or plain dicts
    (with keys) to allow calling without pulling llm_client at test time.
    """

    def _get(obj, key):
        return getattr(obj, key) if hasattr(obj, key) else obj[key]

    llms = list(evaluations.keys())

    overall_scores = {llm: [_get(evaluations[llm], "score_geral")] for llm in llms}
    scores_per_dim = {llm: _get(evaluations[llm], "scores_por_dimensao") for llm in llms}
    fortes_per_llm = {llm: _get(evaluations[llm], "pontos_fortes") for llm in llms}
    fracos_per_llm = {llm: _get(evaluations[llm], "pontos_fracos") for llm in llms}

    # AC-2: overall r — built from ONE score per LLM, so we need 2+ samples
    # to compute Pearson. For a single video, we report just the pair deltas
    # as a proxy; correlator is meaningful across batches.
    if all(len(v) >= 2 for v in overall_scores.values()):
        pair_r_overall = pairwise_r({llm: overall_scores[llm] for llm in llms})
    else:
        pair_r_overall = {
            f"{a}-{b}": 1.0 - abs(overall_scores[a][0] - overall_scores[b][0]) / 100.0
            for a, b in _pairs(llms)
        }

    # AC-3: dimension r — compute vectors across dimensions, per pair
    per_dim_r: dict[str, dict[str, float]] = {}
    for dim in DIMENSIONS:
        vectors = {llm: [scores_per_dim[llm].get(dim, 0.0)] for llm in llms}
        if all(len(v) >= 2 for v in vectors.values()):
            per_dim_r[dim] = pairwise_r(vectors)
        else:
            per_dim_r[dim] = {
                f"{a}-{b}": 1.0 - abs(vectors[a][0] - vectors[b][0]) / 100.0
                for a, b in _pairs(llms)
            }

    # AC-4: top-3 concordance
    fortes_conc = top3_concordance(fortes_per_llm)
    fracos_conc = top3_concordance(fracos_per_llm)

    # Alert surface
    alerts: list[dict] = []
    mean_r = _mean(list(pair_r_overall.values()))
    if mean_r < R_TARGET_OVERALL:
        alerts.append(
            {
                "dimensao": None,
                "r_calculado": mean_r,
                "r_esperado": R_TARGET_OVERALL,
                "severidade": "warning",
                "detalhes": {"pairwise": pair_r_overall},
            }
        )
    for dim, pair_map in per_dim_r.items():
        dim_mean = _mean(list(pair_map.values()))
        if dim_mean < R_TARGET_DIMENSION:
            alerts.append(
                {
                    "dimensao": dim,
                    "r_calculado": dim_mean,
                    "r_esperado": R_TARGET_DIMENSION,
                    "severidade": "warning",
                    "detalhes": {"pairwise": pair_map},
                }
            )
    for pair, count in fortes_conc.items():
        if count < TOP3_TARGET:
            alerts.append(
                {
                    "dimensao": "pontos_fortes",
                    "r_calculado": count,
                    "r_esperado": TOP3_TARGET,
                    "severidade": "warning",
                    "detalhes": {"pair": pair, "concordance": count},
                }
            )

    return ConvergenceReport(
        pairwise_r_overall=pair_r_overall,
        mean_r_overall=mean_r,
        pairwise_r_per_dimension=per_dim_r,
        top3_fortes_concordance=fortes_conc,
        top3_fracos_concordance=fracos_conc,
        alerts=alerts,
    )
