# Runner Integration Guide

Este guia detalha os padrões arquiteturais de LLM Runners na SINKRA Hub e como integrá-los de forma viável ao Ecossistema. 

**Referência Canônica (Golden Master):** Inspire-se na implementação moderna do `mmos.sh`, que usa inteiramente as funções do framework, evitando reedições parciais por script.

## The Lookup Table: "Se você precisa de X, use módulo Y"

| O que você está implementando? | Módulo na lib | Função a invocar | Anti-Pattern sendo evitado |
|---|---|---|---|
| Chamar LLM | `runtime.sh` | `run_llm_prompt "$system" "$user_txt"` | **"Hardcoded Pipe"** (`claude -p`). Ignora context error dedup, auto fallbacks e sessões. |
| Alterar variáveis de controle de etapa JSON | `state-manager.sh` | `state_phase_update "$STATE_FILE" "phase_1" "ok"` | **"JQ Direto Cabeludo"**. Pipes múltiplos causando perdas ou syntax errors. |
| Calcular Custos e Gasto de Tokens | `metrics.sh` | `record_metrics()` (ou Auto-invocado via `runtime.sh`) | **"Contabilidade Paralela"**. Planilhas próprias. Consumo sem limite invisível. |
| Delimitar Inbound vs Payload Limpo | `headless-guard.sh` | `truncate_prior_context` e `filter_llm_output` | **"OOM / Payload Garbage"**. Out of Memory ou falhas de parsers (JSON puro com aspas acidentais). |

## Migration Examples

### Do `claude -p` Hardcoded → `run_llm_prompt()`

**❌ A Evitar (Modelo Defasado / Parcial)**
```bash
response=$(claude -p "$(cat prompt.md)")
echo "Tokens consumidos: ???"
# Fica a critério do programador debugar se retornar erro.
```

**✅ Módulo Correto (Runner-lib Integration)**
```bash
source "$RUNNER_LIB_DIR/loader.sh"
# O runtime cuida da session, da API e metricas:
run_llm_prompt "$system_prompt" "$user_prompt" "max_turns=5"
```

### Do `JQ` Direto para → `state-manager.sh`

**❌ A Evitar:**
```bash
jq '.phases.discovery = "in_progress"' state-decoder.json > state-decoder.tmp
mv state-decoder.tmp state-decoder.json
```

**✅ Padrão Correto:**
```bash
state_phase_update "$STATE_FILE" "discovery" "in_progress"
```
