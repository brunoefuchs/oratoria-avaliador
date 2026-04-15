"""Unified evaluation prompt used by all 3 LLMs + versioning via SHA256.

Critical: reuse EXACTLY the same criteria as ml-worker/workers/report_generator.py.
If prompt diverges from production, convergence scores reflect prompt differences,
not model differences. Keep in sync.
"""

import hashlib


REPORT_EVAL_PROMPT_V1 = """Você é um avaliador técnico de oratória. Analise o vídeo fornecido e retorne APENAS um JSON (sem texto adicional) com esta estrutura:

{
  "score_geral": 0-100,
  "scores_por_dimensao": {
    "voz": 0-100,
    "clareza": 0-100,
    "presenca": 0-100,
    "gestos": 0-100,
    "arquetipos": 0-100,
    "congruencia": 0-100
  },
  "pontos_fortes": ["ponto 1", "ponto 2", "ponto 3"],
  "pontos_fracos": ["ponto 1", "ponto 2", "ponto 3"]
}

Critérios de avaliação:
- Voz: projeção, articulação, dicção, ritmo, respiração
- Clareza: estrutura da mensagem, ausência de muletas, variação de ritmo
- Presença: postura corporal, abertura, ocupação do espaço
- Gestos: amplitude, intenção, naturalidade, sincronia com fala
- Arquétipos: consistência da persona comunicacional (guerreiro/sábio/bobo/herói/etc.)
- Congruência: coerência entre palavra, corpo e voz

Escala 0-100:
  0-20 crítico, 21-40 fraco, 41-60 mediano, 61-80 bom, 81-100 excelente

Pontos fortes/fracos: top 3 observações CONCISAS (máx 1 frase cada).
"""


def prompt_version(prompt: str = REPORT_EVAL_PROMPT_V1) -> str:
    """SHA256 truncado (8 chars) do conteúdo do prompt — rastreabilidade."""
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:8]


PROMPT_VERSION = prompt_version()
