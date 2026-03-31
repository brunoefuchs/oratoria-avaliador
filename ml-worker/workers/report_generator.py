import json
import time

import google.generativeai as genai
import structlog

import config

logger = structlog.get_logger()

REPORT_PROMPT = """Voce e um especialista em oratoria e comunicacao. Analise as metricas abaixo de uma apresentacao em video e gere um relatorio de feedback.

## Metricas da Avaliacao

Score Geral: {overall_score}/100

### Postura (Score: {posture_score}/100)
{posture_metrics}

### Gestual (Score: {gesture_score}/100)
{gesture_metrics}

### Tom de Voz (Score: {voice_score}/100)
{voice_metrics}

### Vicios de Linguagem (Score: {fillers_score}/100)
{fillers_metrics}

## Instrucoes de Formato

Responda EXCLUSIVAMENTE em JSON valido com esta estrutura:
{{
  "summary": "Resumo geral de 2-3 frases sobre a performance",
  "dimension_feedback": {{
    "posture": {{
      "score_label": "Muito bom|Bom|Regular|Precisa atencao|Critico",
      "strengths": ["ponto forte 1", "ponto forte 2"],
      "improvements": ["melhoria 1", "melhoria 2"],
      "tip": "Uma dica pratica e especifica para melhorar"
    }},
    "gesture": {{
      "score_label": "...",
      "strengths": ["..."],
      "improvements": ["..."],
      "tip": "..."
    }},
    "voice": {{
      "score_label": "...",
      "strengths": ["..."],
      "improvements": ["..."],
      "tip": "..."
    }},
    "fillers": {{
      "score_label": "...",
      "strengths": ["..."],
      "improvements": ["..."],
      "tip": "..."
    }}
  }}
}}

Seja especifico e acionavel. Use os dados numericos para embasar o feedback. Responda em portugues do Brasil."""


def _format_metrics(metrics: dict) -> str:
    """Format metrics dict into readable text for prompt."""
    lines = []
    for key, value in metrics.items():
        if isinstance(value, (dict, list)):
            lines.append(f"- {key}: {json.dumps(value, ensure_ascii=False)}")
        else:
            lines.append(f"- {key}: {value}")
    return "\n".join(lines) if lines else "- Dados indisponiveis"


def generate_report(aggregated: dict) -> dict:
    """Generate qualitative report using Gemini 2.0 Flash."""
    start = time.time()
    logger.info("report_generation_start")

    genai.configure(api_key=config.GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.0-flash")

    dimension_scores = aggregated.get("dimension_scores", {})
    detailed = aggregated.get("detailed_metrics", {})

    prompt = REPORT_PROMPT.format(
        overall_score=aggregated.get("overall_score", 0),
        posture_score=dimension_scores.get("posture", 0),
        posture_metrics=_format_metrics(detailed.get("posture", {})),
        gesture_score=dimension_scores.get("gesture", 0),
        gesture_metrics=_format_metrics(detailed.get("gesture", {})),
        voice_score=dimension_scores.get("voice", 0),
        voice_metrics=_format_metrics(detailed.get("voice", {})),
        fillers_score=dimension_scores.get("fillers", 0),
        fillers_metrics=_format_metrics(detailed.get("fillers", {})),
    )

    # Retry with backoff
    last_error = None
    for attempt in range(3):
        try:
            response = model.generate_content(prompt)
            text = response.text.strip()

            # Clean markdown code blocks if present
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
                "summary": report.get("summary", ""),
                "dimension_feedback": report.get("dimension_feedback", {}),
                "llm_model": "gemini-2.0-flash",
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
    raise RuntimeError(f"Report generation failed after 3 attempts: {last_error}")
