# Convergence Harness — Story 7.6

**Status:** MVP via OpenRouter (Python). Dashboard `/dev/convergence` deferido (spec original TS).

## Objetivo

Medir convergência entre **3 LLMs** (Gemini 2.5 Flash / Claude Opus 4.6 / GPT-5) avaliando o mesmo vídeo de oratória. Saída: correlação Pearson (r) por dimensão + concordância top-3 em pontos fortes/fracos. Alvo: `r ≥ 0.85` geral, `r ≥ 0.75` por dimensão, `2/3` coincidência em top-3.

Sem isso, a métrica principal do Epic 7 ("convergência ≥85%") é aspiracional.

## Decisões de implementação (divergem do spec original)

| Spec original | MVP atual | Razão |
|---------------|-----------|-------|
| TypeScript `tools/convergence/` | Python `scripts/convergence/` | Stack consistente com ml-worker; aproveita `httpx` |
| 3 SDKs separados (gemini/anthropic/openai) | 1 SDK (OpenRouter via httpx) | Destrava rápido, cap de budget unificado |
| Embeddings via `@xenova/transformers` | Jaccard token overlap | Evita dependência pesada; iterável |
| Dashboard Next.js `/dev/convergence` | **DEFERIDO** | Separar em story própria; MVP entrega só CLI + persistence |
| `p-limit`/`bottleneck` para RPM por provider | Sequencial | OpenRouter throttles internamente; paralelismo não compensa complexidade |

## Setup

### 1. Env vars (em `.env` ou export)

```bash
OPENROUTER_API_KEY=sk-or-v1-...       # obrigatório
SUPABASE_URL=https://...              # necessário só pra --persist
SUPABASE_SERVICE_ROLE_KEY=...         # necessário só pra --persist

# Opcionais — override dos model names caso mudem
CONVERGENCE_GEMINI_MODEL=google/gemini-2.5-flash
CONVERGENCE_CLAUDE_MODEL=anthropic/claude-opus-4.1
CONVERGENCE_GPT_MODEL=openai/gpt-5
```

### 2. Deps

Nada novo. Usa `httpx` (já no ml-worker). Opcionalmente `supabase-py` para persistir.

```bash
# Se quiser persistir no Supabase:
pip install supabase
```

### 3. Migrations

Aplicar no Supabase (`010_convergence_runs.sql` + `011_convergence_alerts.sql`):

```bash
supabase db push
```

## CLI

### Dry-run (sem chamar LLM — útil pra testar correlator)

```bash
python -m scripts.convergence.harness --dry-run
```

### Single video via URL pública

```bash
python -m scripts.convergence.harness \
  --video-id 7a3e9ccd-... \
  --video-url https://storage.supabase.co/.../file.mp4 \
  --output-json ./run-result.json
```

### Single video via arquivo local (base64-encoded no request)

```bash
python -m scripts.convergence.harness \
  --video-path ./sample.mp4 \
  --output-json ./run-result.json
```

⚠️ Arquivos locais grandes (>25MB) podem estourar request size em alguns modelos. Prefira `--video-url`.

### Persistir no Supabase

```bash
python -m scripts.convergence.harness \
  --video-id 7a3e9ccd-... \
  --video-url https://... \
  --persist
```

### Batch (10 vídeos)

Arquivo `batch.txt`:

```
7a3e9ccd-...|https://.../v1.mp4
8b4f0dde-...|https://.../v2.mp4
...
```

Rodar:

```bash
python -m scripts.convergence.harness --batch ./batch.txt --persist --output-json ./batch-results.json
```

## Output (exemplo)

```
=== Convergence Report ===
Prompt version: a3f7c9de

Scores gerais por LLM:
  gemini   (google/gemini-2.5-flash): 72
  claude   (anthropic/claude-opus-4.1): 74
  gpt      (openai/gpt-5): 70

Pairwise proximity (overall, 0-1):
  gemini-claude    r=0.980 ✓
  gemini-gpt       r=0.980 ✓
  claude-gpt       r=0.960 ✓
  mean_r_overall   0.973

Pairwise proximity (per dimension, 0-1):
  voz          mean=0.980 ✓
  clareza      mean=0.975 ✓
  ...

Top-3 concordância (≥2 de 3 é o alvo):
  fortes: {'gemini-claude': 3, 'gemini-gpt': 2, 'claude-gpt': 2}
  fracos: {'gemini-claude': 2, 'gemini-gpt': 3, 'claude-gpt': 2}

✓ Todos os targets atingidos.
```

## Orçamento

- **Objetivo do Epic 7:** US$ 5 em 10 vídeos
- **Estimativa por vídeo (3 LLMs):** ~US$ 0.40–0.60
- **Cap operacional:** monitorar consumo via dashboard OpenRouter. Abortar se 80% do budget consumido antes de 8 vídeos

## Como interpretar

### Alerta overall (`r < 0.85`)
Os 3 modelos divergem em score geral. Prompt pode estar ambíguo ou critérios de cada modelo muito diferentes. Revisar `prompts.py`.

### Alerta por dimensão (`r < 0.75`)
Uma dimensão específica diverge mais que outras. Ex: se "arquétipos" vem com r=0.50, provavelmente o prompt não define bem quais 12 arquétipos esperamos.

### Top-3 < 2 coincidências
Modelos apontam pontos fortes/fracos diferentes. Pode ser:
- Falha do Jaccard (threshold 0.3 pode ser baixo demais para sinônimos)
- Genuína divergência
- Top-3 truncado (LLM retornou mais, só pegamos 3)

**Mitigação:** iterar threshold ou plugar `sentence-transformers` (~300MB extra).

## Como adicionar novo LLM

1. Em `llm_client.py`, adicionar entrada no `MODELS` dict:
   ```python
   "llama": os.environ.get("CONVERGENCE_LLAMA_MODEL", "meta-llama/llama-3.1-405b-instruct"),
   ```
2. Em `correlator.py`, `DIMENSIONS` não muda — correlator já é N-LLM agnostic via `_pairs()`.
3. Em `supabase/migrations/010_convergence_runs.sql`, atualizar `CHECK (llm IN (...))`.
4. Rodar migration nova (ex: `012_add_llama_to_convergence.sql`).

## Troubleshooting

### `OPENROUTER_API_KEY not set`
Adicionar no `.env` ou exportar: `export OPENROUTER_API_KEY=sk-or-v1-...`.

### `429 Rate limited`
OpenRouter aplica rate-limit por conta. Esperar 60s e reexecutar. Batch grande: processar em blocos de 3-5 vídeos.

### `No JSON found in LLM response`
LLM não retornou JSON válido. Checar com `--verbose` o raw response. Se prompt estiver OK, provavelmente falha temporária do modelo — reexecutar.

### `Malformed response from {llm}`
OpenRouter retornou estrutura inesperada. Checar body com `--verbose`. Pode ser model string incorreto (verificar em https://openrouter.ai/models).

### Video em base64 explode tamanho do request
Usar `--video-url` (URL pública) em vez de `--video-path`. Upload pro storage do Supabase primeiro.

## Testes

```bash
# Correlator unit tests (planejado — ainda não implementado)
pytest scripts/convergence/tests/

# Smoke dry-run
python -m scripts.convergence.harness --dry-run
```

## Limitações conhecidas

1. **3 LLMs podem concordar estando todos errados.** Convergência alta + precisão baixa. Mitigado pela Story 7.7 (ground truth humano com Guilherme Reginatto).
2. **Jaccard é proxy pobre pra semântica.** "Voz monótona" não casa com "pouca variação de pitch". Iterável.
3. **Pearson em 1 vídeo só é proxy.** Para r real, precisa 2+ amostras por LLM. Com 10 vídeos do batch, correlator vira significativo (pode ser computado em versão futura).
4. **Base64 upload** em `--video-path` é caro em request size. Prefira storage público (`--video-url`).
5. **Dashboard frontend não existe.** Consumir resultados via `--output-json` + CLI ou query direto no Supabase.

## Referências

- **Story:** `docs/stories/7.6.convergence-harness.story.md`
- **Epic:** `docs/stories/7.0.epic-report-precision.md`
- **Prompt master:** `scripts/convergence/prompts.py`
- **Handoff origem:** `.aiox/handoffs/handoff-po-to-dev-2026-04-14-story-7-6-ready.yaml`
- **Pareto zone:** 0,8% Genialidade — bloqueante da métrica principal Epic 7

— Dex, sempre construindo 🔨
