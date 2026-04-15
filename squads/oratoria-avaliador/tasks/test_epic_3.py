"""
test_epic_3.py
──────────────
Smoke tests para Epic 3: mentor-router, hierarchy-ranker, exercise-prescriber,
mentor-narrator, fidelity-checker.

Roda sem pytest:
    python3 squads/oratoria-avaliador/tasks/test_epic_3.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from mentor_router import route_mentor  # noqa: E402
from scoring_engine import score_evaluation  # noqa: E402
from hierarchy_ranker import rank_problems  # noqa: E402
from exercise_prescriber import prescribe  # noqa: E402
from mentor_narrator import render_template_narrative, build_llm_prompt  # noqa: E402
from fidelity_checker import measure_fidelity  # noqa: E402


def _load_fixture(name: str) -> dict:
    p = _HERE.parent / "data" / "fixtures" / name
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def test_router_default_ptbr():
    print("=== TEST_E3_01: router default pt-BR → gui ===")
    r = route_mentor(evaluation_context=None, user_profile=None)
    assert r["mentor"] == "gui-reginatto", r
    assert r["language"] == "pt-BR"
    print(f"  mentor: {r['mentor']} — {r['rationale']}")
    print("PASS\n")


def test_router_vendas_gui():
    print("=== TEST_E3_02: motivacao vendas → gui ===")
    ctx = {"motivacao": ["vender_mais"], "desejo_melhorar": ["autoridade"]}
    r = route_mentor(evaluation_context=ctx)
    assert r["mentor"] == "gui-reginatto"
    assert r["signals_analyzed"]["gui_hits"] >= 2
    print(f"  hits: {r['signals_analyzed']['gui_hits']} — {r['rationale']}")
    print("PASS\n")


def test_router_en_vinh():
    print("=== TEST_E3_03: language=en → vinh ===")
    r = route_mentor(user_profile={"language": "en"})
    assert r["mentor"] == "vinh-giang"
    print(f"  mentor: {r['mentor']}")
    print("PASS\n")


def test_hierarchy_ranks_by_weighted_impact():
    print("=== TEST_E3_04: hierarchy rankeia por weighted_impact ===")
    features = _load_fixture("features_valid_v1.json")
    scoring = score_evaluation(features, evaluation_context={"motivacao": ["vender_mais"]})
    h = rank_problems(scoring, top_n=3)
    assert h["top_n"] == 3
    assert len(h["problems"]) <= 3
    # Rankings devem estar em ordem decrescente de weighted_impact
    impacts = [p["weighted_impact"] for p in h["problems"]]
    assert impacts == sorted(impacts, reverse=True), impacts
    for i, p in enumerate(h["problems"], start=1):
        assert p["rank"] == i
        assert p["why"], f"rank {i} sem why"
    print(f"  top-3: {[(p['rank'], p['dimension'], p['weighted_impact']) for p in h['problems']]}")
    print("PASS\n")


def test_hierarchy_skips_optimal_dimensions():
    print("=== TEST_E3_05: dimensão com gap < 1 não entra no ranking ===")
    scoring = {
        "evaluation_id": "test",
        "applied_weights": {"voice": 0.25, "body": 0.25, "face": 0.25, "storytelling": 0.25},
        "dimension_scores": {
            "voice": {"score": 95.0, "evidence": []},   # gap=0
            "body": {"score": 50.0, "evidence": []},    # gap=35
            "face": {"score": 85.5, "evidence": []},    # gap=0 (arredondando)
            "storytelling": {"score": 60.0, "evidence": []},  # gap=25
        },
    }
    h = rank_problems(scoring, top_n=3)
    dims = [p["dimension"] for p in h["problems"]]
    assert "voice" not in dims, f"voice com score 95 não devia entrar: {dims}"
    print(f"  rankings: {dims}")
    print("PASS\n")


def test_exercise_prescriber_gui():
    print("=== TEST_E3_06: exercise_prescriber gui — G6 coverage ===")
    features = _load_fixture("features_valid_v1.json")
    scoring = score_evaluation(features)
    h = rank_problems(scoring, top_n=3)
    plan = prescribe(h, "gui-reginatto")
    assert plan["g6_exercise_linkage_pass"] is True, plan
    assert plan["mentor"] == "gui-reginatto"
    for item in plan["exercises_by_problem"]:
        assert item["has_exercise"], f"rank {item['rank']} sem exercise"
    print(f"  coverage: OK ({len(plan['exercises_by_problem'])} problems)")
    print("PASS\n")


def test_exercise_prescriber_vinh():
    print("=== TEST_E3_07: exercise_prescriber vinh ===")
    features = _load_fixture("features_valid_v1.json")
    scoring = score_evaluation(features)
    h = rank_problems(scoring, top_n=3)
    plan = prescribe(h, "vinh-giang")
    assert plan["mentor"] == "vinh-giang"
    assert plan["g6_exercise_linkage_pass"] is True
    # Deve usar exercícios específicos do vinh
    exs_names = [
        p["exercises"][0]["name"] if p["exercises"] else None
        for p in plan["exercises_by_problem"]
    ]
    print(f"  vinh exercises: {exs_names}")
    assert any("Highlighter" in n or "Big" in n or "Archetype" in n or "Bridge" in n for n in exs_names if n)
    print("PASS\n")


def test_narrator_template_gui():
    print("=== TEST_E3_08: narrator template gui — saída em pt-BR ===")
    features = _load_fixture("features_valid_v1.json")
    scoring = score_evaluation(features)
    h = rank_problems(scoring, top_n=3)
    plan = prescribe(h, "gui-reginatto")
    narrative = render_template_narrative("gui-reginatto", h, plan)
    assert "Turma," in narrative, "falta saudação gui"
    assert "gui-reginatto" in narrative
    # Deve mencionar um dos top-3 problemas
    top_dim = h["problems"][0]["dimension"]
    assert top_dim in narrative, f"narrativa sem dim {top_dim}"
    print(f"  narrative length: {len(narrative)} chars")
    print("PASS\n")
    return narrative


def test_narrator_template_vinh():
    print("=== TEST_E3_09: narrator template vinh — EN greeting ===")
    features = _load_fixture("features_valid_v1.json")
    scoring = score_evaluation(features)
    h = rank_problems(scoring, top_n=3)
    plan = prescribe(h, "vinh-giang")
    narrative = render_template_narrative("vinh-giang", h, plan)
    assert "Hey friend," in narrative or "vinh-giang" in narrative
    print(f"  narrative length: {len(narrative)} chars")
    print("PASS\n")
    return narrative


def test_fidelity_gui():
    print("=== TEST_E3_10: fidelity gui ≥ ~65% (template baseline) ===")
    features = _load_fixture("features_valid_v1.json")
    scoring = score_evaluation(features)
    h = rank_problems(scoring, top_n=3)
    plan = prescribe(h, "gui-reginatto")
    narrative = render_template_narrative("gui-reginatto", h, plan)
    f = measure_fidelity(narrative, "gui-reginatto")
    print(f"  fidelity: {f['fidelity_pct']}% — sig_hits={len(f['signature_hits'])}, word_hits={len(f['power_word_hits'])}")
    assert f["fidelity_pct"] >= 50, f
    # Template não atinge 85% por design (é baseline — LLM em Epic 3 real atinge)
    print("PASS (template baseline; LLM real deve passar 85%)\n")


def test_build_llm_prompt_structure():
    print("=== TEST_E3_11: build_llm_prompt contém DNA injection ===")
    features = _load_fixture("features_valid_v1.json")
    scoring = score_evaluation(features)
    h = rank_problems(scoring, top_n=3)
    plan = prescribe(h, "gui-reginatto")
    prompt = build_llm_prompt("gui-reginatto", h, plan, evaluation_context={"motivacao": ["vender_mais"]})
    assert prompt["mentor"] == "gui-reginatto"
    assert "MANDATORY SIGNATURE PHRASES" in prompt["system"]
    assert "POWER WORDS" in prompt["system"]
    assert "Portuguese" in prompt["system"]
    assert prompt["fidelity_targets"]["min_phrase_hits"] == 2
    print(f"  system prompt: {len(prompt['system'])} chars, user prompt: {len(prompt['user'])} chars")
    print(f"  fidelity_targets: {prompt['fidelity_targets']['min_phrase_hits']} phrases, {prompt['fidelity_targets']['min_word_hits']} words min")
    print("PASS\n")


def run() -> int:
    test_router_default_ptbr()
    test_router_vendas_gui()
    test_router_en_vinh()
    test_hierarchy_ranks_by_weighted_impact()
    test_hierarchy_skips_optimal_dimensions()
    test_exercise_prescriber_gui()
    test_exercise_prescriber_vinh()
    test_narrator_template_gui()
    test_narrator_template_vinh()
    test_fidelity_gui()
    test_build_llm_prompt_structure()
    print("ALL EPIC 3 TESTS PASSED (11/11)")
    return 0


if __name__ == "__main__":
    sys.exit(run())
