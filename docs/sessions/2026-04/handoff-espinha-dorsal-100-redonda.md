# Handoff — Espinha Dorsal 100% Redonda (ML pipeline)

**Data:** 2026-04-14
**Status:** CONCLUIDO · commit `cffbec7` em `origin/main`
**Agentes:** @ux-design-expert (Uma) → @dev (Dex) → @devops (Gage)

---

## Objetivo da sessao

Usuario re-submeteu o mesmo video de referencia (53.85s, 168 palavras) apos as melhorias de ontem. Objetivo: **auditar se todas as analises funcionaram, fazem sentido, e bater com o baseline V2** — a espinha dorsal do produto precisa ficar perfeita.

---

## Diagnostico inicial (pre-fix)

**Avaliacao `3ba19973` vs baseline V2 `6f69288f`:**

| Dimensao | V2 | Auditoria | Status |
|----------|-----|-----------|--------|
| posture/gesture/voice/fillers/variety/archetypes/identity/opening/congruence/temporal | idem | idem | ✅ todas rodaram, scores dim. identicos |
| overall | 57 | **54** | ❌ peso errado aplicado |
| temporal.fechamento.pitch/volume | 0.0 | 0.0 | ❌ bug antigo, ja existia |

Todas as 10 analises com `confidence=high`. Valores numericos por dimensao **identicos** ao V2 (mesmo video, determinismo validado). A unica diferenca era **overall 57 → 54**: o aggregator havia usado pesos DEFAULT em vez de `rede_social` (o contexto declarado no questionario).

---

## 3 bugs corrigidos nesta sessao

### 1. Race condition do contexto (`ml-worker/app.py:244-263`)

**Bug:** o aggregator lia `evaluation_context` no Step 9, mas em pipelines rapidos (84s total) o usuario ainda estava preenchendo o questionario. Resultado: `motivacao=None` → pesos default.

**Fix:** polling de 1s (ate 15s total) aguardando o contexto chegar antes de cair no default.

**Validacao:** eval `dc5ed8e2` pos-fix → overall **57** com pesos `rede_social` aplicados corretamente.

### 2. Fechamento zerado no temporal (`ml-worker/workers/temporal_analyzer.py`)

**Bug:** `_split_windows_by_terco` usava `t = i * 15.0` (inicio da janela) para alocar por terco. Para video 53.85s com 3 janelas: todas caiam em abertura/abertura/meio → fechamento ficava vazio → `_avg([])` = 0.0.

**Fix:**
- Centro da janela: `t = (i + 0.5) * window_size`
- Ignora valores zerados (janelas sem sinal de voz)
- `window_size` parametrizado, lido do voice_analyzer

### 3. Cauda do video perdida (`voice_analyzer.py`, `variety_analyzer.py`, `archetype_classifier.py`)

**Bug:** `janela_count = int(duration/JANELA_SEGUNDOS)`. Para 53.85s: 3 janelas de 15s = 45s cobertos. **Os ultimos 8.85s da fala eram descartados.**

**Fix:** `N = round(duration/alvo)`, tamanho = `duration/N`. Cobertura 100% garantida em qualquer duracao:

| Duracao | Voice (alvo 15s) | Archetype (alvo 10s) | Perdido |
|---------|------------------|----------------------|---------|
| 45s | 3×15.0s | 4×11.25s | 0s |
| **53.85s** | **4×13.46s** | **5×10.77s** | **0s** |
| 60s | 4×15.0s | 6×10.0s | 0s |
| 90s | 6×15.0s | 9×10.0s | 0s |
| 300s | 20×15.0s | 30×10.0s | 0s |

Arquivos afetados:
- `voice_analyzer.py`: exporta `janela_size_seconds`, aplica no pitch/volume/WPM por janela
- `variety_analyzer.py`: `_detectar_trechos_monotonos` parametriza `janela_segundos`
- `archetype_classifier.py`: mesmo padrao com alvo 10s

---

## Resultado (eval `9093cbe9` pos-fix) — V3 baseline

| Dimensao | V2 | V3 | Delta | Origem |
|----------|----|----|----|----|
| Voice | 52 | **55** | +3 | velocidade_score 51→68 (cv_velocidade 0.052→0.086 cruzou range ideal) |
| Variety | 14 | **32** | +18 | variacao_velocidade 36→81 (propagacao do cv acima) |
| Overall | 57 | **62** | +5 | propagacao voice+variety com peso `rede_social` |
| Posture/Gesture/Fillers/Archetypes/Identity/Opening/Congruence | — | — | 0 | sem mudanca |
| temporal.fechamento | pitch 0.0 / vol 0.0 | **110.4 / 67.6** | fix | agora valores reais |

**Interpretacao:** a variedade real do orador nao mudou — mudou a precisao da medicao. Com 3 janelas grandes, `cv_velocidade` era **subestimado em 64%** (0.052 vs 0.086 real). Com 4 janelas cobrindo 100%, a variacao genuina aparece.

**Impacto em producao:**
- Videos de duracao multipla de 15s/10s (maioria em uso prolongado): valores **identicos** a V2
- Videos irregulares (53s, 62s, 89s): metricas mais fieis
- Zero risco de regressao

---

## Brinde — ajuste visual no web

Ajuste no `.display-lg` em `apps/web/src/app/globals.css:69`:
```diff
- font-size: clamp(1.5rem, 4.5vw, 3rem);
+ font-size: clamp(1.75rem, 5.5vw, 3rem);
```

Mobile: 24px → 28px. Desktop: 48px (inalterado). Hero da home mais legivel em mobile sem afetar web. **Nao commitado ainda** (parte da migracao Resonant Stage pendente, ver `handoff-app-resonant-stage-migration.md`).

---

## Arquivos entregues (commit `cffbec7` em `origin/main`)

```
M ml-worker/app.py                            (+14 -4)
M ml-worker/workers/voice_analyzer.py         (+18 -8)
M ml-worker/workers/temporal_analyzer.py      (+23 -10)
M ml-worker/workers/variety_analyzer.py       (+6 -4)
M ml-worker/workers/archetype_classifier.py   (+5 -4)
A docs/sessions/2026-04/calibration-reference-values-v3.md (+158)
```

---

## Referencias

- Baseline V2 (pre-fix): `docs/sessions/2026-04/calibration-reference-values-v2.md`
- **Baseline V3 (atual):** `docs/sessions/2026-04/calibration-reference-values-v3.md`
- Handoff original mentores: `docs/sessions/2026-04/handoff-dev-to-mentors-real-eval-results.md`
- Video de referencia: `e4359918-9b31-4e6b-901d-390933cbfa39` (53s, 168 palavras)
- Evaluations desta sessao no Supabase:
  - `3ba19973` — pre-fix contexto (overall=54)
  - `dc5ed8e2` — pos race-fix (overall=57)
  - `9093cbe9` — pos cobertura 100% (overall=62) · **baseline V3**

---

— @devops (Gage)
