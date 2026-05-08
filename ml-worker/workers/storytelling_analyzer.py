"""Story 7.3 — Storytelling Analyzer (local-first com fallback LLM opcional).

Mede arquitetura da mensagem (NAO delivery): bridge sentence, opening hook, CTA,
e chemicals (dopamine + oxytocin) — 2 dos 4 do framework Vinh.

Vinh framework relevante:
- Bridge sentence ("the reason I'm telling you this is...") = conecta historia → audiencia
- Opening hook = primeiros 7 segundos decidem tudo
- CTA = convite a acao no fechamento
- 4 Chemicals: dopamine (curiosidade), oxytocin (vulnerabilidade), endorphins (humor — TODO), cortisol (anti-pattern)

Decisao do spike Task 0: regex-first determinístico (zero nova dependencia)
+ fallback LLM opt-in via env STORYTELLING_USE_LLM=true.
"""

import os
import re

import structlog

logger = structlog.get_logger()

# ─────────────────────────────────────────────────────────────────────────────
# PADROES PT-BR (validados via amostra de transcripts oratoria-avaliador)
# Ajustar via Task 8 com videos de calibracao.
# ─────────────────────────────────────────────────────────────────────────────

# Bridge sentence — frase que conecta historia/dado ao publico
BRIDGE_PATTERNS = [
    r"\b(a\s+)?raz[ãa]o (de eu )?(estar )?(te |lhe )?(contando|falando|compartilhando|dizendo) isso",
    r"\b(o\s+)?motivo (de eu |pra te |para te |de )?(contar|compartilhar|falar)",
    r"\btrago isso (aqui )?porque",
    r"\bisto (impor|interes)ta (para|pra) voc[êe] porque",
    r"\bo que isso significa (pra|para) voc[êe]",
    r"\bpor que (eu )?(estou )?(te )?(dizendo|contando|falando) isso",
    r"\bisso (interes|impor)ta (pra|para) voc[êe] porque",
    r"\b(eu )?(estou |vou )?(compartilho|compartilhando) isso (pra|para) voc[êe]",
    r"\bo ponto (aqui )?[ée]:?\s",
    r"\ba li[çc][ãa]o (aqui )?[ée]:?\s",
]

# CTA (Call to Action) — imperativos + convites
CTA_PATTERNS = [
    r"\b(eu )?te convido (a|para|pra)\s",
    r"\bcomece (hoje|agora|j[áa])",
    r"\bo pr[óo]ximo passo",
    r"\b(experimente|tente|fa[çc]a|veja|olhe|escute|escreva|grave|teste|comece|aplique|implemente|pratique)\s.{1,30}\b(hoje|agora|amanh[ãa]|essa\s+semana|esse\s+m[êe]s|j[áa])\b",
    r"\bvoc[êe] pode\s.{1,30}\b(hoje|agora)\b",
    r"\b(eu )?te chamo (para|pra)\s",
    r"\bse vira[çc]o[uem]?\s.{1,40}\b(comece|fa[çc]a|tente|teste)\b",
    r"\bclique no link",
    r"\bdescobr.{1,5} mais em\s",
    r"\bagora\s+[ée]\s+sua\s+vez\b",
]

# Hook patterns — tipos
HOOK_PATTERNS = {
    "question": [r"\?"],  # presença de "?"
    "story": [
        r"\bquando (eu|tinha)\b",
        r"\bh[áa] (\d+|[a-z]+)\s+(anos|meses|dias)\b",
        r"\bera uma vez\b",
        r"\bimagine\b",
        r"\blembro (que|quando|de)\b",
        r"\bvou contar\b",
    ],
    "stat": [
        r"\b\d+%\b",
        r"\b\d+\s+(milh[õo]es|bilh[õo]es|mil)\b",
        r"\b(metade|dois ter[çc]os|um ter[çc]o|tres em cada|9 em cada)\b",
    ],
    "vulnerability": [
        r"\beu (falhei|errei|n[ãa]o sabia|tive medo|fiquei perdid[oa]|me senti)",
        r"\bnunca (consegui|tive coragem)",
        r"\bera o pior\b",
    ],
    "challenge": [
        r"\b(voc[êe]|voces) j[áa] (parou|pararam|sentiu|sentiram|notou|notaram)",
        r"\bquantos de voc[êe]s",
        r"\bquem aqui (j[áa] |nunca |sente)",
    ],
    "magic_trick": [
        # Reservado para humor/surpresa — dificil detectar com regex sem falso positivo.
        # Mantemos vazio: detection vira "none" se nenhum outro tipo bater.
    ],
    # 2026-05-05: hook de ANTITESE/DICOTOMIA — "ou X, ou Y" (template Vinh classico)
    "antithesis": [
        r"\bou\s+\w+(?:\s+\w+){0,3}\s*,\s*ou\s+\w+",  # "ou ela te X, ou ela te Y"
        r"\b(existem|tem|s[oó])\s+(duas|2|tres|3)\s+(funcoes|funções|tipos|opcoes|opções|caminhos)\b",
        r"\b(ou voce|ou tu)\s+\w+,?\s*(ou voce|ou tu)\s+\w+",
    ],
    # 2026-05-05: hook de AFIRMACAO CORAJOSA / declaracao chocante
    "bold_claim": [
        r"\bse voce nao \w+,?\s+e melhor voce nao\b",  # "se vc nao X, e melhor vc nao"
        r"\bninguem (te |vai te)?\w+ isso\b",
        r"\bo que (te|voce)\s+(nao\s+)?(contam|contaram|disseram)\b",
        r"\b(toda|qualquer|todo)\s+\w+\s+(falha|fracassa|morre|some)\s+(porque|por causa)",
    ],
    # 2026-05-05 v2: 6 hooks novos
    # Pergunta retorica sem "?" — speaker afirma como pergunta retorica
    "rhetorical_question": [
        r"\bsera que (voce|tu|a gente|nos)\b",
        r"\bcomo e que\b",
        r"\bpor que (sera|que)\b",
        r"\b(voce|tu) ja se perguntou\b",
        r"\bquem nunca\b",
    ],
    # Cenario hipotetico — coloca audiencia em situacao imaginaria
    "hypothetical": [
        r"\bsuponha que\b",
        r"\bimagine se\b",
        r"\be se (voce|tu|fosse|tivesse)\b",
        r"\bpense (numa|num|no momento)\b",
        r"\bvamos supor\b",
    ],
    # Observacao cotidiana — fisga via familiaridade
    "everyday_observation": [
        r"\bja (reparou|notou|viu) que\b",
        r"\btoda vez que\b",
        r"\b(voce|tu) (ja|provavelmente) (passou|passa|sentiu) por\b",
        r"\bsempre (que|tem)\b",
    ],
    # Confronto direto — call-out provocativo
    "direct_challenge": [
        r"\b(voce|tu) (esta|est[áa]) (fazendo|achando|pensando) (errado|isso errado)\b",
        r"\b(voce|tu) acha mesmo que\b",
        r"\bse (voce|tu) acredita\b",
        r"\bpara de\s+(achar|pensar|fazer)\b",
    ],
    # Paradoxo / contra-intuitivo
    "paradox": [
        r"\bquanto mais .{1,40} menos\b",
        r"\bquanto menos .{1,40} mais\b",
        r"\bo que parece\s+\w+\s+e\s+(na verdade|na realidade)\b",
        r"\b(exatamente|justamente) o contrario\b",
    ],
    # Comparacao metaforica — "X é como Y"
    "metaphor": [
        r"\b(e|sao) como (uma|um|os|as)?\s*\w+\b",  # "é como uma orquestra"
        r"\bfunciona como (uma|um|os|as)?\s*\w+\b",
        r"\bigual a (uma|um|os|as)?\s*\w+\b",
        r"\bse parece com\b",
        r"\b(tipo|que nem) (uma|um)\s+\w+\b",
    ],
    # 2026-05-05 v3 — 9 familias do guia Conrado Adolpho (108 ganchos)
    # Cat 1: Curiosidade & Segredo
    "mystery_secret": [
        r"\bos? segredos? d[aeo]s?\b",
        r"\bo que .{1,30} nao (quer|querem) que (voce|tu) saiba\b",
        r"\b(descubra|descobre) (como|o que|o segredo|a estrategia)\b",
        r"\ba verdade (sobre|que ninguem te conta|escondida)\b",
        r"\bo que ninguem (te|voce) (conta|fala|diz)\b",
        r"\bdesconstruindo\b",
        r"\bo? \w+ (que|quem) voce nao conhece\b",
        r"\bvoce sabia que\b",
        r"\bos? \w+ \w+ (nao revelados?|escondidos?|ocultos?)\b",
        r"\ba historia (nao contada|por tras) de\b",
    ],
    # Cat 2: Medo & Urgência
    "fear_urgency": [
        r"\bse previna (agora|antes)\b",
        r"\bantes de (assinar|contratar|investir|comprar|tomar)\b",
        r"\bantes (que|de) .{1,40} (aconteca|seja tarde|voce)",
        r"\bperigo oculto\b",
        r"\bnunca\.? nunca\b",
        r"\bnunca (faca|contrate|invista)\b",
        r"\bleia isso antes\b",
        r"\bnao (invista|contrate|faca|assine) antes\b",
        r"\bos? \w+ sinais? de que\b",
        r"\bcomo se livrar do perigo\b",
    ],
    # Cat 3: Ganância & FOMO
    "fomo_desire": [
        r"\b(que|conteudo|leads?|oportunidades?) (voce|tu) (esta|estao) perdendo\b",
        r"\bimagine acordar (todo dia|com|toda semana)\b",
        r"\bimagine poder\b",
        r"\btenha um \w+ (todo|todos? os) (mes|mes|ano|semana)\b",
        r"\ba maneira mais (facil|rapida|barata|previsivel|simples)\b",
        r"\bcomo transformar .{1,30} sem (risco|esforco|dor)\b",
        r"\bos? \w+ (escondidos?|ocultos?) (debaixo|dentro) (do|da)\b",
        r"\b(qual|quais) desses\b",
    ],
    # Cat 4: Autoridade & Prova Social
    "authority_proof": [
        r"\bveja e copie (o|a) (metodo|processo|estrategia)\b",
        r"\b(novo )?estudo comprova\b",
        r"\b(cientistas|especialistas|dados) comprovam\b",
        r"\bciencia comprova\b",
        r"\ba biblia (do|da|de)\b",
        r"\b\w+ descobre (uma|um|sistema|metodo)\b",
        r"\bo que .{1,30} faz quando\b",
        r"\b\w+ mostra o que (usa|tem|faz) no dia a dia\b",
    ],
    # Cat 5: Herói Improvável
    "unlikely_hero": [
        r"\beles riram quando eu\b",
        r"\bcomo eu (fiz|consegui|gerei) .{1,30} (sem|com)\b",
        r"\bcomo (uma|um) \w+ (de|do|da) \w+ (se tornou|virou|conseguiu)\b",
        r"\b\w+ humilha\b",
        r"\bcomo .{1,30} descobriu uma maneira (simples|rapida|segura)\b",
        r"\bcomo uma nova descoberta transformou\b",
    ],
    # Cat 6: Números & Especificidade (lista numerada)
    "numbered_list": [
        r"\bos? (\d+|cinco|seis|sete|oito|nove|dez) (mitos?|mentiras?|sinais?|erros?|razoes?|formas?|maneiras?|estrategias?|passos?) (sobre|para|de|que)\b",
        r"\b(\d+|cinco|seis|sete) razoes? (para|pra) voce\b",
        r"\b(\d+|cinco|seis|sete|oito|nove|dez) (passos?|formas?|maneiras?|jeitos?) (simples|para|pra)\b",
        r"\b\w+: o que fazer e o que nunca fazer\b",
        r"\bem (\d+|cinco|seis|sete|tres|quatro) passos\b",
    ],
    # Cat 7: Diagnóstico & Autoconhecimento
    "diagnostic_quiz": [
        r"\bque tipo de \w+ (voce|tu) e\??\b",
        r"\bfaca (este|esse) teste\b",
        r"\bvoce esta (cometendo|fazendo) (esse|um) erro\??\b",
        r"\bvoce esta \w+ do jeito errado\??\b",
        r"\bvoce sabe (quais|os) (sao os )?sintomas\b",
        r"\bos? \w+ sintomas (ocultos?|de)\b",
        r"\bdescubra como resolver o problema de\b",
        r"\bvoce comete (uma|alguma|um|esse|esses) (dessas|desses)?\s*\d*\s*(coisas?|erros?|comportamentos?)\b",
        r"\bo que aconteceria se voce\b",
        r"\bvoce ja verificou\b",
    ],
    # Cat 8: Segmentação
    "targeting": [
        r"\bpara (voce|voces|donos?|empresarios?|profissionais?) que\b",
        r"\bvoce que (esta|tem|sofre|trabalha)\b",
        r"\buma mensagem (rapida|importante) para\b",
        r"\batencao,?\s+\w+",
        r"\bvoce sofre de\b",
        r"\bcontinue lendo (somente )?se voce\b",
        r"\bvoce ja se sentiu como\b",
        r"\bo maior erro que .{1,30} (comete|cometem)\b",
        r"\bchegou (a|sua) (sua )?vez de\b",
    ],
    # Cat 9: Quebra de Crença & Mitos
    "belief_break": [
        r"\btudo (que|o que) (voce|tu) (aprendeu|sabe|viu) sobre .{1,40} (esta errado|nao funciona)\b",
        r"\besquec[ae] tudo (que|o que) (voce|tu) (aprendeu|sabe|viu)\b",
        r"\b\w+ (esta|estao) mort[oa]\b",
        r"\bos? \d+ mentiras? que te contam\b",
        r"\bpor que .{1,30} nao quer que (voce|tu)\b",
        r"\bposso ser cancelado (por|pela) isso\b",
        r"\b(o que|tudo) .{1,30} ensinou esta errado\b",
    ],
}

# Chemicals — dopamine (loops abertos, suspense)
DOPAMINE_PATTERNS = [
    r"\bvou (te )?contar (algo |uma coisa )?(surpreendente|que vai te surpreender|incri[íi]vel)",
    r"\b(em )?(\d+|alguns|tres|quatro|cinco) (segundos|minutos), voc[êe] vai\b",
    r"\bem instantes (eu )?vou (revelar|mostrar|contar)",
    r"\bguarde (essa |isso |essa frase|esse n[úu]mero)",
    r"\bspoiler:",
    r"\bvolto (a |em )?(isso|nisso) j[áa]",
]

# Chemicals — oxytocin (vulnerabilidade autodeclarada)
OXYTOCIN_PATTERNS = [
    r"\beu (falhei|errei|n[ãa]o sabia|tive medo|fiquei perdid[oa])",
    r"\bme senti (sozinh[oa]|fracassad[oa]|impotente|desesperad[oa]|envergonhad[oa])",
    r"\bn[ãa]o tinha (resposta|ideia|coragem|nada)",
    r"\bera (o |a )?(pior|mais (frac[oa]|insegur[oa]))",
    r"\b(perdi|falhei|fracassei) (em|no|na|com)",
    r"\b(at[ée] )?chorei",
]

# Cortisol risk — proxy textual (delivery cortisol vem de variety analyzer; aqui só palavras)
CORTISOL_TEXT_PATTERNS = [
    r"\b(p[ãa]nico|terror|desespero|ang[úu]stia|ansiedade)\b",
    r"\bperigo iminente",
    r"\bcatastr[óo]f(e|ico)",
]

# 2026-05-05: Loss aversion — proxy textual de cortisol "negativo" suave.
# Usado em pitchs ("se voce nao fizer, vai perder X"). Diferente de catastrofe.
LOSS_AVERSION_PATTERNS = [
    r"\b(de forma|de maneira)\s+(mais\s+)?(negativa|pejorativa|negativamente)",
    r"\b(perde|perder|perdendo)\s+(autoridade|valor|credibilidade|chance|oportunidade)",
    r"\bvai (te |voce )?(custar|perder|fracassar|falhar)",
    r"\b(no|do)\s+contrario,",
    r"\bse voce nao \w+,?\s+(e melhor|voce vai|nao tem)",
]

OPENING_PCT = 0.20  # primeiros 20% do transcript
CLOSING_PCT = 0.15  # ultimos 15%


def _normalize_text(text: str) -> str:
    """Remove acentos pra matching mais robusto (2026-05-05).

    Patterns regex sao escritos sem acento por convencao. Texto whisper
    vem com acentos em PT-BR — sem normalizar, "ja" nao casa "ja"."""
    import unicodedata

    nfkd = unicodedata.normalize("NFKD", text)
    return "".join([c for c in nfkd if not unicodedata.combining(c)])


def _count_matches(text: str, patterns: list) -> tuple[int, list[str]]:
    """Conta matches de uma lista de padroes regex e retorna excerpts."""
    text_norm = _normalize_text(text)
    excerpts = []
    count = 0
    for pat in patterns:
        for m in re.finditer(pat, text_norm, re.IGNORECASE):
            count += 1
            start = max(0, m.start() - 20)
            end = min(len(text_norm), m.end() + 40)
            excerpts.append(text_norm[start:end].strip())
    return count, excerpts[:3]


def _detect_bridge(text: str) -> dict:
    count, excerpts = _count_matches(text, BRIDGE_PATTERNS)
    return {
        "detected": count > 0,
        "count": count,
        "excerpts": excerpts,
    }


def _detect_cta(closing_text: str) -> dict:
    count, excerpts = _count_matches(closing_text, CTA_PATTERNS)
    return {
        "detected": count > 0,
        "excerpt": excerpts[0] if excerpts else None,
    }


def _classify_hook(opening_text: str) -> dict:
    """Identifica tipo dominante de hook nos primeiros 20%.

    2026-05-05: scoring com PESOS por especificidade. Hooks especificos
    (rhetorical, hypothetical, paradox, metaphor, antithesis) tem peso 2 —
    vencem matches genericos como "question" (peso 0.5) ou "story" (peso 1).
    Sem isso, "imagine se voce X" caia em "story" pelo "imagine".
    """
    SPECIFICITY_WEIGHTS = {
        # Tier alto — específicos, Vinh-style
        "rhetorical_question": 2.0,
        "hypothetical": 2.0,
        "paradox": 2.0,
        "metaphor": 2.0,
        "everyday_observation": 2.0,
        "direct_challenge": 2.0,
        "antithesis": 2.0,
        "bold_claim": 1.5,
        "vulnerability": 1.5,
        # Tier alto — Conrado Adolpho 9 categorias (2026-05-05)
        "mystery_secret": 2.0,
        "fear_urgency": 2.0,
        "fomo_desire": 2.0,
        "authority_proof": 2.0,
        "unlikely_hero": 2.0,
        "numbered_list": 1.8,
        "diagnostic_quiz": 2.0,
        "targeting": 1.7,
        "belief_break": 2.0,
        # Tier medio
        "story": 1.0,
        "stat": 1.0,
        "challenge": 1.0,
        # Tier baixo (muito generico)
        "question": 0.5,
    }
    scores = {}
    for hook_type, patterns in HOOK_PATTERNS.items():
        if not patterns:
            continue
        count, _ = _count_matches(opening_text, patterns)
        weight = SPECIFICITY_WEIGHTS.get(hook_type, 1.0)
        scores[hook_type] = count * weight

    if not any(scores.values()):
        return {"type": "none", "strength": "weak"}

    dominant = max(scores, key=scores.get)
    total = sum(scores.values())
    strength = "strong" if scores[dominant] >= 2 or total >= 3 else "medium"
    if scores[dominant] >= 1 and strength != "strong":
        strength = "medium"
    return {"type": dominant, "strength": strength}


def _detect_chemicals(text: str, variety_metrics: dict | None) -> dict:
    """Detecta presenca de chemicals via texto + cross-reference variety."""
    dopamine_count, dopamine_ex = _count_matches(text, DOPAMINE_PATTERNS)
    oxytocin_count, oxytocin_ex = _count_matches(text, OXYTOCIN_PATTERNS)
    cortisol_text_count, _ = _count_matches(text, CORTISOL_TEXT_PATTERNS)
    loss_aversion_count, loss_aversion_ex = _count_matches(text, LOSS_AVERSION_PATTERNS)

    # Cortisol risk: cross-reference com variety (monotonia) se disponivel.
    # Story 7.3 fix QA — mensagem com mais contexto pedagogico pro usuario.
    cortisol_risk = False
    cortisol_reason = ""
    if variety_metrics:
        pct_monotono = variety_metrics.get("pct_tempo_monotono", 0)
        if pct_monotono > 60 and dopamine_count == 0 and oxytocin_count == 0:
            cortisol_risk = True
            cortisol_reason = (
                f"Risco de desengajamento: {pct_monotono}% da fala foi monotona "
                "(sem variacao vocal) E nenhuma estrutura narrativa que prenda atencao. "
                "Cortisol e quimica do desconforto — audiencia tende a parar de prestar atencao "
                "ou trocar de aba. Variar tom + adicionar uma historia/pergunta resolve."
            )
    if cortisol_text_count > 2 and not cortisol_reason:
        cortisol_risk = True
        cortisol_reason = (
            "Vocabulario com carga negativa elevada (panico/desespero/catastrofe). "
            "Use com moderacao — sobrecarga emocional negativa cansa a audiencia."
        )

    return {
        "dopamine": {
            "detected": dopamine_count > 0,
            "examples": dopamine_ex,
        },
        "oxytocin": {
            "detected": oxytocin_count > 0,
            "examples": oxytocin_ex,
        },
        "endorphins": "not_yet_implemented",
        "loss_aversion": {
            "detected": loss_aversion_count > 0,
            "examples": loss_aversion_ex,
        },
        "cortisol_risk": {
            "detected": cortisol_risk,
            "reason": cortisol_reason,
        },
    }


def _compute_score(
    bridge: dict,
    hook: dict,
    cta: dict,
    chemicals: dict,
    duration_seconds: float = 60.0,
) -> tuple[int, str]:
    """Score 0-100 + diagnostico textual.

    2026-05-05: scoring AGORA adaptativo a duracao. Reels (<90s) tem
    estrutura compacta — hook + argumento + CTA. Bridge sentence e
    vulnerabilidade profunda sao luxos de formatos longos.

    Tiers:
    - <90s (reel/short): essenciais = hook + CTA. Bridge bonus.
    - 90s-3min (apresentacao curta): bridge esperado.
    - >3min (palestra): full arco + chemicals.
    """
    is_short = duration_seconds < 90
    is_medium = 90 <= duration_seconds < 180

    if is_short:
        # Formato Reel: hook + argumento + CTA. Estrutura compacta.
        score = 35  # baseline mais alto (formato premia objetividade)
        if hook["type"] != "none":
            if hook["strength"] == "strong":
                score += 25  # hook forte é metade do jogo em Reel
            elif hook["strength"] == "medium":
                score += 15
            else:
                score += 5
        if cta["detected"]:
            score += 20  # CTA é objetivo do Reel
        if chemicals.get("loss_aversion", {}).get("detected"):
            score += 10  # técnica de pitch curto
        if bridge["detected"]:
            score += 10  # bonus, não obrigatório
        if chemicals["oxytocin"]["detected"]:
            score += 10  # vulnerabilidade rara em Reel = ouro
        if chemicals["dopamine"]["detected"]:
            score += 5
        if chemicals["cortisol_risk"]["detected"]:
            score -= 15  # menos punitivo em Reel
    elif is_medium:
        score = 25
        if bridge["detected"]:
            score += 15
        if hook["type"] != "none":
            score += 12 if hook["strength"] == "strong" else 7
        if cta["detected"]:
            score += 15
        if chemicals["dopamine"]["detected"]:
            score += 10
        if chemicals["oxytocin"]["detected"]:
            score += 10
        if chemicals.get("loss_aversion", {}).get("detected"):
            score += 5
        if chemicals["cortisol_risk"]["detected"]:
            score -= 18
    else:
        # Palestra >=3min: full arco esperado
        score = 20
        if bridge["detected"]:
            score += 18  # bridge é critico em formato longo
        if hook["type"] != "none":
            score += 12 if hook["strength"] == "strong" else 7
        if cta["detected"]:
            score += 12
        if chemicals["dopamine"]["detected"]:
            score += 12
        if chemicals["oxytocin"]["detected"]:
            score += 15  # vulnerabilidade essencial em palestra
        if chemicals.get("loss_aversion", {}).get("detected"):
            score += 5
        if chemicals["cortisol_risk"]["detected"]:
            score -= 20

    score = max(0, min(100, score))

    if score >= 80:
        diagnostico = "narrativa_excepcional"
    elif score >= 60:
        diagnostico = "narrativa_solida"
    elif score >= 35:
        diagnostico = "narrativa_basica"
    else:
        diagnostico = "narrativa_ausente"

    return score, diagnostico


def _generate_suggestions(bridge: dict, hook: dict, cta: dict, chemicals: dict) -> list[str]:
    """Sugestoes acionaveis se score < 70."""
    suggestions = []
    if not bridge["detected"]:
        suggestions.append(
            "Adicione uma BRIDGE sentence: 'A razao de eu estar te contando isso e...' "
            "Sem ela, sua historia serve voce, nao a audiencia."
        )
    if hook["type"] == "none":
        suggestions.append(
            "Comece com um HOOK forte: pergunta reflexiva, dado chocante, "
            "ou historia pessoal (vulnerabilidade). Os primeiros 7 segundos decidem tudo."
        )
    elif hook["strength"] == "weak":
        suggestions.append(
            f"Seu hook ({hook['type']}) e fraco. Aprofunde — adicione detalhe sensorial ou tensao."
        )
    if not cta["detected"]:
        suggestions.append(
            "Termine com um CTA claro: 'Comece hoje', 'O proximo passo e...', "
            "'Experimente isso essa semana'. Sem CTA, a fala vira informacao, nao transformacao."
        )
    if not chemicals["dopamine"]["detected"] and not chemicals["oxytocin"]["detected"]:
        suggestions.append(
            "Sua fala nao acionou chemicals positivos. Considere abrir um loop "
            "(suspense/curiosidade) ou compartilhar uma vulnerabilidade autentica."
        )
    if chemicals["cortisol_risk"]["detected"]:
        suggestions.append(
            f"ATENCAO: risco de cortisol detectado. {chemicals['cortisol_risk']['reason']}"
        )
    return suggestions[:3]


def _hook_from_opening_result(opening_result: dict) -> dict | None:
    """Story 7.3 fix QA — reusa classificacao do opening_analyzer ao inves de re-classificar.

    Mapping opening_analyzer.tecnicas_detectadas → storytelling hook format.
    """
    if not opening_result or not opening_result.get("disponivel"):
        return None
    tecnicas = opening_result.get("tecnicas_detectadas", [])
    if not tecnicas:
        return {"type": "none", "strength": "weak"}
    primeira = tecnicas[0]
    tecnica_id = primeira.get("tecnica", "")
    qualidade = primeira.get("qualidade", "fraca")
    # Map tecnica_id → storytelling hook type
    type_map = {
        "pergunta_reflexiva": "question",
        "pergunta_casual": "question",
        "dado_chocante": "stat",
        "gancho_historia": "story",
        "frase_impacto": "bold_claim",
        "quebra_gelo": "challenge",
        "conexao_audiencia": "challenge",
        "citacao_autoridade": "stat",
        # 2026-05-05: faltavam mapeamentos — opening detectava mas storytelling
        # caia em "none" quando hook era axiomatico/dichotomy/identity.
        "declaracao_axiomatica": "antithesis",
        "identity_led": "bold_claim",
    }
    hook_type = type_map.get(tecnica_id, "none")
    # qualidade: opening_analyzer usa "boa"/"fraca", storytelling usa "weak/medium/strong"
    if qualidade == "boa":
        strength = "strong" if len(tecnicas) >= 2 else "medium"
    else:
        strength = "weak"
    return {"type": hook_type, "strength": strength}


def _compute_storytelling_metrics(
    transcript: dict,
    variety_metrics: dict | None = None,
    opening_result: dict | None = None,
) -> dict:
    """Analisa estrutura narrativa do transcript.

    Args:
        transcript: dict com 'full_text' e 'words' (output do whisper)
        variety_metrics: dict opcional com pct_tempo_monotono etc (cross-reference)
        opening_result: dict opcional do opening_analyzer (story 7.3 fix consistencia)
            Se passado, hook reusa classificacao do opening_analyzer ao inves de re-classificar.
    """
    full_text = transcript.get("full_text", "")
    if not full_text or len(full_text.split()) < 30:
        logger.warning("storytelling_text_too_short")
        return _disponivel_false("Transcript muito curto para analise narrativa")

    text_lower = full_text.lower()
    text_len = len(text_lower)
    opening_text = text_lower[: int(text_len * OPENING_PCT)]
    closing_text = text_lower[int(text_len * (1 - CLOSING_PCT)) :]

    bridge = _detect_bridge(text_lower)
    # Story 7.3 fix QA: prefer opening_analyzer classification (consistencia cross-worker)
    hook_from_opening = _hook_from_opening_result(opening_result)
    hook = hook_from_opening if hook_from_opening else _classify_hook(opening_text)
    cta = _detect_cta(closing_text)
    chemicals = _detect_chemicals(text_lower, variety_metrics)

    # Duration-aware scoring (2026-05-05)
    duration_seconds = transcript.get("duration_seconds", 0.0)
    if not duration_seconds and transcript.get("words"):
        last_word = transcript["words"][-1] if transcript["words"] else {}
        duration_seconds = float(last_word.get("end", 60.0))
    duration_seconds = duration_seconds or 60.0

    score, diagnostico = _compute_score(
        bridge, hook, cta, chemicals, duration_seconds=duration_seconds
    )
    suggestions = _generate_suggestions(bridge, hook, cta, chemicals) if score < 70 else []

    # AC-9 — fallback LLM opcional (default off)
    use_llm = os.environ.get("STORYTELLING_USE_LLM", "false").lower() == "true"
    if use_llm:
        # Hook: futuro — chamada Gemini para refinar deteccao em casos border-line.
        # Por ora, log e segue com regex.
        logger.info("storytelling_llm_flag_set_but_not_implemented")

    logger.info(
        "storytelling_analysis_complete",
        score=score,
        diagnostico=diagnostico,
        bridge_detected=bridge["detected"],
        hook_type=hook["type"],
        cta_detected=cta["detected"],
    )

    # Story 10.3 — extension info-only: tipos_payoff_detectados (heurística leve).
    # Callback abertura↔fechamento NÃO é detectado aqui (semântico → fica 100% Gemini
    # no discourse_arc_analyzer). Estes campos são input cross-feed pro Gemini E
    # exibição opcional UI; NÃO alteram score atual (AC2 constraint).
    tipos_payoff = _detect_payoff_types(text_lower, closing_text)

    return {
        "disponivel": True,
        "score": score,
        "diagnostico": diagnostico,
        "bridge_sentence": bridge,
        "opening_hook": hook,
        "cta": cta,
        "chemicals": chemicals,
        "suggestions": suggestions,
        "tipos_payoff_detectados": tipos_payoff,
    }


# Story 10.3 — heurística leve de payoff types (Kindra Hall taxonomy)
# Callback fica fora — semântico, vira 100% Gemini no discourse_arc_analyzer.
_PAYOFF_KEYWORDS = {
    "insight": [
        "perceba", "percebi", "entendi", "descobri", "aprendi", "a verdade é",
        "o que importa", "a chave", "o segredo", "o ponto é", "a lição",
    ],
    "imagem": [
        "imagine", "visualize", "como se", "parecia", "soava", "cheirava",
        "tocava", "pintura", "cena", "quadro",
    ],
    "cta": [
        "faça", "experimente", "comece", "tente", "vá", "pratique",
        "implemente", "aplique", "teste", "lembre-se",
    ],
    "licao": [
        "moral", "ensinamento", "princípio", "regra", "fundamento",
        "se você",  "sempre que", "nunca",
    ],
}


def _detect_payoff_types(full_text_lower: str, closing_text_lower: str) -> list[str]:
    """Detecta tipos de payoff presentes (heurística keyword).

    Concentra busca no closing_text (peso 2x) — payoff geralmente é fechamento.
    """
    found: dict[str, int] = {}
    for tipo, keywords in _PAYOFF_KEYWORDS.items():
        # Closing pesa 2x (payoff é fechamento usualmente)
        closing_hits = sum(1 for kw in keywords if kw in closing_text_lower)
        full_hits = sum(1 for kw in keywords if kw in full_text_lower)
        if closing_hits > 0 or full_hits >= 2:
            found[tipo] = closing_hits * 2 + full_hits

    # Retorna ordenado por frequência (mais provável primeiro)
    return [t for t, _ in sorted(found.items(), key=lambda x: -x[1])]


def _disponivel_false(motivo: str) -> dict:
    return {
        "disponivel": False,
        "score": 0,
        "diagnostico": "indisponivel",
        "bridge_sentence": {"detected": False, "count": 0, "excerpts": []},
        "opening_hook": {"type": "none", "strength": "weak"},
        "cta": {"detected": False, "excerpt": None},
        "chemicals": {
            "dopamine": {"detected": False, "examples": []},
            "oxytocin": {"detected": False, "examples": []},
            "endorphins": "not_yet_implemented",
            "cortisol_risk": {"detected": False, "reason": ""},
        },
        "suggestions": [motivo],
    }


# Story 8.3 — Truth Contract
from contracts import WorkerFailure, WorkerResult, WorkerSuccess  # noqa: E402


def analyze_storytelling_legacy(
    transcript: dict,
    variety_metrics: dict | None = None,
    opening_result: dict | None = None,
) -> dict:
    """Legacy path (TRUTH_CONTRACT_ENABLED=false)."""
    return _compute_storytelling_metrics(transcript, variety_metrics, opening_result)


def analyze_storytelling(
    transcript: dict,
    variety_metrics: dict | None = None,
    opening_result: dict | None = None,
) -> "WorkerResult":
    """Truth Contract path — retorna WorkerResult (Pydantic).

    Adapta disponivel:bool pattern:
    - disponivel=True + score → WorkerSuccess
    - disponivel=False → WorkerFailure(skipped)
    - Exception → WorkerFailure(crashed)
    """
    try:
        result = _compute_storytelling_metrics(transcript, variety_metrics, opening_result)
        if not result.get("disponivel", True):
            reason = result.get("suggestions", ["indisponivel"])
            reason_str = reason[0] if reason else "analise de storytelling indisponivel"
            return WorkerFailure(
                dimension="storytelling",
                dimension_status="skipped",
                failure_reason=reason_str,
                metrics=result,
            )
        score = result.get("score")
        if score is None:
            return WorkerFailure(
                dimension="storytelling",
                dimension_status="insufficient_data",
                failure_reason="score is None after storytelling analysis",
            )
        metrics = {k: v for k, v in result.items() if k not in ("score", "disponivel")}
        return WorkerSuccess(
            dimension="storytelling",
            score=max(0, min(100, int(score))),
            metrics=metrics,
            confidence=1.0,
        )
    except Exception as e:
        logger.error(
            "storytelling_crashed", error_type=type(e).__name__, error=str(e), exc_info=True
        )
        return WorkerFailure(
            dimension="storytelling",
            dimension_status="crashed",
            failure_reason=f"{type(e).__name__}: {str(e)}",
        )
