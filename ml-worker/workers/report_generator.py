import json
import time

import google.generativeai as genai
import structlog

import config

logger = structlog.get_logger()

REPORT_PROMPT = """Voce e um coach de comunicacao de nivel mundial. Seu metodo e baseado nos seguintes principios:

## Seus Principios de Coaching

1. **Principio da Variedade**: "Sempre que qualquer coisa se torna padrao, ela se torna nao-funcional." O cerebro desliga quando consegue prever o que vem a seguir. Variedade em TODAS as dimensoes e a chave.

2. **88 Teclas**: A voz e um instrumento. A maioria das pessoas usa apenas 20 teclas — nao porque as outras sao falsas, mas porque sao desconhecidas. Expandir o instrumento = comunicacao autentica.

3. **4 Arquetipos Vocais**: Todo comunicador deve conseguir alternar entre Educador (autoritativo, pausado), Coach (direto, staccato), Motivador (inspiracional, legato) e Amigo (casual, caloroso). Ficar preso em um so = default = nao-funcional.

4. **Regra de Ouro**: "Se algo distrai as pessoas da mensagem, e um problema. Se nao distrai, deixe como esta."

5. **Regra 80/20**: Identifique os 20% de mudancas que geram 80% de melhoria. Nunca de uma lista com mais de 5-6 itens.

6. **Forcas primeiro**: SEMPRE comece reconhecendo o que a pessoa faz BEM antes de dar feedback de melhoria.

7. **Pausas estrategicas**: Silencio apos momentos importantes permite que a audiencia processe. Pausa NAO e fraqueza — e poder.

8. **Peaks and Troughs**: A comunicacao precisa de altos e baixos — volume, velocidade, emocao. Monotonia em qualquer dimensao mata o engajamento.

## Metricas da Avaliacao

Pontuacao Geral: {overall_score}/100

### Variedade Vocal (Pontuacao: {variety_score}/100)
{variety_metrics}

### Voz e Diccao (Pontuacao: {voice_score}/100)
{voice_metrics}

### Presenca Visual (Pontuacao: {gesture_score}/100)
{gesture_metrics}

### Postura e Presenca (Pontuacao: {posture_score}/100)
{posture_metrics}

### Clareza Verbal (Pontuacao: {fillers_score}/100)
{fillers_metrics}

### Arquetipos Vocais (Referencia — nao incluir no feedback por dimensao)
{archetype_metrics}

## Terminologia OBRIGATORIA

Use SEMPRE estes termos no texto gerado (NUNCA use os termos em ingles ou tecnicos entre parenteses):
- "tom" (nunca "pitch")
- "estabilidade corporal" (nunca "grounding")
- "vicios de linguagem" (nunca "fillers")
- "problemas de fluencia" (nunca "clusters de fillers")
- "riqueza de vocabulario" (nunca "diversidade lexical")
- "padroes" (nunca "defaults")
- "pilares travados" (nunca "dimensoes travadas")
- "pontuacao" (nunca "score")
- "palavras por minuto" (nunca "WPM")
- "diccao" (nunca "prosodia")

## Instrucoes CRITICAS

Voce deve gerar o feedback seguindo EXATAMENTE estas regras:
- COMECE com 2-3 forcas genuinas e especificas (nunca generico)
- Use os dados numericos para embasar CADA observacao
- MAXIMO 5 melhorias priorizadas (regra 80/20 — so o que causa maior impacto)
- Cada exercicio deve ter NO MAXIMO 2 frases curtas, formato imperativo: "Faca X. Resultado: Y." Nunca paragrafos longos.
- Use linguagem de coach (direta, calorosa, encorajadora — nunca fria ou clinica)
- Quando mencionar variedade, use a metafora das "88 teclas"
- NAO inclua feedback especifico sobre arquetipos vocais nas dimensoes (e um recurso extra, nao avaliado no score principal). Pode referenciar o conceito dos 4 arquetipos nos principios de coaching quando relevante
- Quando mencionar pausas, diferencie ESTRATEGICAS (boas) de HESITACAO (a melhorar)
- O plano de 12 semanas deve focar UMA habilidade por semana
- NUNCA diga "voce e monotono" — diga "sua fala ficou previsivel em alguns trechos, e podemos adicionar mais variedade"

## Story 7.1 fix — INTERPRETACAO DE METRICAS COM BANDA IDEAL

Algumas metricas usam **banda ideal** (zona certa entre dois extremos), NAO sao "quanto mais melhor".
NUNCA elogie valores extremos. Use sub_scores como verdade, NAO porcentagens brutas.

- **Contato visual:** banda ideal **70-90%**. Acima de 90% = "olhar fixo demais" (intimida). Abaixo de 70% = "pouco contato" (parece evitar).
  - Se eye_contact_pct > 90 OU < 70 → mencionar como melhoria, NAO como forca
  - Se sub_scores.contato_visual >= 80 → forca real
- **Gesticulacao:** banda ideal **40-70%** do tempo. Pouco = sem expressividade. Excesso = distrai.
  - gesto_zona "ideal" → forca. "pouca_variacao" ou "excesso" → melhoria
- **Diversidade arquetipos:** 1 arquetipo em 100% = lock-in (ruim). Variedade entre 4 arquetipos = bom.

Use **sub_scores** para avaliar, NAO valores brutos com pct elevados.

Responda EXCLUSIVAMENTE em JSON valido com esta estrutura:
{{
  "resumo": "Resumo de 3-4 frases: contexto geral, principal forca, principal oportunidade de crescimento. Tom encorajador.",
  "forcas": [
    {{
      "titulo": "Nome da forca",
      "descricao": "O que a pessoa faz bem, com dados numericos de suporte",
      "impacto": "Por que isso e valioso na comunicacao"
    }}
  ],
  "melhorias_80_20": [
    {{
      "titulo": "Nome da melhoria",
      "descricao": "O que precisa mudar, com dados numericos",
      "exercicio": "MAX 2 frases. Formato: acao imperativa + resultado. Ex: 'Grave 1 minuto variando o volume entre sussurro e projecao. Isso desbloqueia sua dinamica vocal.'",
      "prioridade": 1
    }}
  ],
  "dimensoes": {{
    "variedade": {{
      "label": "Excelente|Bom|Moderado|Precisa atencao|Critico",
      "feedback": "Feedback especifico sobre variacao vocal usando 'peaks and troughs' e '88 teclas'",
      "dica": "Dica pratica com exercicio"
    }},
    "voz": {{
      "label": "...",
      "feedback": "Feedback sobre velocidade, volume, pitch, pausas",
      "dica": "..."
    }},
    "presenca_visual": {{
      "label": "...",
      "feedback": "Feedback sobre gestual, contato visual, expressividade",
      "dica": "..."
    }},
    "postura": {{
      "label": "...",
      "feedback": "Feedback sobre postura, grounding, movimento",
      "dica": "..."
    }},
    "clareza_verbal": {{
      "label": "...",
      "feedback": "Feedback sobre vicios de linguagem, distinguindo hesitacao de muletas",
      "dica": "..."
    }}
  }},
  "plano_12_semanas": [
    {{
      "semana": "1-2",
      "foco": "Nome da habilidade",
      "exercicio": "Exercicio especifico",
      "meta": "Como saber que melhorou"
    }}
  ],
  "mensagem_final": "Mensagem encorajadora personalizada, reconhecendo o potencial da pessoa"
}}

Seja especifico, use dados reais, e fale como um coach que acredita genuinamente no potencial do aluno. Responda em portugues do Brasil."""


def _format_metrics(metrics: dict, max_depth: int = 2) -> str:
    """Formata metricas para o prompt, limitando profundidade para clareza."""
    lines = []
    for key, value in metrics.items():
        if key in (
            "fillers",
            "mapa_temporal",
            "estrategicas",
            "hesitacao",
            "respiracao",
        ):
            # Dados muito granulares — resumir
            if isinstance(value, list):
                lines.append(f"- {key}: {len(value)} itens")
            continue
        if isinstance(value, dict) and max_depth > 0:
            lines.append(f"- {key}:")
            for k2, v2 in value.items():
                if isinstance(v2, (dict, list)) and max_depth <= 1:
                    lines.append(f"  - {k2}: [resumido]")
                else:
                    lines.append(f"  - {k2}: {v2}")
        elif isinstance(value, list):
            lines.append(f"- {key}: {json.dumps(value[:10], ensure_ascii=False)}")
        else:
            lines.append(f"- {key}: {value}")
    return "\n".join(lines) if lines else "- Dados indisponiveis"


def _build_context_section(context: dict | None) -> str:
    """Constroi secao de contexto do orador para o prompt (V2 — 6 perguntas)."""
    if not context:
        return ""

    sentimento_map = {
        1: "muito nervoso",
        2: "nervoso",
        3: "neutro",
        4: "confiante",
        5: "muito confiante",
    }

    lines = ["\n\n## CONTEXTO DO ORADOR (questionario pre-avaliacao)"]

    if context.get("sentimento"):
        lines.append(
            f"- Sentimento ao gravar: {sentimento_map.get(context['sentimento'], 'desconhecido')} ({context['sentimento']}/5)"
        )
    if context.get("maior_medo"):
        medos = (
            context["maior_medo"]
            if isinstance(context["maior_medo"], list)
            else [context["maior_medo"]]
        )
        lines.append(f"- Maiores medos: {', '.join(medos)}")
    if context.get("motivacao"):
        motivacoes = (
            context["motivacao"]
            if isinstance(context["motivacao"], list)
            else [context["motivacao"]]
        )
        lines.append(f"- Motivacao para melhorar: {', '.join(motivacoes)}")
    if context.get("avaliado_antes") is not None:
        lines.append(
            f"- Ja se avaliou antes: {'sim' if context['avaliado_antes'] else 'nao, primeira vez'}"
        )
    if context.get("desejo_transmitir"):
        desejos = (
            context["desejo_transmitir"]
            if isinstance(context["desejo_transmitir"], list)
            else [context["desejo_transmitir"]]
        )
        lines.append(f"- Deseja transmitir: {', '.join(desejos)}")
    if context.get("desejo_melhorar"):
        melhorar = (
            context["desejo_melhorar"]
            if isinstance(context["desejo_melhorar"], list)
            else [context["desejo_melhorar"]]
        )
        lines.append(f"- Quer melhorar: {', '.join(melhorar)}")

    lines.append("")
    lines.append("INSTRUCOES DE ADAPTACAO:")
    lines.append(
        "1. SENTIMENTO: Se nervoso (1-2), tom EXTRA encorajador. Se confiante (4-5), mais direto/desafiador."
    )
    lines.append(
        "2. MEDOS: Enderece pelo menos 1 medo mencionado no feedback — mostre que a avaliacao ajuda a superar."
    )
    lines.append(
        "3. MOTIVACAO: Conecte o feedback ao MOTIVO do orador. Se quer 'vender mais', linke melhoria a resultado."
    )
    lines.append(
        "4. PRIMEIRA VEZ: Se nao se avaliou antes, explique brevemente o que cada metrica significa."
    )
    lines.append(
        "5. DESEJO_TRANSMITIR: Avalie se a comunicacao REALMENTE transmite o que o orador quer. Se quer 'autoridade' mas usa linguagem hesitante, aponte o gap."
    )
    lines.append(
        "6. DESEJO_MELHORAR: Priorize feedback nas dimensoes que o orador PEDIU. Comece por elas."
    )

    return "\n".join(lines)


def _build_cross_insights(aggregated: dict) -> list[str]:
    """Gera insights cruzados pre-calculados combinando 2+ metricas."""
    insights = []
    scores = aggregated.get("dimension_scores", {})
    metrics = aggregated.get("detailed_metrics", {})
    voice = metrics.get("voice", {})
    gesture = metrics.get("gesture", {})
    posture = metrics.get("posture", {})
    variety = metrics.get("variety", {})
    fillers = metrics.get("fillers", {})
    archetypes = metrics.get("archetypes", {})
    temporal = aggregated.get("temporal", {})

    # X01: Instrumento rico sub-utilizado
    pitch_range = voice.get("pitch_range_semitones", 0)
    cv_pitch = voice.get("cv_pitch", 0)
    if pitch_range >= 15 and cv_pitch < 0.08:
        insights.append(
            f"INSIGHT CRITICO: orador tem range de tom de {pitch_range} semitons "
            f"(instrumento rico) mas CV pitch de {cv_pitch} (praticamente plano). "
            f"Metafora: voce tem um Ferrari e dirige na segunda marcha."
        )

    # X02: Fala rapida + uniforme
    wpm = voice.get("wpm", 0)
    cv_vel = voice.get("cv_velocidade", 0)
    if wpm > 170 and cv_vel < 0.10:
        insights.append(
            f"INSIGHT CRITICO: fala a {wpm} WPM (acima do ideal 130-170) E sem variacao "
            f"(CV {cv_vel}). Dois problemas que se amplificam — rapidez sem respiro."
        )

    # X03: Gesticula muito fora da zona
    gest_pct = gesture.get("gesticulation_pct", 0)
    zona = gesture.get("zona_ideal_pct", 100)
    if gest_pct >= 90 and zona < 30:
        insights.append(
            f"INSIGHT: gesticula {gest_pct}% do tempo mas apenas {zona}% na zona ideal "
            f"(peito-cintura). O gesto e ruido visual, nao enfase."
        )

    # X04: Friend + volume alto
    arq_dom = archetypes.get("arquetipo_dominante", "")
    vol_base = voice.get("volume_base_1_10", 0)
    if arq_dom == "amigo" and vol_base > 8:
        insights.append(
            f"INSIGHT: lock-in no arquetipo Amigo (casual) mas com volume {vol_base}/10. "
            f"Amigo deveria ser caloroso e calmo — nao gritando."
        )

    # X05: Olhar fixo num ponto
    eye = gesture.get("eye_contact_pct", 0)
    dist_olhar = gesture.get("distribuicao_olhar", 1)
    if eye >= 95 and dist_olhar < 0.3:
        insights.append(
            f"INSIGHT: contato visual excelente ({eye}%) mas olhar fixo em um ponto "
            f"(distribuicao {dist_olhar}). Falta distribuir para toda a audiencia."
        )

    # X06: Postura boa mas instavel
    align = posture.get("alignment_score", 0)
    ground = posture.get("grounding_score", 100)
    if align >= 80 and ground < 50:
        insights.append(
            f"INSIGHT: postura alinhada ({align}) mas instavel ({ground}). "
            f"O corpo esta certo mas os pes nao estao firmes."
        )

    # X07: Monotono APESAR de ter range
    pct_mono = variety.get("pct_tempo_monotono", 0)
    if pct_mono > 70 and pitch_range >= 12:
        insights.append(
            f"INSIGHT CRITICO: monotono em {pct_mono}% do tempo APESAR de ter range "
            f"vocal de {pitch_range} semitons. O instrumento esta ali — voce escolheu nao usar."
        )

    # X08: Vicios substituem pausas
    fpm = fillers.get("fillers_per_minute", 0)
    pausas = voice.get("pausas", {})
    qtd_estr = pausas.get("qtd_estrategicas", 0)
    if fpm > 5 and qtd_estr < 2:
        insights.append(
            f"INSIGHT: {fpm} vicios/min e apenas {qtd_estr} pausas estrategicas. "
            f"Os vicios SUBSTITUEM as pausas — quando deveria ter silencio, voce preenche."
        )

    # X09: Voz razoavel mas variedade baixa
    voice_score = scores.get("voice", 0)
    variety_score = scores.get("variety", 0)
    if voice_score >= 60 and variety_score < 30:
        insights.append(
            f"INSIGHT: voz tecnicamente razoavel ({voice_score}) mas variedade muito baixa "
            f"({variety_score}). Voce tem a tecnica mas a usa de forma monotona."
        )

    # X10: Abertura fraca mas pico no meio
    por_terco = temporal.get("por_terco", {})
    ab = por_terco.get("abertura", {}).get("score", 0)
    meio = por_terco.get("meio", {}).get("score", 0)
    if ab and meio and ab < 50 and meio >= 70:
        insights.append(
            f"INSIGHT: abriu fraco ({ab}) mas pegou forca no meio ({meio}). "
            f"Voce demora pra esquentar — vamos trabalhar a abertura."
        )

    return insights


def _rank_problems(aggregated: dict) -> list[dict]:
    """Rankeia problemas do orador por impacto real (weight × severity)."""
    PROBLEM_DEFS = [
        {
            "key": "voice.cv_volume",
            "threshold": 0.05,
            "op": "<",
            "weight": 10,
            "label": "Volume uniforme (sem peaks and troughs)",
        },
        {
            "key": "variety.pct_tempo_monotono",
            "threshold": 50,
            "op": ">",
            "weight": 10,
            "label": "Fala previsivel/monotona",
        },
        {
            "key": "voice.cv_pitch",
            "threshold": 0.08,
            "op": "<",
            "weight": 9,
            "label": "Tom de voz sem variacao",
        },
        {
            "key": "archetypes.lock_in",
            "threshold": True,
            "op": "==",
            "weight": 8,
            "label": "Lock-in em 1 arquetipo vocal",
        },
        {
            "key": "voice.wpm",
            "threshold": 170,
            "op": ">",
            "weight": 7,
            "label": "Velocidade de fala acima do ideal",
        },
        {
            "key": "temporal.por_terco.abertura.score",
            "threshold": 50,
            "op": "<",
            "weight": 7,
            "label": "Abertura fraca (perde audiencia logo no inicio)",
        },
        {
            "key": "gesture.zona_ideal_pct",
            "threshold": 30,
            "op": "<",
            "weight": 6,
            "label": "Gestos fora da zona de poder",
        },
        {
            "key": "voice.pausas.ratio_estrategicas",
            "threshold": 0.2,
            "op": "<",
            "weight": 6,
            "label": "Poucas pausas estrategicas",
        },
        {
            "key": "gesture.gesto_repetitivo",
            "threshold": True,
            "op": "==",
            "weight": 5,
            "label": "Gesto repetitivo (default gestual)",
        },
        {
            "key": "fillers.fillers_per_minute",
            "threshold": 4,
            "op": ">",
            "weight": 5,
            "label": "Vicios de linguagem frequentes",
        },
        {
            "key": "posture.grounding_score",
            "threshold": 50,
            "op": "<",
            "weight": 4,
            "label": "Instabilidade corporal",
        },
    ]

    metrics = aggregated.get("detailed_metrics", {})

    def _get_value(key: str):
        parts = key.split(".")
        obj = metrics
        for p in parts:
            if isinstance(obj, dict):
                obj = obj.get(p)
            else:
                return None
        return obj

    problems = []
    for defn in PROBLEM_DEFS:
        value = _get_value(defn["key"])
        if value is None:
            continue

        threshold = defn["threshold"]
        op = defn["op"]
        is_problem = False

        if op == "<" and isinstance(value, (int, float)):
            is_problem = value < threshold
        elif op == ">" and isinstance(value, (int, float)):
            is_problem = value > threshold
        elif op == "==":
            is_problem = value == threshold

        if is_problem:
            if isinstance(value, (int, float)) and isinstance(threshold, (int, float)):
                severity = abs(value - threshold) / max(abs(threshold), 1)
            else:
                severity = 1.0

            priority = defn["weight"] * severity
            level = (
                "CRITICO"
                if priority > 8
                else "ALTO"
                if priority > 5
                else "MEDIO"
                if priority > 3
                else "BAIXO"
            )

            problems.append(
                {
                    "label": defn["label"],
                    "value": value,
                    "threshold": threshold,
                    "weight": defn["weight"],
                    "severity": round(severity, 2),
                    "priority": round(priority, 2),
                    "level": level,
                }
            )

    problems.sort(key=lambda p: p["priority"], reverse=True)
    return problems[:6]


def generate_report(aggregated: dict, context: dict | None = None) -> dict:
    """Gera relatorio qualitativo de coaching usando Gemini."""
    start = time.time()
    logger.info("report_generation_start")

    genai.configure(api_key=config.GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash")

    dimension_scores = aggregated.get("dimension_scores", {})
    detailed = aggregated.get("detailed_metrics", {})
    incomplete = aggregated.get("incomplete_dimensions", [])

    # Guard rails: instrucao ao LLM para nao dar coaching em dimensoes com baixa confianca
    guard_rails = ""
    if incomplete:
        dims_str = ", ".join(incomplete)
        guard_rails = (
            f"\n\n## ATENCAO — Dimensoes com Confianca Baixa\n"
            f"As seguintes dimensoes tiveram confianca BAIXA ou FALHARAM na analise: {dims_str}\n"
            f"NAO de coaching especifico sobre essas dimensoes. "
            f"Apenas mencione brevemente que a analise foi inconclusiva e sugira regravar com melhor qualidade de video/audio.\n"
        )

    prompt = REPORT_PROMPT.format(
        overall_score=aggregated.get("overall_score", 0),
        variety_score=dimension_scores.get("variety", 0),
        variety_metrics=_format_metrics(detailed.get("variety", {})),
        voice_score=dimension_scores.get("voice", 0),
        voice_metrics=_format_metrics(detailed.get("voice", {})),
        gesture_score=dimension_scores.get("gesture", 0),
        gesture_metrics=_format_metrics(detailed.get("gesture", {})),
        posture_score=dimension_scores.get("posture", 0),
        posture_metrics=_format_metrics(detailed.get("posture", {})),
        fillers_score=dimension_scores.get("fillers", 0),
        fillers_metrics=_format_metrics(detailed.get("fillers", {})),
        archetype_score=dimension_scores.get("archetypes", 0),
        archetype_metrics=_format_metrics(detailed.get("archetypes", {})),
    )

    # Hierarquia de problemas (ranking por impacto)
    problems = _rank_problems(aggregated)
    if problems:
        prompt += "\n\n## HIERARQUIA DE PROBLEMAS (rankeados por impacto — 80/20)\n"
        for i, p in enumerate(problems, 1):
            prompt += f"#{i} {p['level']} — {p['label']} (valor: {p['value']}, ideal: {p['threshold']})\n"
        prompt += "\nINSTRUCAO: concentre 80% do feedback nos problemas #1 e #2. O orador SAI com 1 prioridade: o problema #1.\n"

    # Insights cruzados
    insights = _build_cross_insights(aggregated)
    if insights:
        prompt += (
            "\n\n## INSIGHTS PRE-CALCULADOS (cruzamento de metricas — USE como base)\n"
        )
        for insight in insights:
            prompt += f"- {insight}\n"
        prompt += "\nINSTRUCAO: use esses insights como BASE do feedback. NAO copie literal — reescreva no seu tom de coach.\n"

    # Identidade comunicativa (Story 6.8)
    identity = aggregated.get("identity", {})
    if identity.get("score") is not None and identity.get("diagnostico") != "failed":
        prompt += "\n\n## IDENTIDADE COMUNICATIVA DO ORADOR\n"
        prompt += f"Score de identidade: {identity['score']}/100 ({identity.get('diagnostico', '')})\n"
        prompt += f"Linguagem de autoridade: {identity.get('autoridade_count', 0)} marcadores ({identity.get('autoridade_ratio', 0):.0%})\n"
        prompt += f"Linguagem de vitima: {identity.get('vitima_count', 0)} marcadores\n"
        total_vicios = identity.get("total_vicios", 0)
        if total_vicios > 0:
            prompt += f"Vicios emocionais detectados: {total_vicios} (dominante: {identity.get('vicio_dominante', 'nenhum')})\n"
        exemplos = identity.get("exemplos", [])
        if exemplos:
            prompt += (
                "Exemplos: " + ", ".join(f'"{e["texto"]}"' for e in exemplos[:3]) + "\n"
            )
        prompt += "\nINSTRUCAO: Se identidade_bloqueada ou identidade_fragil, aborde PRIMEIRO — antes de tecnica.\n"
        prompt += "Cruze com desejo_transmitir do questionario: se orador quer 'autoridade' mas linguagem indica vitima, aponte o gap.\n"

    # Analise de abertura (Story 6.10)
    opening = aggregated.get("opening", {})
    if opening.get("disponivel"):
        prompt += "\n\n## ANALISE DE ABERTURA\n"
        prompt += f"Score de abertura: {opening['score']}/100 ({opening.get('diagnostico', '')})\n"
        tecnicas = opening.get("tecnicas_detectadas", [])
        if tecnicas:
            prompt += (
                "Tecnicas detectadas: " + ", ".join(t["label"] for t in tecnicas) + "\n"
            )
        else:
            prompt += "Tecnicas detectadas: NENHUMA\n"
        prompt += f"Feedback: {opening.get('feedback', '')}\n"
        ausentes = opening.get("tecnicas_ausentes", [])
        if ausentes:
            prompt += "Sugestoes de tecnicas nao usadas:\n"
            for a in ausentes:
                prompt += f"- {a['sugestao']}\n"
        prompt += "\nINSTRUCAO: Se abertura_fraca, comece o feedback por isso. A abertura e o momento mais critico.\n"

    if guard_rails:
        prompt += guard_rails

    context_section = _build_context_section(context)
    if context_section:
        prompt += context_section

    # Dados de congruencia
    congruence = aggregated.get("congruence", {})
    if congruence.get("contradicoes"):
        prompt += "\n\n## Congruencia Entre Canais\n"
        prompt += f"Score de congruencia: {congruence.get('score', '?')}/100 ({congruence.get('diagnostico', '')})\n"
        prompt += "Contradicoes detectadas:\n"
        for c in congruence["contradicoes"]:
            prompt += f"- {c['descricao']}\n"
        prompt += "\nMencione as incongruencias de forma construtiva — o orador pode nao estar ciente que corpo e voz enviam mensagens diferentes.\n"

    # Dados temporais (3 tercos)
    temporal = aggregated.get("temporal", {})
    if temporal.get("disponivel"):
        tercos = temporal.get("por_terco", {})
        prompt += "\n\n## Arco Temporal da Performance\n"
        prompt += f"Padrao detectado: {temporal.get('padrao', 'desconhecido')} — {temporal.get('padrao_descricao', '')}\n"
        for label in ["abertura", "meio", "fechamento"]:
            t = tercos.get(label, {})
            prompt += f"- {label.capitalize()}: score {t.get('score', '?')}, fillers {t.get('fillers', 0)}, trechos monotonos {t.get('trechos_monotonos', 0)}\n"
        prompt += "\nComente sobre o arco temporal: o orador mantem energia, perde no meio, ou constroi crescendo?\n"

    last_error = None
    for attempt in range(3):
        try:
            response = model.generate_content(prompt)
            text = response.text.strip()

            # Limpar blocos de codigo markdown
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
            if text.endswith("```"):
                text = text.rsplit("```", 1)[0]
            text = text.strip()

            report = json.loads(text)

            elapsed = time.time() - start
            logger.info(
                "report_generation_complete",
                duration_seconds=round(elapsed, 2),
                attempt=attempt + 1,
            )

            return {
                "resumo": report.get("resumo", ""),
                "forcas": report.get("forcas", []),
                "melhorias_80_20": report.get("melhorias_80_20", []),
                "dimensoes": report.get("dimensoes", {}),
                "plano_12_semanas": report.get("plano_12_semanas", []),
                "mensagem_final": report.get("mensagem_final", ""),
                # Retrocompatibilidade
                "summary": report.get("resumo", ""),
                "dimension_feedback": report.get("dimensoes", {}),
                "llm_model": "gemini-2.5-flash",
                "llm_cost_usd": 0.0,
            }

        except json.JSONDecodeError as e:
            logger.warning(
                "report_json_parse_failed",
                attempt=attempt + 1,
                error=str(e),
            )
            last_error = e
        except Exception as e:
            logger.warning(
                "report_generation_attempt_failed",
                attempt=attempt + 1,
                error=str(e),
            )
            last_error = e
            time.sleep(2**attempt)

    logger.error("report_generation_failed", error=str(last_error))
    raise RuntimeError(f"Geracao de relatorio falhou apos 3 tentativas: {last_error}")
