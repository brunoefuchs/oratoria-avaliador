# Epic 9 — Verificação Plano ↔ Realidade + Fórmula Ativa

**Data:** 2026-04-17
**Analista:** @vinh-giang
**Contexto:** Pós-merge de 9 PRs Epic 9 (commits `1faf2fc` → `3d8f29d`)

---

## 1. Score plano ↔ realidade

### Decisões arquiteturais (3/3 cumpridas)

| # | Plano original (2026-04-16) | Estado em main | Status |
|---|---|---|---|
| 1 | overall_score só com 🟢 Alta + variety como meta-dim | `SCORING_DIMENSIONS = (posture, gesture, voice, fillers, variety, facial)` — 6 dims | ✅ |
| 2 | Secondary dims exibidas com badge "em calibração" | `SECONDARY_DIMENSIONS` tem 8 dims + `DIMENSION_CONFIDENCE` 🟢🟡🔴 + UI `ConfidenceBadge` | ✅ + 1 bonus (gesture_semantic) |
| 3 | tonality 🟡→🟢 via ML **após validação mentor** | Wav2Vec2 integrado como SECONDARY, promoção condicional a Gate 3 | ✅ conservador correto |

### 6 upgrades técnicos

| # | Plano | Realidade | Status |
|---|---|---|---|
| 1 | Whisper `large-v3-turbo` + VRAM orchestrator | `superb/whisper turbo` + fallback medium + `ModelGPU` context manager | ✅ Gate 1 PASS peak 4.93GB real |
| 2 | Wav2Vec2-emotion (base vs large) | `superb/wav2vec2-base-superb-er` integrado, carrega em CPU | ✅ lib instalada (transformers 5.5.4) |
| 3 | py-feat FACS (20 AUs + 6 emoções) | Código pronto, lib bloqueada Python 3.12 (bug upstream `pkgutil.ImpImporter`) | 🟡 parcial — `PYFEAT_ENABLED=false` |
| 4 | openSMILE eGeMAPS (88 features) | Integrado via lazy import | ✅ opensmile 2.6.0 instalado |
| 5 | pyannote VAD (pausa retórica >1.2s) | Integrado + fallback librosa sem HF token | ✅ pyannote.audio 4.0.4 |
| 6 | Gemini Vision (~$0.015/vídeo) | `gesture_semantic_analyzer` com budget guard $0.10/eval | ✅ flag OFF default |

**Score: 5.5/6 upgrades técnicos + 3/3 decisões = 95% do plano entregue.**

### Pesos contextuais (Cenário B)

| Dim | Plano | Main atual | Status |
|---|---|---|---|
| voice | 0.22 | 0.22 | ✅ |
| variety | 0.20 | 0.20 | ✅ |
| gesture | 0.18 | 0.18 | ✅ |
| facial | 0.16 | 0.16 | ✅ |
| posture | 0.14 | 0.14 | ✅ |
| fillers | 0.10 | 0.10 | ✅ |

**100% fiel ao plano.** Soma: 1.00.

---

## 2. Fórmula ATIVA em main

### Com `STATE_OF_ART_ENABLED=true` (Epic 9 ON)

```python
# 6 SCORING_DIMENSIONS processadas
overall_score = round(
    Σ(score_dim × peso_dim) / Σ(peso_dim)
    para dim ∈ SCORING_DIMENSIONS
    onde isinstance(result_dim, WorkerSuccess)
)
```

**Pesos default (HEURISTIC_V1 rotulado no código):**

| Dim | Peso |
|---|---|
| voice | 0.22 |
| variety | 0.20 |
| gesture | 0.18 |
| facial | 0.16 |
| posture | 0.14 |
| fillers | 0.10 |
| **Σ** | **1.00** |

### Pesos contextuais (quando `contexto` resolvido via `motivacao`)

Cada contexto ajusta pesos preservando soma = 1.00. Mapping `motivacao → contexto`:

```python
MOTIVACAO_TO_CONTEXTO = {
    "redes_sociais": "rede_social",
    "vender_mais": "vendas",
    "carreira": "reuniao",
    "palestrar": "palco",
    "satisfacao_pessoal": None,  # usa default
    "outro": None,
}
```

Tabela completa (workers/aggregator.py:47-97):

| Contexto | voice | variety | gesture | facial | posture | fillers |
|---|---|---|---|---|---|---|
| default | 0.22 | 0.20 | 0.18 | 0.16 | 0.14 | 0.10 |
| palco | 0.18 | 0.22 | 0.20 | 0.14 | **0.18** | 0.08 |
| podcast | **0.28** | **0.25** | 0.08 | 0.15 | 0.06 | **0.18** |
| vendas | 0.22 | 0.20 | 0.18 | 0.16 | 0.12 | 0.12 |
| rede_social | 0.20 | 0.18 | 0.18 | **0.20** | 0.10 | 0.14 |
| reuniao | 0.22 | 0.18 | 0.14 | 0.16 | **0.18** | 0.12 |
| aula | 0.22 | **0.22** | 0.18 | 0.14 | 0.14 | 0.10 |

### Tratamento de falha parcial

Se uma ou mais dims retornam `WorkerFailure`:
- Numerador e denominador só somam dims com `WorkerSuccess`
- Payload marca `partial_aggregation=True`
- `incomplete_dimensions: list[str]` lista quais falharam
- `overall_score` permanece válido (não cai pra 0)
- Se TODAS falharam → `overall_score=None` (honestidade sobre indisponibilidade)

### Path legacy (`STATE_OF_ART_ENABLED=false`)

Preserva comportamento v0.6.0 bit-idêntico:
- `SCORING_DIMENSIONS_V060` = 10 dims (mas só 5 pesam: variety, voice, gesture, posture, fillers)
- `PESOS_DEFAULT_V060` intocado desde v0.6.0
- `aggregate_metrics_legacy` (Epic 8) preservado com `force_v060=True`

Rollback instantâneo via env var.

---

## 3. Dimensões SECONDARY (não pesam em overall_score)

8 dims calculadas + salvas em `detailed_metrics`, exibidas com badge de confiança:

| Dim | Confidence | Origem |
|---|---|---|
| archetypes | 🟡 média | Praat acoustic analysis |
| tonality | 🟡 média | Wav2Vec2 + eGeMAPS (ML real) |
| temporal | 🟡 média | Features derivadas por terço |
| opening | 🔴 baixa | Regex PT-BR 7 técnicas |
| identity | 🔴 baixa | Regex PT-BR vícios emocionais |
| storytelling | 🔴 baixa | Regex Bridge + 4 Chemicals |
| congruence | 🔴 baixa | Regras if-then entre canais |
| gesture_semantic | 🟡 média | Gemini Vision LLM structured |

**Promoção path:** qualquer 🟡 pode virar 🟢 + entrar em SCORING após Gate 3 (ground truth Gui) validar correlação ≥ 0.75.

---

## 4. Validação em dados reais (Gate 2)

Story 9.1.1 replay em 5 evals reais do Supabase (2026-04-17):

| # | eval_id | v0.6.0 | v0.7.0 | Δ | facial |
|---|---|---|---|---|---|
| 1 | 775b5f6b | 59 | 54 | **-5** | 40 |
| 2 | 8f53044c | 59 | 54 | **-5** | 40 |
| 3 | 113cb6a4 | 60 | 57 | **-3** | 40 |
| 4 | 494693f0 | 60 | 57 | **-3** | 40 |
| 5 | 18699d04 | 58 | 62 | **+4** | 75 |

- Max delta 5pt ≤ 15pt threshold ✅
- 100% deltas rastreáveis à nova fórmula ✅
- Direção correlaciona com `facial_score` ✅

**Verdict Gate 2: PASS.**

---

## 5. Gaps reconhecidos (honestidade)

1. **py-feat bloqueado** — Python 3.12 + bug upstream. `PYFEAT_ENABLED=false` default até fix.
2. **Wav2Vec2 em CPU** — factory não chama `.to("cuda")`. Funciona mas lento (~75s load). Follow-up não-bloqueante.
3. **Pesos heurísticos** — rotulados `HEURISTIC_V1` no código. Calibração real em Story 9.7 pós-Gate 3.
4. **Bugs MediaPipe pendentes** — MP-4b, MP-5b, MP-6, MP-7 ainda abertos (documento: `handoff-sessao-2026-04-15-completa.md`). Epic 9 NÃO endereçou esses bugs — são independentes.

---

## Conclusão

Plano proposto em `2026-04-16` por @vinh-giang foi **95% entregue** em 1 dia de sessão (2026-04-17). Fórmula ativa em main reflete Cenário B aprovado pelo @po. Gate 2 validou comportamento em dados reais.

**Próximo gate é humano:** Gui Reginatto (Story 7.7) validando outputs em PT-BR pra decidir promoções 🟡→🟢.
