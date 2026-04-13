"""Opening Analyzer — analisa tecnica de abertura nos primeiros 20% do transcript.

Detecta se o orador usou:
1. Frase de impacto (curta + volume alto)
2. Pergunta reflexiva (? nos primeiros 20%)
3. Dado chocante (numeros, estatisticas)
4. Quebra-gelo (interacao com audiencia)
5. Gancho com historia (narrativa pessoal)
6. Conexao com audiencia (fala diretamente PARA)
7. Citacao de autoridade

Objetivo (mentor): "Fazer com que todas as pessoas parem o que estao fazendo e olhem para voce."
"""

import re

import structlog

logger = structlog.get_logger()

TECNICAS = [
    {
        "id": "pergunta_reflexiva",
        "label": "Pergunta Reflexiva",
        "descricao": "Voce abriu com uma pergunta — isso ativa a curiosidade do ouvinte",
        "detect": "question_mark",
    },
    {
        "id": "dado_chocante",
        "label": "Dado / Estatistica",
        "descricao": "Voce usou dados numericos para gerar impacto na abertura",
        "patterns": [r'\b\d+[%]?\b', r'\b\d+[\.,]\d+\b'],
        "keywords": [r'por ?cento', r'porcento', r'bilh[oõ]', r'milh[oõ]', r'mil\b', r'metade', r'dobro', r'triplo'],
    },
    {
        "id": "quebra_gelo",
        "label": "Quebra-Gelo",
        "descricao": "Voce interagiu diretamente com a audiencia — gera conexao imediata",
        "patterns": [r'quem aqui', r'levant[ae]m?\s+a\s+m[aã]o', r'voc[eê]s j[aá]', r'quantos de voc[eê]s'],
    },
    {
        "id": "gancho_historia",
        "label": "Gancho com Historia",
        "descricao": "Voce abriu com uma narrativa — historias ativam oxitocina (confianca)",
        "patterns": [r'quando eu', r'h[aá] \d+ anos', r'um dia', r'lembro quando', r'imagine', r'era uma vez', r'deixa eu te contar'],
    },
    {
        "id": "conexao_audiencia",
        "label": "Conexao Direta",
        "descricao": "Voce falou diretamente PARA a audiencia — cria sensacao de conversa pessoal",
        "patterns": [r'voc[eê] que est[aá]', r'voc[eê]s que', r'pra voc[eê] que', r'voce que ta'],
    },
    {
        "id": "citacao_autoridade",
        "label": "Citacao de Autoridade",
        "descricao": "Voce referenciou uma autoridade — transfere credibilidade",
        "patterns": [r'como disse', r'segundo\s+\w+', r'nas palavras de'],
    },
]

SUGESTOES = {
    "pergunta_reflexiva": "Pergunte algo que faca a audiencia PENSAR: 'Voce ja parou pra pensar por que a maioria das pessoas tem medo de falar?'",
    "dado_chocante": "Abra com um numero que surpreenda: '93% das pessoas tem medo de falar em publico — mais do que de morrer.'",
    "quebra_gelo": "Interaja direto: 'Quem aqui ja sentiu o coracao disparar antes de falar em publico? Levanta a mao.'",
    "gancho_historia": "Comece com uma historia: 'Quando eu tinha 23 anos, subi num palco pela primeira vez e travei.'",
    "conexao_audiencia": "Fale PARA alguem: 'Voce que esta assistindo isso agora, provavelmente ja passou por isso.'",
    "frase_impacto": "Abra com uma frase curta e forte: 'Poucas coisas custam tanto dinheiro quanto o silencio.'",
    "citacao_autoridade": "Cite alguem respeitado: 'Como disse Warren Buffett: a comunicacao e a habilidade mais subvalorizada do mundo.'",
}


def analyze_opening(transcription: dict, voice_metrics: dict, duration_seconds: float) -> dict:
    """Analisa os primeiros 20% do transcript para detectar tecnicas de abertura."""
    words = transcription.get("words", [])
    full_text = transcription.get("full_text", "")

    if not words or duration_seconds < 10:
        return {"disponivel": False, "motivo": "Video muito curto para analise de abertura"}

    # Pegar primeiros 20% do transcript
    total_words = len(words)
    opening_word_count = max(5, int(total_words * 0.20))
    opening_words = words[:opening_word_count]
    opening_text = " ".join(w["word"] for w in opening_words).lower()
    opening_end_time = opening_words[-1].get("end", 0) if opening_words else 0

    tecnicas_detectadas = []
    tecnicas_ids = set()

    # 1. Pergunta reflexiva
    if "?" in opening_text or any(re.search(p, opening_text, re.IGNORECASE) for p in [r'voc[eê] sabe', r'como funciona', r'j[aá] pensou', r'j[aá] parou', r'ser[aá] que']):
        perguntas = [s.strip() for s in opening_text.split("?") if s.strip()]
        tecnicas_detectadas.append({
            "tecnica": "pergunta_reflexiva",
            "label": "Pergunta Reflexiva",
            "descricao": "Voce abriu com uma pergunta — isso ativa a curiosidade do ouvinte",
            "exemplo": (perguntas[0][:80] + "?") if perguntas else opening_text[:80],
            "qualidade": "boa" if perguntas and len(perguntas[0].split()) >= 5 else "fraca",
        })
        tecnicas_ids.add("pergunta_reflexiva")

    # 2. Dado chocante
    numeros = re.findall(r'\b\d+[%]?\b|\b\d+[\.,]\d+\b', opening_text)
    palavras_impacto = re.findall(r'por ?cento|porcento|bilh[oõ]|milh[oõ]|mil\b|metade|dobro|triplo', opening_text)
    if numeros or palavras_impacto:
        tecnicas_detectadas.append({
            "tecnica": "dado_chocante",
            "label": "Dado / Estatistica",
            "descricao": "Voce usou dados numericos para gerar impacto na abertura",
            "exemplo": f"Numeros usados: {', '.join(numeros[:3])}",
            "qualidade": "boa",
        })
        tecnicas_ids.add("dado_chocante")

    # 3-6. Pattern-based tecnicas
    for tecnica_def in TECNICAS:
        if tecnica_def["id"] in tecnicas_ids:
            continue
        if "patterns" not in tecnica_def:
            continue

        for pattern in tecnica_def["patterns"]:
            match = re.search(pattern, opening_text, re.IGNORECASE)
            if match:
                tecnicas_detectadas.append({
                    "tecnica": tecnica_def["id"],
                    "label": tecnica_def["label"],
                    "descricao": tecnica_def["descricao"],
                    "exemplo": match.group()[:80],
                    "qualidade": "boa",
                })
                tecnicas_ids.add(tecnica_def["id"])
                break

    # 7. Frase de impacto (curta + volume acima da media)
    if "frase_impacto" not in tecnicas_ids:
        primeira_frase = full_text.split(".")[0].strip() if "." in full_text else ""
        if primeira_frase and len(primeira_frase.split()) <= 10:
            volume_windows = voice_metrics.get("volume_por_janela", [])
            if volume_windows and len(volume_windows) > 1:
                media_vol = sum(volume_windows) / len(volume_windows)
                if volume_windows[0] >= media_vol:
                    tecnicas_detectadas.append({
                        "tecnica": "frase_impacto",
                        "label": "Frase de Impacto",
                        "descricao": "Voce abriu com uma frase curta e forte — captura atencao imediata",
                        "exemplo": primeira_frase[:80],
                        "qualidade": "boa",
                    })
                    tecnicas_ids.add("frase_impacto")

    # Score de abertura
    n = len(tecnicas_detectadas)
    if n == 0:
        score = 20
        diagnostico = "abertura_fraca"
        feedback = "Voce comecou falando sem usar nenhuma tecnica de conexao. O objetivo dos primeiros segundos e: fazer TODOS pararem o que estao fazendo e olharem pra voce."
    elif n == 1:
        score = 60
        diagnostico = "abertura_razoavel"
        feedback = f"Voce usou 1 tecnica de abertura ({tecnicas_detectadas[0]['label']}). Bom começo, mas ha espaco pra mais impacto."
    elif n == 2:
        score = 85
        diagnostico = "abertura_forte"
        feedback = f"Voce usou {n} tecnicas de abertura. Abertura profissional."
    else:
        score = 95
        diagnostico = "abertura_excelente"
        feedback = f"Voce usou {n} tecnicas de abertura! Abertura de alto impacto."

    # Bonus combinacoes poderosas
    if "pergunta_reflexiva" in tecnicas_ids and "gancho_historia" in tecnicas_ids:
        score = min(100, score + 10)

    # Sugestoes para tecnicas nao usadas
    tecnicas_ausentes = []
    todas_tecnicas = {"pergunta_reflexiva", "dado_chocante", "quebra_gelo", "gancho_historia", "conexao_audiencia", "frase_impacto", "citacao_autoridade"}
    for t_id in todas_tecnicas - tecnicas_ids:
        if t_id in SUGESTOES and len(tecnicas_ausentes) < 3:
            tecnicas_ausentes.append({
                "tecnica": t_id,
                "sugestao": SUGESTOES[t_id],
            })

    logger.info(
        "opening_analysis_complete",
        score=score,
        diagnostico=diagnostico,
        tecnicas_detectadas=len(tecnicas_detectadas),
    )

    return {
        "disponivel": True,
        "score": score,
        "diagnostico": diagnostico,
        "feedback": feedback,
        "tecnicas_detectadas": tecnicas_detectadas,
        "tecnicas_ausentes": tecnicas_ausentes,
        "opening_text": opening_text[:300],
        "opening_duration_seconds": round(opening_end_time, 1),
    }
