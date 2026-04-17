# Gate 2 Smoke — Story 9.1 (Pendente @qa)

**Story:** 9.1 — Aggregator Refactor + Confidence Badges
**Branch:** `feature/9.1-aggregator-refactor-confidence-badges`
**Commits:** c773d34, a6b21d8, 825e838, ed48a54, d3355c2, (este)
**Target:** 10 vídeos de calibração, delta ≤15pt, rastreabilidade, direção consistente

---

## Critério Ajustado pelo @po (2026-04-16)

Diferente do gate_2_regression genérico (≤5pt). Story 9.1 muda a fórmula:

1. **Delta overall_score ≤ 15 pontos** em cada vídeo
2. **Cada delta rastreável à nova fórmula** (diferença explicável em texto livre)
3. **Direção consistente:** vídeos monotônicos ↓ (porque nova fórmula pesa mais variety), vídeos variados ↑

---

## Protocolo de execução (@qa ou @dev em modo smoke)

### 1. Setup

```bash
# Branch checkout
git checkout feature/9.1-aggregator-refactor-confidence-badges

# Selecionar 10 evaluations do Supabase (ideal: mix de monotônicos e variados)
# SELECT id FROM evaluations WHERE status='complete' ORDER BY created_at DESC LIMIT 10;
```

### 2. Replay em cada eval

Para cada eval_id:

```bash
# Path OFF (baseline v0.6.0)
STATE_OF_ART_ENABLED=false python -m ml_worker.scripts.replay_eval <eval_id>
# → coleta overall_score_v060

# Path ON (novo v0.7.0)
STATE_OF_ART_ENABLED=true python -m ml_worker.scripts.replay_eval <eval_id>
# → coleta overall_score_v070
```

**Script `replay_eval.py` pendente** — usa `detailed_metrics` salvo em
`analysis_results` + re-executa apenas `aggregate_metrics()` e `generate_report`.
Não re-processa video (rápido, zero custo).

### 3. Preencher tabela abaixo

| # | eval_id | contexto | monotônico? | v0.6.0 | v0.7.0 | delta | explicação rastreável | veredito |
|---|---------|----------|-------------|--------|--------|-------|-----------------------|----------|
| 1 | — | — | — | — | — | — | — | ⬜ |
| 2 | — | — | — | — | — | — | — | ⬜ |
| 3 | — | — | — | — | — | — | — | ⬜ |
| 4 | — | — | — | — | — | — | — | ⬜ |
| 5 | — | — | — | — | — | — | — | ⬜ |
| 6 | — | — | — | — | — | — | — | ⬜ |
| 7 | — | — | — | — | — | — | — | ⬜ |
| 8 | — | — | — | — | — | — | — | ⬜ |
| 9 | — | — | — | — | — | — | — | ⬜ |
| 10| — | — | — | — | — | — | — | ⬜ |

**Exemplo de linha preenchida:**

| # | eval_id | contexto | monotônico? | v0.6.0 | v0.7.0 | delta | explicação rastreável | veredito |
|---|---------|----------|-------------|--------|--------|-------|-----------------------|----------|
| 1 | abc123  | palco    | sim         | 72     | 64     | -8    | facial agora pesa 0.14 (era 0), tem smile baixo. variety 0.22 vs 0.25 antes, mas monotonia mais penalizada pelo novo peso. | ✅ |

### 4. Decisão final

**Gate 2 Story 9.1 PASS se:**
- [ ] Todos os 10 vídeos com delta ≤15 pontos
- [ ] Todos os deltas têm explicação rastreável à fórmula
- [ ] Vídeos classificados como "monotônicos" têm delta ≤0 (ou positivo pequeno)
- [ ] Vídeos classificados como "variados" têm delta ≥0 (ou negativo pequeno)
- [ ] Zero crashes / unhandled exceptions durante replay

**Gate 2 FAIL:**
- Delta >15pt em qualquer vídeo sem explicação da fórmula → @dev revisa pesos
- Direção inconsistente (monotônico subiu, variado desceu) → revisar heurística
  (possível trigger de Story 9.7 calibração antecipada)

---

## Pós-PASS

1. @qa gera `docs/qa/gates/9.1-aggregator-refactor.yml` com verdict=PASS
2. @devops abre PR `feat(epic-9): story 9.1 aggregator refactor + confidence badges`
3. Merge em `main` com flag default `STATE_OF_ART_ENABLED=false` (zero impacto prod)
4. Rollout em shadow: ativar flag via env var em staging, comparar 100 evals
5. Flip produção após 1 semana estável

---

**Status:** ✅ **EXECUTADO 2026-04-17** via Story 9.1.1
**Resultados:** `docs/qa/gate2-story91-results.md`
**Script:** `ml-worker/scripts/replay_eval.py`
**Verdict:** PASS (max delta 5pt ≤ 15pt threshold)
