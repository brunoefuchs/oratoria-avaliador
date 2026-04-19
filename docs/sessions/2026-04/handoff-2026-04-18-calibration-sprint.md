# Handoff — Sprint Calibração 2026-04-18

**Duração:** ~8h autônomas (sessão mais longa de calibração do projeto)
**Agente principal:** @vinh-giang (coaching) + @dev (implementação) + @devops (push)
**Estado final:** main em `a863783`, push completo, ml-worker local em :7860

---

## 1. TL;DR

Em 8h de calibração sistemática:
- **19 commits** em main (18 fixes + 1 doc)
- **Gui (palestrante profissional):** 61 → **81** (+20pts)
- **Bruno (coaching baseline):** 50 → **59** (+9pts)
- **Gap discriminativo:** 22pts — app distingue níveis comunicativos
- **Cross-validation** via Gemini Vision confirmou calibração matemática
- **3 princípios metodológicos** salvos em memória pra futuros ciclos

---

## 2. Sprints executados

### Sprint 1 (B7-B11) — Fixes primários
Commits `0ffe979` → `8459299`. 5 fixes bloqueando discriminação real:
- **B7** archetype classifier ranking-based (eliminou Amigo-lock-in universal)
- **B8** opening detecta declaração axiomática + identity-led intros
- **B9** tonality reconcilia heurística vs ML (quando divergem)
- **B10** facial reduz peso brow + rewards smile subtil
- **B11** pausa condicional (fala calma não penaliza)

### Sprint 2 (smartphone-first) — Calibração real-world
Commits `3e86180` → `9ab0e86`. Literatura Awan 2024 / Maryn 2022 / Eyben 2016.
Thresholds migraram de eGeMAPS studio → smartphone real-world:
- HNR_GOOD 18.0 → 10.0
- SHIMMER_NEUTRAL 0.06 → 0.10
- JITTER_NEUTRAL 0.012 → 0.020
- cv_volume floor 0.03 → 0.015
- brow landmark threshold 0.008 → 0.005
- smile janela saudável 20-60 → 20-70

### Sprint 3 — Bottleneck surgery
Commit `4445bbe`. 3 ajustes cirúrgicos:
- voice velocidade AGC (cv_velocidade piso 0.05→0.03)
- posture dinamismo <120s → min 60 (não 30)
- tonality baseline 30→45

### Sprint 4 — REVERTED
Commits `0d4f358` + `6829c40`. Tentativa de inflar secondary dims foi erro.
Insight: fix na camada de **agregação** (STATE_OF_ART_ENABLED=true) resolveu.

### Sprint 5 (aggregation) — Achado do dia
**`STATE_OF_ART_ENABLED=true`** no `.env` local. Aggregator passou a usar pesos
Cenário B (6 dims com facial=0.16) em vez de legacy V060 (5 dims, sem facial).
Efeito Gui: 75 → 78 imediatamente, só porque facial=90 passou a contar.

### Sprint 6 — Cross-validation via Gemini Vision
Commit `e0605c8`. Story 9.6 descoberta como **não plugada** em app.py —
`analyze_gesture_semantic` existia mas nunca era chamado. Integrei dispatch
pós-transcription como opt-in.

Cross-validation no Gui:
- `variety.variacao_gesticulacao`: 33 "caótica" → 80 "ideal" (Opção A)
- `gesture_semantic` (Gemini Vision): 95 "excepcional"
- **Convergência math-ML confirmou Opção A sem precisar Gemini em produção**
- Custo real: **$0.0013/eval** (54s vídeo, 29 frames)

Penalidade `gesto_repetitivo` refatorada de binária −15 → proporcional ao
`unique_ratio` (−10 mild, −20 claro, −30 severo).

### Sprint 7 — Fillers cluster
Commit `8a91b16`. Cluster penalty −5 → −10 (travamento cognitivo merece peso).

### Sprint 8 — Pausa retórica por contexto lexical
Commits `3312d9e` + `a863783`. Fix duplo:
1. **Threshold lexical:** pausa 0.35-0.5s vira estratégica SE palavra seguinte
   não for conectivo/muleta (CONTINUACAO_WORDS set).
2. **Scoring por densidade + ratio modulator:**
   ```
   densidade_score: >=4/min=100, >=2=85, >=1=70, >0=55, 0=30
   quality_factor = min(1.0, ratio_estrategicas * 2)
   pausa_score = densidade * factor - penalidade_hesitacao
   ```

Validação: Gui `6.2/min, ratio 0.50` → pausa **100**. Bruno
`6.7/min, ratio 0.33` → pausa **67** (ratio puniu metade-metade).

---

## 3. Evolução dos evals-âncora

### Gui Reginatto (54s profissional, intentional high-score recording)
```
eccce5b7 (original, pre-sprint):  61/100 (legacy V060, facial ignorado)
aca79d1d (pós upload calibrado):  78/100
d4cff03d (pós Sprint 3):          75/100
172e5568 (pós Sprint 3 mais):     75/100
dbe6ebcb (pós Sprint 5, A-only):  80/100
5a267eb4 (A+B sem dispatch):      80/100
e8de151c (A+B dispatched):        80/100 + gesture_semantic=95
3c5e8934 (pós penalty proporcional): 79/100
6148aa8b (pós Fix 1 lexical):     80/100
cda26f15 (pós densidade base):    81/100 — pausa 100
00d61f44 (pós modulator ratio):   81/100 — pausa 100 mantida
```

### Bruno (54s amador, archetype lock-in Amigo)
```
8534ca9e (original, pre-sprint):  50/100 (100% Amigo, tonality=0)
b6a9f5bc (cross-check com Gemini): 58/100 + gesture_semantic=85
f24b1ddf (pós penalty proporcional): 58/100
b3aa4ff1 (pós refinamento pausa): 59/100 — pausa caiu de 100 → 67
```

---

## 4. Arquivos modificados (18 fixes)

```
ml-worker/workers/archetype_classifier.py  (B7)
ml-worker/workers/opening_analyzer.py      (B8)
ml-worker/workers/tonality_analyzer.py     (B9, B9-v2, baseline)
ml-worker/workers/facial_analyzer.py       (B10, smile janela)
ml-worker/workers/voice_analyzer.py        (B11, velocidade AGC, pausa x3)
ml-worker/workers/variety_analyzer.py      (B12 AGC, Opção A gesticulacao)
ml-worker/workers/gesture_analyzer.py      (penalty proporcional unique_ratio)
ml-worker/workers/filler_detector.py       (cluster penalty -5→-10)
ml-worker/workers/posture_analyzer.py      (dinamismo <120s)
ml-worker/app.py                            (gesture_semantic dispatch)
ml-worker/.env                              (STATE_OF_ART_ENABLED=true)
ml-worker/scripts/reprocess_eval.py         (utility)
docs/sessions/2026-04/2026-04-17-metodologia-revisao-final-pos-epic9.md
  (seções 10.1-10.9 addendum)
```

---

## 5. 3 princípios metodológicos salvos em memória

Todas em `/home/bruno/.claude/projects/-mnt-c-Users-bruno-code-oratoria-avaliador/memory/`:

### `feedback_validacao_dupla.md`
> Quando existe método alternativo pra validar supposition, usar antes de propagar fix. ROI: 30min de validação vs erro propagado em 10k evals.

### `feedback_gemini_vision_on_demand.md`
> ML pago ($0.0013/eval/min em Gemini) só ativar em dims onde math é comprovadamente fraca. Nunca default. Rate limits + latência +84s + custo ampliado por duração.

### Princípio-síntese (doc metodologia Seção 10.6)
> Honestidade pedagógica tem 3 camadas: **medição** (thresholds refletem ambiente), **classificação** (não colapsar em defaults), **agregação** (refletir evidência). Epic 9 resolveu 3ª, sprint 04-18 resolveu 1ª e 2ª.

---

## 6. Estado da infraestrutura

### Flags em `.env` local
```
STATE_OF_ART_ENABLED=true          # Cenário B pesos (6 dims com facial)
# GESTURE_SEMANTIC_ENABLED=true    # opt-in via shell export apenas
```

### Outros flags desligados (opt-in em produção)
- `TONALITY_ML_ENABLED` (Wav2Vec2 VAD)
- `OPENSMILE_ENABLED`
- `PYANNOTE_VAD_ENABLED`
- `PYFEAT_ENABLED`

### ml-worker
Rodando local em `localhost:7860`. Script de reprocess disponível:
```bash
cd ml-worker
export $(grep -v '^#' .env | xargs)
.venv/bin/python scripts/reprocess_eval.py <source_eval_id> "label"
```

### Testes
311 passed, all workers limpos via ruff.

---

## 7. Pendências conhecidas

### P1 — validação em fala sustentada
Todos os 20+ evals rodados hoje foram ≤54s. **Calibração não foi validada em
vídeos >2min**. Possíveis regressões esperadas:
- `posture` short-video floor (60) não aplica em longos, pode ficar muito severo
- `variety` thresholds mobile podem ser diferentes em áudio longo (AGC ajusta
  dinamicamente em calls longas)
- `gesto_repetitivo` com unique_ratio em window de 20 frames subestima em vídeo
  longo (mesmos 20 frames = janela muito curta proporcionalmente)

### P2 — 3 dims secundárias continuam baixas em Gui
- `storytelling` 35 (conteúdo educacional sem bridge canônica)
- `identity` 60 (dados_insuficientes + total_vicios=0 → não merece score médio)
- `tonality` 40-55 (heurística mobile ainda mapeia em 2-3 texturas)

**Não afetam overall_score** (são secondary), mas aparecem no detalhamento.
Fix de cada exige análise semântica própria.

### P3 — Gemini Vision não determinístico
Chamadas repetidas no mesmo vídeo deram 95 então 85 (Gui) ou 85 então 90
(Bruno). Variabilidade ±10pts. Implicação: **não usar como ground truth**,
só sanity check. Se virar feature em produção, cachear resultado por eval_id.

### P4 — Story 9.6 (gesture_semantic) foi plugada mas sem tests
Dispatch integrado em `app.py` mas sem teste unitário específico pra integração.
Próximo ciclo deveria adicionar teste que mock o Gemini e valida dispatch.

---

## 8. Para retomar

### Checklist pra próxima sessão

1. ✅ `git pull origin main` (incluir `a863783`)
2. ✅ ml-worker: kill antigo + restart com flag atualizada:
   ```bash
   cd ml-worker
   pkill -f "uvicorn app:app"
   export $(grep -v '^#' .env | xargs)
   .venv/bin/uvicorn app:app --host 0.0.0.0 --port 7860
   ```
3. ✅ Ler memórias novas: `feedback_validacao_dupla`, `feedback_gemini_vision_on_demand`
4. ✅ Ler Seções 10.1-10.9 do doc metodologia (principles cristalizados)

### Prioridades sugeridas

1. **Validar em vídeo longo** (>3min). Gui ou novo palestrante.
2. **Story 9.8** — 1 fix legítimo remanescente (fillers cluster) já foi feito hoje;
   os outros 3 "bugs" legacy foram validados como NÃO bugs (auditoria pedagógica
   confundiu camadas). Story 9.8 pode ser fechada ou re-escopada pra:
   - Adicionar cross-reference de gesto-palavra (Gemini ou POS tagging)
   - Validar calibração smartphone em longo
3. **Review do dashboard** — UI hoje mostra números sem contexto. Principalmente:
   - Variacao_gesticulacao vs gesto_repetitivo (são ORTOGONAIS, UI confunde)
   - Pausa_score = 100 quando 6 estratégicas detectadas — feedback explicar o "porquê"

---

## 9. Trilha de commits (cronológica)

```
a863783  fix: pausa_score densidade + modulator ratio
3312d9e  fix: pausa retorica deteccao por contexto lexical
baf7007  docs: secoes 10.7-10.9 cross-validation via Gemini Vision
e0605c8  fix: calibration validada via Gemini Vision cross-check
8a91b16  fix: fillers cluster penalty -5 → -10 + doc revisao
6829c40  Revert Sprint 4
0d4f358  Sprint 4 (REVERTED)
4445bbe  Sprint 3 velocidade AGC + posture <120s + tonality baseline
9ab0e86  B9-v2 jitter/HNR mobile + textura thresholds relaxados
3e86180  Sprint 2 real-world calibration
8459299  B11 pausa condicional
05ba4ee  B10 facial brow peso reduzido
7e6813b  B9 tonality reconcilia heuristica vs ML
6e59bf8  B8 opening declaracao axiomatica + identity-led
0ffe979  B7 archetype ranking-based (elimina Amigo lock-in)
```

---

## 10. Princípio-síntese final

> **"Um erro propagado custa caro. Um erro consertado na raiz é ROI."**  — user, 2026-04-18

Hoje foi dia inteiro consertando raízes:
- Thresholds studio → mobile (camada de **medição**)
- Classifier normalizado → ranking absoluto (camada de **classificação**)
- Pausa por duração → pausa por duração + contexto lexical + ratio (camada de **semântica**)
- Pesos Cenário B ativos (camada de **agregação**)
- Validação cruzada via método ortogonal (Gemini) **antes** de propagar

O app passa a estar pronto pra **escalar com honestidade** — não só com aparência de precisão.

Próxima sessão: validar fora do laboratório dos 54s.
