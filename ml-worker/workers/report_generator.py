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
        if key in ("fillers", "mapa_temporal", "estrategicas", "hesitacao", "respiracao"):
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


def generate_report(aggregated: dict) -> dict:
    """Gera relatorio qualitativo de coaching usando Gemini."""
    start = time.time()
    logger.info("report_generation_start")

    genai.configure(api_key=config.GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash")

    dimension_scores = aggregated.get("dimension_scores", {})
    detailed = aggregated.get("detailed_metrics", {})

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
