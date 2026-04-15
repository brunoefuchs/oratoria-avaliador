"""
mentor_router.py
────────────────
Decide qual mentor clone narra o relatório: gui-reginatto ou vinh-giang.

Regras canônicas (PRD 10.2 story 3.1):
- pt-BR + foco em identidade/vendas/autoridade → gui-reginatto
- en + foco vocal/palco/performance magic → vinh-giang
- Default (pt-BR + mistura): gui-reginatto (nativo)

Epic 3 — Story 3.1. Determinístico, sem LLM.
"""

from __future__ import annotations

from typing import Any

GUI_KEYWORDS = {
    "vender_mais", "vendas", "redes_sociais",
    "autoridade", "carreira", "palestrar",
}
VINH_KEYWORDS_EN = {
    "stage", "vocal", "performance", "magic",
}


def route_mentor(
    evaluation_context: dict[str, Any] | None = None,
    user_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Retorna mentor escolhido + rationale.

    evaluation_context: questionário 6.Q (motivacao, desejo_transmitir, desejo_melhorar)
    user_profile: { language: "pt-BR"|"en", ... } (opcional)
    """
    lang = "pt-BR"
    if user_profile and user_profile.get("language"):
        lang = user_profile["language"]

    ctx = evaluation_context or {}
    motivacao = set(ctx.get("motivacao") or [])
    desejo_transmitir = set(ctx.get("desejo_transmitir") or [])
    desejo_melhorar = set(ctx.get("desejo_melhorar") or [])
    all_signals = motivacao | desejo_transmitir | desejo_melhorar

    gui_hits = len(all_signals & GUI_KEYWORDS)
    vinh_hits_en = len(all_signals & VINH_KEYWORDS_EN)

    if lang.lower().startswith("en"):
        mentor = "vinh-giang"
        rationale = f"language={lang} → vinh (native EN; vocal/performance frameworks)"
    elif vinh_hits_en > 0 and "palco" in motivacao and lang == "pt-BR":
        mentor = "vinh-giang"
        rationale = f"palco focus + vocal keywords → vinh (com adaptação pt-BR)"
    elif gui_hits > 0:
        mentor = "gui-reginatto"
        rationale = f"motivacao/desejo matches gui domain ({gui_hits} hits) + lang={lang} → gui"
    else:
        mentor = "gui-reginatto"
        rationale = f"default pt-BR → gui-reginatto (nativo + método comuniCAR)"

    dna_base_path = f"squads/squad-creator-pro/minds/{mentor.replace('-', '_')}/"

    return {
        "mentor": mentor,
        "language": lang,
        "dna_paths": {
            "voice_dna": dna_base_path + "voice_dna.yaml",
            "thinking_dna": dna_base_path + "thinking_dna.yaml",
            "mind_complete": dna_base_path + "mind_dna_complete.yaml",
        },
        "rationale": rationale,
        "signals_analyzed": {
            "motivacao": list(motivacao),
            "desejo_transmitir": list(desejo_transmitir),
            "desejo_melhorar": list(desejo_melhorar),
            "gui_hits": gui_hits,
            "vinh_en_hits": vinh_hits_en,
        },
    }
