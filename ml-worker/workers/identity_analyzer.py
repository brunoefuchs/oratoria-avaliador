"""Identity Analyzer — detecta marcadores linguisticos de identidade comunicativa.

Analisa o transcript do Whisper buscando:
1. Vicios emocionais (Vitimizacao, Comparacao, Rejeicao, Culpa, Injustica)
2. Linguagem de Autoridade vs Linguagem de Vitima

Score de 0-100 onde 100 = identidade firme, autoridade alta.
NAO afeta overall_score — dimensao informativa.
"""

import re

import structlog

from contracts import WorkerResult
from workers._truth_contract_helpers import wrap_worker_result

logger = structlog.get_logger()

VICIOS_EMOCIONAIS = {
    "vitimizacao": [
        r"\bnao consigo\b",
        r"\bnão consigo\b",
        r"\be muito dificil\b",
        r"\bé muito difícil\b",
        r"\bninguem me ajuda\b",
        r"\bninguém me ajuda\b",
        r"\bsempre me acontece\b",
        r"\bnao tem jeito\b",
        r"\bnão tem jeito\b",
        r"\bnao da pra\b",
        r"\bnão dá pra\b",
        r"\bnao da certo\b",
        r"\bimpossivel\b",
        r"\bimpossível\b",
    ],
    "comparacao": [
        r"\bdiferente d[eo]\b",
        r"\btodo mundo tem\b",
        r"\bmenos que os outros\b",
        r"\beu nao sou como\b",
        r"\bo fulano consegue\b",
        r"\beles conseguem\b",
        r"\bpra eles e facil\b",
        r"\bpra eles é fácil\b",
    ],
    "rejeicao": [
        r"\bvao me julgar\b",
        r"\bvão me julgar\b",
        r"\bnao vou conseguir\b",
        r"\bnão vou conseguir\b",
        r"\bninguem vai acreditar\b",
        r"\bninguém vai acreditar\b",
        r"\bvao rir de mim\b",
        r"\bvão rir de mim\b",
        r"\bque vergonha\b",
        r"\bnao sou bom\b",
        r"\bnão sou bom\b",
        r"\bnao sou capaz\b",
    ],
    "culpa": [
        r"\bdesculpa\b",
        r"\bnao sei se posso\b",
        r"\bnão sei se posso\b",
        r"\bespero nao estar atrapalhando\b",
        r"\bperdao\b",
        r"\bperdão\b",
        r"\bme desculpe\b",
        r"\bsinto muito\b",
        r"\bfoi mal\b",
    ],
    "injustica": [
        r"\bdeveria ser diferente\b",
        r"\bnao e justo\b",
        r"\bnão é justo\b",
        r"\berrado isso\b",
        r"\bnao e certo\b",
        r"\bnão é certo\b",
        r"\binjusto\b",
    ],
}

LINGUAGEM_AUTORIDADE = [
    # Originais
    r"\beu vou\b",
    r"\ba melhor forma [eé]\b",
    r"\bfa[cç]a isso\b",
    r"\beu sei\b",
    r"\beu sei que\b",
    r"\bfunciona assim\b",
    r"\beu decidi\b",
    r"\b[eé] assim\b",
    r"\btenho certeza\b",
    r"\bcom certeza\b",
    r"\beu garanto\b",
    r"\bvamos l[aá]\b",
    r"\bprecisamos\b",
    r"\bdevemos\b",
    r"\bvou te mostrar\b",
    r"\bvou te ensinar\b",
    r"\bo que funciona\b",
    # 2026-05-05: ampliado — mentor/coach assertivo usa AFIRMAÇÕES DECLARATIVAS
    # e VERBOS DE AÇÃO em primeira pessoa (destravo, ensino, mostro, transformo).
    r"\bmeu nome [eé]\b",
    r"\beu (destravo|ensino|ajudo|mostro|transformo|construo|crio|fa[cç]o|gero|fecho|implemento)\b",
    r"\beu (te |voc[eê] )?(provo|comprovo|mostro|garanto|afirmo)\b",
    r"\bvou (te |voc[eê] )?(provar|comprovar|mostrar|garantir)\b",
    r"\bte (provo|comprovo|mostro|ensino) que\b",
    r"\b[eé] melhor (voc[eê]|tu) (n[aã]o )?\w+\b",  # "é melhor você não X" (assertion)
    r"\b[eé] a (unica|melhor|verdadeira) (forma|maneira|coisa)\b",
    r"\bsempre que (voc[eê]|tu)\b",  # "sempre que você"
    r"\b(use|evite|contrate|fa[cç]a|pare de|nunca|sempre) \w+\b",  # imperativo
    r"\baprendi\s+(que|com|fazendo)\b",
    r"\bdescobri\s+(que|como|o)\b",
    r"\b(j[aá] )?(vi|atendi|trabalhei com) (mais de )?\d+\b",  # "vi mais de 100"
    r"\btenho \d+ anos\b",
    r"\bao longo (de|dos) \d+ anos\b",
    r"\b(em|h[aá]) \d+ anos (de|atuando|trabalhando)\b",
    r"\bminha experi[eê]ncia (mostra|prova|comprova)\b",
    r"\bo que define\b",
    r"\btudo que (voc[eê]|tu) precisa\b",
    r"\b(quanto|maior) for o\b",  # "quanto maior for o..."
    r"\bdo contr[aá]rio,?\b",
    # 2026-05-05 v3: estilo didático/explicativo (professor assertivo)
    r"\bveja\s+bem\b",
    r"\bolha\s+s[oó]\b",
    r"\bna\s+verdade,?\b",
    r"\bde\s+fato,?\b",
    r"\bna\s+realidade,?\b",
    r"\bent[aã]o,?\s+(se|veja|olha|voc[eê])\b",
    r"\bbasicamente,?\b",
    r"\bo\s+que\s+acontece\s+[eé]\b",
    r"\bcomo\s+funciona\b",
    r"\bcomo\s+[eé]\s+feito\b",
    r"\bperceba\b",
    r"\bobserve\b",
    r"\batente\s+para\b",
    r"\b(repare|note|saiba)\s+(que|bem)\b",
    r"\bisso\s+significa\s+que\b",
    r"\bem\s+resumo,?\b",
    r"\bpor\s+isso\s+(que|mesmo)\b",
]

LINGUAGEM_VITIMA = [
    r"\beu tento\b",
    r"\btalvez\b",
    r"\bquem sabe\b",
    r"\beu acho\b",
    r"\bpode ser que\b",
    r"\beu espero\b",
    r"\bse der\b",
    r"\bn[aã]o sei se\b",
    r"\bsei l[aá]\b",
    r"\bseila\b",
    r"\bde repente\b",
    r"\bse poss[ií]vel\b",
    r"\bnao sei\b",
    r"\bnão sei\b",
    r"\bacho que\b",
]

# Pre-compilar todos os patterns
_VICIOS_COMPILED = {
    cat: [re.compile(p, re.IGNORECASE) for p in patterns]
    for cat, patterns in VICIOS_EMOCIONAIS.items()
}
_AUTORIDADE_COMPILED = [re.compile(p, re.IGNORECASE) for p in LINGUAGEM_AUTORIDADE]
_VITIMA_COMPILED = [re.compile(p, re.IGNORECASE) for p in LINGUAGEM_VITIMA]


def _compute_identity_metrics(transcription: dict) -> dict:
    """Analisa marcadores linguisticos de identidade no transcript."""
    full_text = transcription.get("full_text", "").lower()
    words = transcription.get("words", [])

    if not full_text:
        return {
            "score": None,
            "confidence": "failed",
            "failure_reason": "identity analysis failed",
            "diagnostico": "dados_insuficientes",
            "vicios_emocionais": {},
            "total_vicios": 0,
            "autoridade_count": 0,
            "vitima_count": 0,
            "autoridade_ratio": 0.5,
            "exemplos": [],
        }

    # Contagem de vicios por categoria
    vicios_count = {}
    exemplos = []
    for categoria, patterns in _VICIOS_COMPILED.items():
        count = 0
        for pattern in patterns:
            for match in pattern.finditer(full_text):
                count += 1
                if len(exemplos) < 5:
                    # Buscar timestamp aproximado
                    ts = _find_timestamp(words, match.start(), full_text)
                    exemplos.append(
                        {
                            "texto": match.group(),
                            "categoria": categoria,
                            "tipo": "vicio_emocional",
                            "timestamp": ts,
                        }
                    )
        vicios_count[categoria] = count

    total_vicios = sum(vicios_count.values())
    vicio_dominante = max(vicios_count, key=vicios_count.get) if total_vicios > 0 else None
    if vicio_dominante and vicios_count[vicio_dominante] == 0:
        vicio_dominante = None

    # Linguagem de autoridade vs vitima
    autoridade_count = 0
    for pattern in _AUTORIDADE_COMPILED:
        autoridade_count += len(pattern.findall(full_text))

    vitima_count = 0
    for pattern in _VITIMA_COMPILED:
        matches = pattern.findall(full_text)
        vitima_count += len(matches)
        for m_text in matches[:3]:
            if len(exemplos) < 8:
                exemplos.append(
                    {
                        "texto": m_text if isinstance(m_text, str) else str(m_text),
                        "categoria": "linguagem_vitima",
                        "tipo": "linguagem",
                        "timestamp": 0,
                    }
                )

    # Ratio de autoridade
    total_markers = autoridade_count + vitima_count
    if total_markers > 0:
        autoridade_ratio = autoridade_count / total_markers
    else:
        autoridade_ratio = 0.5  # neutro

    # Amostra suficiente? Se total de marcadores < 3, score e NEUTRO
    # (nao podemos afirmar identidade firme com 1 marcador)
    MINIMUM_MARKERS = 3
    amostra_suficiente = (total_markers + total_vicios) >= MINIMUM_MARKERS

    if not amostra_suficiente:
        # Dados insuficientes — retornar score neutro
        score = 60
        diagnostico = "dados_insuficientes"
    else:
        # Score: Base 60, penalidade vicios (-5 cada, max -40), bonus/penalidade autoridade
        base = 60
        penalidade_vicios = min(40, total_vicios * 5)
        bonus_autoridade = (autoridade_ratio - 0.5) * 80  # -40 a +40

        score = max(0, min(100, int(base - penalidade_vicios + bonus_autoridade)))

        # Diagnostico
        if score >= 80:
            diagnostico = "identidade_firme"
        elif score >= 60:
            diagnostico = "identidade_media"
        elif score >= 40:
            diagnostico = "identidade_fragil"
        else:
            diagnostico = "identidade_bloqueada"

    logger.info(
        "identity_analysis_complete",
        score=score,
        diagnostico=diagnostico,
        total_vicios=total_vicios,
        autoridade_ratio=round(autoridade_ratio, 2),
    )

    return {
        "score": score,
        "vicios_emocionais": vicios_count,
        "vicio_dominante": vicio_dominante,
        "total_vicios": total_vicios,
        "autoridade_count": autoridade_count,
        "vitima_count": vitima_count,
        "autoridade_ratio": round(autoridade_ratio, 2),
        "exemplos": exemplos[:5],
        "diagnostico": diagnostico,
    }


# Story 8.2 — Truth Contract


def analyze_identity_legacy(transcription: dict) -> dict:
    """Legacy path (TRUTH_CONTRACT_ENABLED=false)."""
    return _compute_identity_metrics(transcription)


def analyze_identity(transcription: dict) -> dict:
    """Legacy alias kept for backwards compat with app.py callers."""
    return _compute_identity_metrics(transcription)


def analyze_identity_tc(transcription: dict) -> "WorkerResult":
    """Truth Contract path (TRUTH_CONTRACT_ENABLED=true)."""
    return wrap_worker_result("identity", _compute_identity_metrics, transcription)


def _find_timestamp(words: list, char_offset: int, full_text: str) -> float:
    """Estima timestamp baseado no offset de caractere no texto."""
    if not words:
        return 0.0

    # Reconstruir texto ate o offset para contar palavras
    text_until = full_text[:char_offset]
    word_count = len(text_until.split())

    if word_count < len(words):
        return words[word_count].get("start", 0.0)
    return words[-1].get("start", 0.0) if words else 0.0
