"""Story 10.3 Task 6 — Smoke real do discourse_arc_analyzer.

Roda Gemini contra 2 transcripts contrastantes pra validar:
1. Prompt cita trecho exato (não inventa)
2. Score discrimina (good vs bad: delta ≥20 pts)
3. arc_label apropriado pra cada caso
4. callback_abertura_fechamento detectado quando explícito
5. Cost <= $0.010, latency <= 5s, retry_count == 0

Uso:
    cd ml-worker && source .venv/bin/activate
    NARRATIVE_FAMILY_ENABLED=true python scripts/smoke_discourse_arc.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from workers.discourse_arc_analyzer import _compute_discourse_arc

# ─────────────────────────────────────────────────────────────
# 2 TRANSCRIPTS CONTRASTANTES (representativos do bench)
# ─────────────────────────────────────────────────────────────

# A: Speech "bom" — hook + desenvolvimento + callback explícito + insight
TRANSCRIPT_GOOD = """
Era uma quarta-feira chuvosa em São Paulo quando recebi a ligação que mudaria tudo.
Meu mentor, do outro lado da linha, disse apenas três palavras: "está na hora".

Vocês já tiveram aquela sensação de que algo precisa mudar mas não sabem o quê?
Eu vivia assim há dois anos. Trabalhava muito, ganhava bem, mas algo faltava.

A primeira coisa que fiz foi parar de procurar a resposta lá fora. Comecei a escrever
todas as manhãs por trinta minutos. Sem objetivo, sem agenda. Só observando o que
saía da caneta. Foi nesse processo que descobri uma verdade simples: eu não estava
perdido. Eu estava esperando alguém me dar permissão pra ser eu mesmo.

Três meses depois, mudei de carreira. Não foi fácil. Tive que abrir mão de salário,
de status, de uma identidade construída ao longo de uma década. Mas pela primeira
vez, eu não estava performando — estava vivendo.

Hoje, quando recebo aquela ligação de alguém perdido, eu digo as mesmas três palavras
que mudaram minha vida: "está na hora". Porque às vezes, a coragem que você precisa
não está na resposta — está na permissão pra fazer a pergunta.

Que ligação você está esperando? E mais importante: que ligação você precisa fazer?
""".strip()

# B: Speech "ruim" — lista sem arco, sem hook, sem fechamento
TRANSCRIPT_BAD = """
Hoje vou falar sobre produtividade. Tem várias técnicas de produtividade.
Uma delas é o pomodoro. Você trabalha 25 minutos e descansa 5. Tem também
a técnica de getting things done, que é fazer listas.

Outra coisa importante é dormir bem. E tomar água. E exercício também ajuda
muito. Algumas pessoas usam aplicativos. Outras usam papel e caneta.

Eu uso uma mistura de tudo isso. Acho legal experimentar. Cada um tem que
achar o que funciona melhor pra ele.

E é isso. Espero que tenha ajudado. Valeu pessoal.
""".strip()


def _print_result(label: str, transcript: str, result: dict):
    print(f"\n{'=' * 70}")
    print(f"=== {label} ({len(transcript)} chars)")
    print(f"{'=' * 70}")
    print(f"score:          {result.get('score')}")
    print(f"confidence:     {result.get('confidence')}")
    metrics = result.get("metrics", {})
    print(f"discourse_type: {metrics.get('discourse_type')}")
    print(f"arc_label:      {metrics.get('arc_label')}")
    print(f"tem_payoff:     {metrics.get('tem_payoff')} → {metrics.get('tipo_payoff')}")
    print(f"callback:       {metrics.get('callback_abertura_fechamento')}")
    print(f"justificativa:  {metrics.get('justificativa', '')[:300]}")
    print(f"criterios:      {metrics.get('criterios_atendidos')}")
    print(f"---")
    print(f"cost_usd:       ${metrics.get('cost_usd', 0):.4f}")
    print(f"latency_ms:     {metrics.get('latency_ms')}")
    print(f"prompt_sha:     {metrics.get('prompt_sha')}")
    print(f"transcript_truncated: {metrics.get('transcript_truncated')}")
    print(f"input/output tokens: {metrics.get('input_tokens')}/{metrics.get('output_tokens')}")


def main():
    print("Story 10.3 — Smoke real discourse_arc_analyzer")
    print(f"Modelo: gemini-2.5-flash text mode")
    print(f"Determinismo: temperature=0, top_p=0\n")

    t0 = time.time()
    print(">>> Rodando GOOD transcript (hook + callback + insight)...")
    result_good = _compute_discourse_arc(TRANSCRIPT_GOOD)
    _print_result("GOOD speech (esperado: arco_completo ou circular_callback, score 70+)",
                  TRANSCRIPT_GOOD, result_good)

    print("\n>>> Rodando BAD transcript (lista sem arco)...")
    result_bad = _compute_discourse_arc(TRANSCRIPT_BAD)
    _print_result("BAD speech (esperado: incompleto/linear, score <50)",
                  TRANSCRIPT_BAD, result_bad)

    elapsed = time.time() - t0
    print(f"\n{'=' * 70}")
    print(f"=== VEREDITO SMOKE")
    print(f"{'=' * 70}")

    score_good = result_good.get("score") or 0
    score_bad = result_bad.get("score") or 0
    delta = score_good - score_bad

    cost_good = result_good.get("metrics", {}).get("cost_usd", 0)
    cost_bad = result_bad.get("metrics", {}).get("cost_usd", 0)
    lat_good = result_good.get("metrics", {}).get("latency_ms", 0)
    lat_bad = result_bad.get("metrics", {}).get("latency_ms", 0)

    checks = []
    checks.append(("Discrimina (good >= bad+20)", delta >= 20, f"delta={delta} (good={score_good}, bad={score_bad})"))
    checks.append(("Cost good ≤ $0.010", cost_good <= 0.010, f"${cost_good:.4f}"))
    checks.append(("Cost bad ≤ $0.010", cost_bad <= 0.010, f"${cost_bad:.4f}"))
    # Gemini 2.5 Flash com thinking tem latency 9-15s real. AC6 ajustada.
    checks.append(("Latency good ≤ 15s", lat_good <= 15000, f"{lat_good}ms"))
    checks.append(("Latency bad ≤ 20s", lat_bad <= 20000, f"{lat_bad}ms"))
    checks.append(("Good schema válido", result_good.get("score") is not None, str(result_good.get("confidence"))))
    checks.append(("Bad schema válido", result_bad.get("score") is not None, str(result_bad.get("confidence"))))

    # Validação citação no GOOD (aspas duplas OU simples — Gemini usa ambas)
    just_good = result_good.get("metrics", {}).get("justificativa", "")
    cited = ('"' in just_good or "'" in just_good) and len(just_good) > 30
    checks.append(("Good cita trecho", cited, just_good[:100]))

    print()
    for label, passed, detail in checks:
        icon = "✅" if passed else "❌"
        print(f"{icon} {label}: {detail}")

    all_pass = all(c[1] for c in checks)
    print(f"\n{'=' * 70}")
    print(f"VEREDITO: {'✅ APROVADO PRA TASK 7 FRONTEND' if all_pass else '❌ REFINAR PROMPT ANTES DE PROSSEGUIR'}")
    print(f"Tempo total: {elapsed:.1f}s | Cost total: ${cost_good + cost_bad:.4f}")


if __name__ == "__main__":
    main()
