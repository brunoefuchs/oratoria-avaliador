"""Report Generator — coaching report com Gemini.

Story 8.5 (Truth Contract): reescrita para aceitar AggregatedMetrics (Pydantic),
corrigir score=None → "INDISPONIVEL" no prompt (nao "0/100"), usar Gemini JSON mode,
retry com temperatura variavel, remover retrocompat fields.

Duas funcoes publicas:
  - generate_report(metrics, context)  → path Truth Contract (flag ON)
  - generate_report_legacy(aggregated, context) → path legacy preservado 100% intacto
"""

import json
import time

import google.generativeai as genai
import structlog

import config
from contracts.aggregated_metrics import AggregatedMetrics

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

Pontuacao Geral: {overall_score}

### Variedade Vocal (Pontuacao: {variety_score})
{variety_metrics}

### Voz e Diccao (Pontuacao: {voice_score})
{voice_metrics}

### Presenca Visual (Pontuacao: {gesture_score})
{gesture_metrics}

### Postura e Presenca (Pontuacao: {posture_score})
{posture_metrics}

### Clareza Verbal (Pontuacao: {fillers_score})
{fillers_metrics}

### Expressao Facial (Pontuacao: {facial_score})
{facial_metrics}

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
{{{{
  "resumo": "Resumo de 3-4 frases: contexto geral, principal forca, principal oportunidade de crescimento. Tom encorajador.",
  "forcas": [
    {{{{
      "titulo": "Nome da forca",
      "descricao": "O que a pessoa faz bem, com dados numericos de suporte",
      "impacto": "Por que isso e valioso na comunicacao"
    }}}}
  ],
  "melhorias_80_20": [
    {{{{
      "titulo": "Nome da melhoria",
      "descricao": "O que precisa mudar, com dados numericos",
      "exercicio": "MAX 2 frases. Formato: acao imperativa + resultado. Ex: 'Grave 1 minuto variando o volume entre sussurro e projecao. Isso desbloqueia sua dinamica vocal.'",
      "prioridade": 1
    }}}}
  ],
  "dimensoes": {{{{
    "variedade": {{{{
      "label": "Excelente|Bom|Moderado|Precisa atencao|Critico",
      "feedback": "Feedback especifico sobre variacao vocal usando 'peaks and troughs' e '88 teclas'",
      "dica": "Dica pratica com exercicio"
    }}}},
    "voz": {{{{
      "label": "...",
      "feedback": "Feedback sobre velocidade, volume, pitch, pausas",
      "dica": "..."
    }}}},
    "presenca_visual": {{{{
      "label": "...",
      "feedback": "Feedback sobre gestual, contato visual, expressividade",
      "dica": "..."
    }}}},
    "postura": {{{{
      "label": "...",
      "feedback": "Feedback sobre postura, grounding, movimento",
      "dica": "..."
    }}}},
    "clareza_verbal": {{{{
      "label": "...",
      "feedback": "Feedback sobre vicios de linguagem, distinguindo hesitacao de muletas",
      "dica": "..."
    }}}},
    "expressao_facial": {{{{
      "label": "...",
      "feedback": "Feedback sobre sorriso, sobrancelhas, micro-expressoes e textura emocional do rosto",
      "dica": "..."
    }}}}
  }}}},
  "plano_12_semanas": [
    {{{{
      "semana": "1-2",
      "foco": "Nome da habilidade",
      "exercicio": "Exercicio especifico",
      "meta": "Como saber que melhorou"
    }}}}
  ],
  "mensagem_final": "Mensagem encorajadora personalizada, reconhecendo o potencial da pessoa"
}}}}

Seja especifico, use dados reais, e fale como um coach que acredita genuinamente no potencial do aluno. Responda em portugues do Brasil."""


def _format_metrics(metrics: dict, max_depth: int = 2) -> str:
    """Formata metricas para o prompt, limitando profundidade para clareza."""
    lines = []
    for key, value in metrics.items():
        if key in ("fillers", "mapa_temporal", "estrategicas", "hesitacao", "respiracao"):
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
        sentimento_val = context["sentimento"]
        sentimento_desc = sentimento_map.get(sentimento_val, "desconhecido")
        lines.append(f"- Sentimento ao gravar: {sentimento_desc} ({sentimento_val}/5)")
    if context.get("maior_medo"):
        medos = (
            context["maior_medo"]
            if isinstance(context["maior_medo"], list)
            else [context["maior_medo"]]
        )
        lines.append("- Maiores medos: " + ", ".join(medos))
    if context.get("motivacao"):
        motivacoes = (
            context["motivacao"]
            if isinstance(context["motivacao"], list)
            else [context["motivacao"]]
        )
        lines.append("- Motivacao para melhorar: " + ", ".join(motivacoes))
    if context.get("avaliado_antes") is not None:
        avaliado_str = "sim" if context["avaliado_antes"] else "nao, primeira vez"
        lines.append(f"- Ja se avaliou antes: {avaliado_str}")
    if context.get("desejo_transmitir"):
        desejos = (
            context["desejo_transmitir"]
            if isinstance(context["desejo_transmitir"], list)
            else [context["desejo_transmitir"]]
        )
        lines.append("- Deseja transmitir: " + ", ".join(desejos))
    if context.get("desejo_melhorar"):
        melhorar = (
            context["desejo_melhorar"]
            if isinstance(context["desejo_melhorar"], list)
            else [context["desejo_melhorar"]]
        )
        lines.append("- Quer melhorar: " + ", ".join(melhorar))

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

    pitch_range = voice.get("pitch_range_semitones", 0) or 0
    cv_pitch = voice.get("cv_pitch", 0) or 0
    if pitch_range >= 15 and cv_pitch < 0.08:
        insights.append(
            f"INSIGHT CRITICO: orador tem range de tom de {pitch_range} semitons "
            f"(instrumento rico) mas CV pitch de {cv_pitch} (praticamente plano). "
            f"Metafora: voce tem um Ferrari e dirige na segunda marcha."
        )

    wpm = voice.get("wpm", 0) or 0
    cv_vel = voice.get("cv_velocidade", 0) or 0
    if wpm > 170 and cv_vel < 0.10:
        insights.append(
            f"INSIGHT CRITICO: fala a {wpm} WPM (acima do ideal 130-170) E sem variacao "
            f"(CV {cv_vel}). Dois problemas que se amplificam — rapidez sem respiro."
        )

    gest_pct = gesture.get("gesticulation_pct", 0) or 0
    zona = gesture.get("zona_ideal_pct", 100) or 100
    if gest_pct >= 90 and zona < 30:
        insights.append(
            f"INSIGHT: gesticula {gest_pct}% do tempo mas apenas {zona}% na zona ideal "
            f"(peito-cintura). O gesto e ruido visual, nao enfase."
        )

    arq_dom = archetypes.get("arquetipo_dominante", "")
    vol_base = voice.get("volume_base_1_10", 0) or 0
    if arq_dom == "amigo" and vol_base > 8:
        insights.append(
            f"INSIGHT: lock-in no arquetipo Amigo (casual) mas com volume {vol_base}/10. "
            f"Amigo deveria ser caloroso e calmo — nao gritando."
        )

    eye = gesture.get("eye_contact_pct", 0) or 0
    dist_olhar = gesture.get("distribuicao_olhar", 1) or 1
    if eye >= 95 and dist_olhar < 0.3:
        insights.append(
            f"INSIGHT: contato visual excelente ({eye}%) mas olhar fixo em um ponto "
            f"(distribuicao {dist_olhar}). Falta distribuir para toda a audiencia."
        )

    align = posture.get("alignment_score", 0) or 0
    ground = posture.get("grounding_score", 100) or 100
    if align >= 80 and ground < 50:
        insights.append(
            f"INSIGHT: postura alinhada ({align}) mas instavel ({ground}). "
            f"O corpo esta certo mas os pes nao estao firmes."
        )

    pct_mono = variety.get("pct_tempo_monotono", 0) or 0
    if pct_mono > 70 and pitch_range >= 12:
        insights.append(
            f"INSIGHT CRITICO: monotono em {pct_mono}% do tempo APESAR de ter range "
            f"vocal de {pitch_range} semitons. O instrumento esta ali — voce escolheu nao usar."
        )

    fpm = fillers.get("fillers_per_minute", 0) or 0
    pausas = voice.get("pausas", {})
    qtd_estr = (pausas or {}).get("qtd_estrategicas", 0) or 0
    if fpm > 5 and qtd_estr < 2:
        insights.append(
            f"INSIGHT: {fpm} vicios/min e apenas {qtd_estr} pausas estrategicas. "
            f"Os vicios SUBSTITUEM as pausas — quando deveria ter silencio, voce preenche."
        )

    voice_score = scores.get("voice")
    variety_score = scores.get("variety")
    if voice_score is not None and variety_score is not None:
        if voice_score >= 60 and variety_score < 30:
            insights.append(
                f"INSIGHT: voz tecnicamente razoavel ({voice_score}) mas variedade muito baixa "
                f"({variety_score}). Voce tem a tecnica mas a usa de forma monotona."
            )

    por_terco = (temporal or {}).get("por_terco", {})
    ab = (por_terco or {}).get("abertura", {})
    meio = (por_terco or {}).get("meio", {})
    ab_score = (ab or {}).get("score")
    meio_score = (meio or {}).get("score")
    if ab_score is not None and meio_score is not None and ab_score < 50 and meio_score >= 70:
        insights.append(
            f"INSIGHT: abriu fraco ({ab_score}) mas pegou forca no meio ({meio_score}). "
            f"Voce demora pra esquentar — vamos trabalhar a abertura."
        )

    return insights


def _rank_problems(aggregated: dict) -> list[dict]:
    """Rankeia problemas do orador por impacto real (weight x severity)."""
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


def _score_label(score: int | None, dim_name: str, incomplete_dimensions: list[str]) -> str:
    """Retorna string honesta para o score: 'X/100' ou 'INDISPONIVEL'.

    V9 do audit: nunca escrever 'X: 0/100' quando score eh None.
    """
    if score is None or dim_name in incomplete_dimensions:
        return "INDISPONIVEL (analise falhou)"
    return f"{score}/100"


def _build_prompt(metrics: AggregatedMetrics, context: dict | None = None) -> str:
    """Constroi o prompt honesto para o Gemini.

    Funcao pura e testavel — nao chama Gemini. Garante que:
    - overall_score None → "INDISPONIVEL (N/total dimensoes falharam)"
    - dimension_scores None → "INDISPONIVEL" na dimensao correspondente
    - Identity com dimension_status != "ok" → secao identidade omitida
    - Nunca score ausente como "0/100"

    Vetos V9 e V10 fechados aqui.
    """
    dimension_scores = metrics.dimension_scores
    detailed = metrics.detailed_metrics
    incomplete = metrics.incomplete_dimensions

    if metrics.overall_score is None:
        n_failed = len(incomplete)
        total_scoring = 6
        overall_str = f"INDISPONIVEL ({n_failed}/{total_scoring} dimensoes falharam)"
    else:
        overall_str = f"{metrics.overall_score}/100"

    variety_str = _score_label(dimension_scores.get("variety"), "variety", incomplete)
    voice_str = _score_label(dimension_scores.get("voice"), "voice", incomplete)
    gesture_str = _score_label(dimension_scores.get("gesture"), "gesture", incomplete)
    posture_str = _score_label(dimension_scores.get("posture"), "posture", incomplete)
    fillers_str = _score_label(dimension_scores.get("fillers"), "fillers", incomplete)
    facial_str = _score_label(dimension_scores.get("facial"), "facial", incomplete)
    archetype_str = _score_label(dimension_scores.get("archetypes"), "archetypes", incomplete)

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
        overall_score=overall_str,
        variety_score=variety_str,
        variety_metrics=_format_metrics(detailed.get("variety", {})),
        voice_score=voice_str,
        voice_metrics=_format_metrics(detailed.get("voice", {})),
        gesture_score=gesture_str,
        gesture_metrics=_format_metrics(detailed.get("gesture", {})),
        posture_score=posture_str,
        posture_metrics=_format_metrics(detailed.get("posture", {})),
        fillers_score=fillers_str,
        fillers_metrics=_format_metrics(detailed.get("fillers", {})),
        facial_score=facial_str,
        facial_metrics=_format_metrics(detailed.get("facial", {})),
        archetype_score=archetype_str,
        archetype_metrics=_format_metrics(detailed.get("archetypes", {})),
    )

    _aggregated_dict = metrics.model_dump()
    problems = _rank_problems(_aggregated_dict)
    if problems:
        prompt += "\n\n## HIERARQUIA DE PROBLEMAS (rankeados por impacto — 80/20)\n"
        for i, p in enumerate(problems, 1):
            prompt += (
                f"#{i} {p['level']} — {p['label']} (valor: {p['value']}, ideal: {p['threshold']})\n"
            )
        prompt += "\nINSTRUCAO: concentre 80% do feedback nos problemas #1 e #2. O orador SAI com 1 prioridade: o problema #1.\n"

    insights = _build_cross_insights(_aggregated_dict)
    if insights:
        prompt += "\n\n## INSIGHTS PRE-CALCULADOS (cruzamento de metricas — USE como base)\n"
        for insight in insights:
            prompt += f"- {insight}\n"
        prompt += "\nINSTRUCAO: use esses insights como BASE do feedback. NAO copie literal — reescreva no seu tom de coach.\n"

    # Story 9.1 (Epic 9): confidence awareness + secondary dims section.
    # So injetado quando STATE_OF_ART_ENABLED=true (aggregator populou esses campos).
    confidence = metrics.dimension_confidence
    if confidence:
        prompt += "\n\n## CONFIANCA DAS MEDICOES (Epic 9 — calibracao mentor)\n"
        alta = [d for d, c in confidence.items() if c == "alta" and d in dimension_scores]
        media = [d for d, c in confidence.items() if c == "media" and d in dimension_scores]
        if alta:
            prompt += f"🟢 Alta (ML validado, >85%): {', '.join(alta)}\n"
        if media:
            prompt += f"🟡 Media (heuristica sobre features confiaveis): {', '.join(media)}\n"

        baixa_secondary = [
            d
            for d, c in confidence.items()
            if c == "baixa" and d in detailed and d not in dimension_scores
        ]
        if baixa_secondary:
            prompt += (
                f"🔴 Baixa (regex PT-BR — analise complementar): {', '.join(baixa_secondary)}\n"
                "INSTRUCAO: trate dims 🔴 como SUGESTAO, nao afirmacao. Use linguagem hedge "
                "('parece indicar', 'pode sugerir'). NAO faca coaching prescritivo em 🔴.\n"
            )

    identity = metrics.identity
    if identity is not None:
        _identity_status = identity.get("dimension_status", "")
        _identity_ok = _identity_status == "ok"
        if _identity_ok:
            _identity_score = identity.get("score")
            _identity_metrics = identity.get("metrics", {})
            if _identity_metrics:
                prompt += "\n\n## IDENTIDADE COMUNICATIVA DO ORADOR\n"
                if _identity_score is not None:
                    diagnostico = _identity_metrics.get("diagnostico", "")
                    prompt += f"Score de identidade: {_identity_score}/100 ({diagnostico})\n"
                autoridade_count = _identity_metrics.get("autoridade_count", 0)
                autoridade_ratio = _identity_metrics.get("autoridade_ratio", 0)
                vitima_count = _identity_metrics.get("vitima_count", 0)
                prompt += f"Linguagem de autoridade: {autoridade_count} marcadores ({autoridade_ratio:.0%})\n"
                prompt += f"Linguagem de vitima: {vitima_count} marcadores\n"
                total_vicios = _identity_metrics.get("total_vicios", 0)
                if total_vicios:
                    vicio_dominante = _identity_metrics.get("vicio_dominante", "nenhum")
                    prompt += f"Vicios emocionais detectados: {total_vicios} (dominante: {vicio_dominante})\n"
                exemplos = _identity_metrics.get("exemplos", [])
                if exemplos:
                    exemplos_str = ", ".join('"' + e["texto"] + '"' for e in exemplos[:3])
                    prompt += "Exemplos: " + exemplos_str + "\n"
                prompt += "\nINSTRUCAO: Se identidade_bloqueada ou identidade_fragil, aborde PRIMEIRO — antes de tecnica.\n"
                prompt += "Cruze com desejo_transmitir do questionario: se orador quer 'autoridade' mas linguagem indica vitima, aponte o gap.\n"

    opening = metrics.opening
    if opening is not None:
        _opening_status = opening.get("dimension_status", "")
        if _opening_status == "ok":
            _opening_metrics = opening.get("metrics", {})
            if _opening_metrics and _opening_metrics.get("disponivel"):
                prompt += "\n\n## ANALISE DE ABERTURA\n"
                opening_score = opening.get("score")
                opening_diag = _opening_metrics.get("diagnostico", "")
                prompt += f"Score de abertura: {opening_score}/100 ({opening_diag})\n"
                tecnicas = _opening_metrics.get("tecnicas_detectadas", [])
                if tecnicas:
                    prompt += (
                        "Tecnicas detectadas: " + ", ".join(t["label"] for t in tecnicas) + "\n"
                    )
                else:
                    prompt += "Tecnicas detectadas: NENHUMA\n"
                opening_feedback = _opening_metrics.get("feedback", "")
                prompt += f"Feedback: {opening_feedback}\n"
                ausentes = _opening_metrics.get("tecnicas_ausentes", [])
                if ausentes:
                    prompt += "Sugestoes de tecnicas nao usadas:\n"
                    for a in ausentes:
                        sugestao = a["sugestao"]
                        prompt += f"- {sugestao}\n"
                prompt += "\nINSTRUCAO: Se abertura_fraca, comece o feedback por isso. A abertura e o momento mais critico.\n"

    if guard_rails:
        prompt += guard_rails

    context_section = _build_context_section(context)
    if context_section:
        prompt += context_section

    congruence = metrics.congruence
    if congruence is not None:
        _cong_status = congruence.get("dimension_status", "")
        if _cong_status == "ok":
            _cong_metrics = congruence.get("metrics", {})
            if _cong_metrics and _cong_metrics.get("contradicoes"):
                prompt += "\n\n## Congruencia Entre Canais\n"
                cong_score = congruence.get("score", "?")
                cong_diag = _cong_metrics.get("diagnostico", "")
                prompt += f"Score de congruencia: {cong_score}/100 ({cong_diag})\n"
                prompt += "Contradicoes detectadas:\n"
                for c in _cong_metrics["contradicoes"]:
                    c_descricao = c["descricao"]
                    prompt += f"- {c_descricao}\n"
                prompt += "\nMencione as incongruencias de forma construtiva — o orador pode nao estar ciente que corpo e voz enviam mensagens diferentes.\n"

    temporal = metrics.temporal
    if temporal is not None:
        _temporal_status = temporal.get("dimension_status", "")
        if _temporal_status == "ok":
            _temporal_metrics = temporal.get("metrics", {})
            if _temporal_metrics and _temporal_metrics.get("disponivel"):
                tercos = _temporal_metrics.get("por_terco", {})
                prompt += "\n\n## Arco Temporal da Performance\n"
                padrao = _temporal_metrics.get("padrao", "desconhecido")
                padrao_desc = _temporal_metrics.get("padrao_descricao", "")
                prompt += f"Padrao detectado: {padrao} — {padrao_desc}\n"
                for label in ["abertura", "meio", "fechamento"]:
                    t = tercos.get(label, {})
                    t_score = t.get("score", "?")
                    t_fillers = t.get("fillers", 0)
                    t_monotonos = t.get("trechos_monotonos", 0)
                    prompt += f"- {label.capitalize()}: score {t_score}, fillers {t_fillers}, trechos monotonos {t_monotonos}\n"
                prompt += "\nComente sobre o arco temporal: o orador mantem energia, perde no meio, ou constroi crescendo?\n"

    return prompt


def _calculate_llm_cost(response) -> float:
    """Calcula custo real via usage_metadata se disponivel."""
    try:
        usage = getattr(response, "usage_metadata", None)
        if usage is None:
            return 0.0
        input_tokens = getattr(usage, "prompt_token_count", 0) or 0
        output_tokens = getattr(usage, "candidates_token_count", 0) or 0
        cost = (input_tokens / 1_000_000 * 0.075) + (output_tokens / 1_000_000 * 0.3)
        return round(cost, 6)
    except Exception:
        return 0.0


def generate_report(metrics: AggregatedMetrics, context: dict | None = None) -> dict:
    """Gera relatorio qualitativo de coaching usando Gemini — path Truth Contract.

    Story 8.5 vetos fechados:
    - V8: AggregatedMetrics Pydantic input
    - V9: None → INDISPONIVEL no prompt, nunca 0/100
    - V10: Identity check via dimension_status
    - V11: Gemini JSON mode (response_mime_type=application/json)
    - V12: Retry com temperatures [0.7, 0.5, 0.3]
    - V13: Schema novo sem retrocompat fields
    - V16: llm_cost_usd calculado via usage_metadata
    """
    start = time.time()
    logger.info("report_generation_start_tc", partial=metrics.partial_aggregation)

    genai.configure(api_key=config.GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash")

    prompt = _build_prompt(metrics, context)

    temperatures = [0.7, 0.5, 0.3]
    last_error = None

    for attempt, temp in enumerate(temperatures):
        _prompt = prompt
        if attempt > 0:
            _prompt += "\n\nIMPORTANTE: retorne APENAS JSON valido, sem markdown, sem comentarios."
            logger.info("report_retry", attempt=attempt + 1, temperature=temp)

        try:
            response = model.generate_content(
                _prompt,
                generation_config={
                    "response_mime_type": "application/json",
                    "temperature": temp,
                },
            )
            text = response.text.strip()

            report = json.loads(text)

            llm_cost = _calculate_llm_cost(response)
            elapsed = time.time() - start

            logger.info(
                "report_generation_complete_tc",
                duration_seconds=round(elapsed, 2),
                attempt=attempt + 1,
                temperature=temp,
                llm_cost_usd=llm_cost,
                partial_aggregation=metrics.partial_aggregation,
            )

            return {
                "resumo": report.get("resumo", ""),
                "forcas": report.get("forcas", []),
                "melhorias_80_20": report.get("melhorias_80_20", []),
                "dimensoes": report.get("dimensoes", {}),
                "plano_12_semanas": report.get("plano_12_semanas", []),
                "mensagem_final": report.get("mensagem_final", ""),
                "llm_model": "gemini-2.5-flash",
                "llm_cost_usd": llm_cost,
            }

        except json.JSONDecodeError as e:
            logger.warning(
                "report_json_parse_failed_tc", attempt=attempt + 1, temperature=temp, error=str(e)
            )
            last_error = e
        except Exception as e:
            logger.warning(
                "report_generation_attempt_failed_tc",
                attempt=attempt + 1,
                temperature=temp,
                error=str(e),
            )
            last_error = e
            if attempt < len(temperatures) - 1:
                time.sleep(2**attempt)

    logger.error("report_generation_failed_tc", error=str(last_error))
    raise RuntimeError(
        f"Geracao de relatorio falhou apos {len(temperatures)} tentativas: {last_error}"
    )


def generate_report_legacy(aggregated: dict, context: dict | None = None) -> dict:
    """Gera relatorio qualitativo de coaching — PATH LEGACY (flag OFF).

    Preservado 100% intacto do pre-Story 8.5. Recebe dict, usa .get(x, 0)
    silencioso, inclui retrocompat fields (summary, dimension_feedback).

    NAO modificar este metodo — e o kill switch do Truth Contract.
    """
    start = time.time()
    logger.info("report_generation_start")

    genai.configure(api_key=config.GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash")

    dimension_scores = aggregated.get("dimension_scores", {})
    detailed = aggregated.get("detailed_metrics", {})
    incomplete = aggregated.get("incomplete_dimensions", [])

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
        facial_score=dimension_scores.get("facial", 0),
        facial_metrics=_format_metrics(detailed.get("facial", {})),
        archetype_score=dimension_scores.get("archetypes", 0),
        archetype_metrics=_format_metrics(detailed.get("archetypes", {})),
    )

    problems = _rank_problems(aggregated)
    if problems:
        prompt += "\n\n## HIERARQUIA DE PROBLEMAS (rankeados por impacto — 80/20)\n"
        for i, p in enumerate(problems, 1):
            prompt += (
                f"#{i} {p['level']} — {p['label']} (valor: {p['value']}, ideal: {p['threshold']})\n"
            )
        prompt += "\nINSTRUCAO: concentre 80% do feedback nos problemas #1 e #2. O orador SAI com 1 prioridade: o problema #1.\n"

    insights = _build_cross_insights(aggregated)
    if insights:
        prompt += "\n\n## INSIGHTS PRE-CALCULADOS (cruzamento de metricas — USE como base)\n"
        for insight in insights:
            prompt += f"- {insight}\n"
        prompt += "\nINSTRUCAO: use esses insights como BASE do feedback. NAO copie literal — reescreva no seu tom de coach.\n"

    identity = aggregated.get("identity", {})
    if identity.get("score") is not None and identity.get("diagnostico") != "failed":
        prompt += "\n\n## IDENTIDADE COMUNICATIVA DO ORADOR\n"
        identity_score = identity["score"]
        identity_diag = identity.get("diagnostico", "")
        prompt += f"Score de identidade: {identity_score}/100 ({identity_diag})\n"
        aut_count = identity.get("autoridade_count", 0)
        aut_ratio = identity.get("autoridade_ratio", 0)
        vit_count = identity.get("vitima_count", 0)
        prompt += f"Linguagem de autoridade: {aut_count} marcadores ({aut_ratio:.0%})\n"
        prompt += f"Linguagem de vitima: {vit_count} marcadores\n"
        total_vicios = identity.get("total_vicios", 0)
        if total_vicios > 0:
            vicio_dom = identity.get("vicio_dominante", "nenhum")
            prompt += f"Vicios emocionais detectados: {total_vicios} (dominante: {vicio_dom})\n"
        exemplos = identity.get("exemplos", [])
        if exemplos:
            exemplos_str = ", ".join('"' + e["texto"] + '"' for e in exemplos[:3])
            prompt += "Exemplos: " + exemplos_str + "\n"
        prompt += "\nINSTRUCAO: Se identidade_bloqueada ou identidade_fragil, aborde PRIMEIRO — antes de tecnica.\n"
        prompt += "Cruze com desejo_transmitir do questionario: se orador quer 'autoridade' mas linguagem indica vitima, aponte o gap.\n"

    opening = aggregated.get("opening", {})
    if opening.get("disponivel"):
        prompt += "\n\n## ANALISE DE ABERTURA\n"
        op_score = opening["score"]
        op_diag = opening.get("diagnostico", "")
        prompt += f"Score de abertura: {op_score}/100 ({op_diag})\n"
        tecnicas = opening.get("tecnicas_detectadas", [])
        if tecnicas:
            prompt += "Tecnicas detectadas: " + ", ".join(t["label"] for t in tecnicas) + "\n"
        else:
            prompt += "Tecnicas detectadas: NENHUMA\n"
        op_feedback = opening.get("feedback", "")
        prompt += f"Feedback: {op_feedback}\n"
        ausentes = opening.get("tecnicas_ausentes", [])
        if ausentes:
            prompt += "Sugestoes de tecnicas nao usadas:\n"
            for a in ausentes:
                a_sugestao = a["sugestao"]
                prompt += f"- {a_sugestao}\n"
        prompt += "\nINSTRUCAO: Se abertura_fraca, comece o feedback por isso. A abertura e o momento mais critico.\n"

    if guard_rails:
        prompt += guard_rails

    context_section = _build_context_section(context)
    if context_section:
        prompt += context_section

    congruence = aggregated.get("congruence", {})
    if congruence.get("contradicoes"):
        prompt += "\n\n## Congruencia Entre Canais\n"
        cong_score = congruence.get("score", "?")
        cong_diag = congruence.get("diagnostico", "")
        prompt += f"Score de congruencia: {cong_score}/100 ({cong_diag})\n"
        prompt += "Contradicoes detectadas:\n"
        for c in congruence["contradicoes"]:
            c_desc = c["descricao"]
            prompt += f"- {c_desc}\n"
        prompt += "\nMencione as incongruencias de forma construtiva — o orador pode nao estar ciente que corpo e voz enviam mensagens diferentes.\n"

    temporal = aggregated.get("temporal", {})
    if temporal.get("disponivel"):
        tercos = temporal.get("por_terco", {})
        prompt += "\n\n## Arco Temporal da Performance\n"
        temp_padrao = temporal.get("padrao", "desconhecido")
        temp_padrao_desc = temporal.get("padrao_descricao", "")
        prompt += f"Padrao detectado: {temp_padrao} — {temp_padrao_desc}\n"
        for label in ["abertura", "meio", "fechamento"]:
            t = tercos.get(label, {})
            t_score = t.get("score", "?")
            t_fillers = t.get("fillers", 0)
            t_monotonos = t.get("trechos_monotonos", 0)
            prompt += f"- {label.capitalize()}: score {t_score}, fillers {t_fillers}, trechos monotonos {t_monotonos}\n"
        prompt += "\nComente sobre o arco temporal: o orador mantem energia, perde no meio, ou constroi crescendo?\n"

    last_error = None
    for attempt in range(3):
        try:
            response = model.generate_content(prompt)
            text = response.text.strip()

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
                "summary": report.get("resumo", ""),
                "dimension_feedback": report.get("dimensoes", {}),
                "llm_model": "gemini-2.5-flash",
                "llm_cost_usd": 0.0,
            }

        except json.JSONDecodeError as e:
            logger.warning("report_json_parse_failed", attempt=attempt + 1, error=str(e))
            last_error = e
        except Exception as e:
            logger.warning("report_generation_attempt_failed", attempt=attempt + 1, error=str(e))
            last_error = e
            time.sleep(2**attempt)

    logger.error("report_generation_failed", error=str(last_error))
    raise RuntimeError(f"Geracao de relatorio falhou apos 3 tentativas: {last_error}")
