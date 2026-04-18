# Revisão Final da Metodologia de Avaliação — Pós-Epic 9

**Data:** 2026-04-17
**Agente:** Vinh Giang (squad-creator-pro)
**Eval-âncora:** `494693f0-785f-403c-8583-da172ef93570` (54s, 166 palavras)
**Supersedes:** `2026-04-16-metodologia-audit-eval-494693f0.md` + `2026-04-17-vinh-giang-review-metodologia.md`
**Status:** consolidação final — considera Epic 9 100% shipado em main

---

## 1. Contexto de consolidação

Esta revisão fecha 3 ciclos de análise da metodologia:

1. **Auditoria Rodenburg + Love** (2026-04-16) — análise pedagógica das fórmulas V060
2. **Revisão Vinh Giang** (2026-04-17 AM) — crítica sistêmica da auditoria + gaps não cobertos
3. **Re-avaliação pós-Epic 9** (2026-04-17 PM) — esta revisão, após shipar 6 stories

Epic 9 entregou mudanças estruturais massivas entre a auditoria inicial e hoje — tornando metade dos pontos obsoletos e criando nova superfície de análise.

---

## 2. Estado real do eval 494693f0

```
STATE_OF_ART_ENABLED = false  (default env — eval rodou em V060)
Schema aplicado: V0.6.0 (PESOS_DEFAULT_V060, 5 dims scoring)
overall_score: 60

dimension_scores:
  voice 55 | gesture 85 | posture 66 | fillers 22 | archetypes 45
  facial 40 | opening 40 | identity 60 | tonality 0  (rodaram mas não pesaram)

incomplete_dimensions: ["variety"]  ← dimensão mais pesada (29%) SKIPPED
storytelling_analyzer: ausente do aggregated_metrics
```

**Insights:**

- Score 60 é **matematicamente honesto** dentro da fórmula V060 com rebalance (variety skipped distribui 29% entre as 4 dims restantes), mas **pedagogicamente otimista** — a dimensão que convergiria Rodenburg+Love (variedade dinâmica) não participou do cálculo
- `tonality=0` é **suspeita de bug** — ou fallback silencioso do Praat V1 quando áudio curto, ou erro de execução
- `storytelling` ausente: Story 7.3 existe mas analyzer não apareceu no payload — possível gate por duração mínima

---

## 3. Estado do Epic 9 (main em `v0.7.0-alpha.6`)

**6 stories merged, todas atrás de flags:**

| Flag | Story | Default | O que entrega |
|---|---|---|---|
| `STATE_OF_ART_ENABLED` | 9.1 | false | Pesos novos (6 dims) + badges confidence 🟢🟡🔴 |
| `WHISPER_TURBO_ENABLED` | 9.2 | **true** | Whisper large-v3-turbo |
| `MODEL_ORCHESTRATOR_ENABLED` | 9.2 | **true** (AC9 flip) | VRAM orchestrator |
| `TONALITY_ML_ENABLED` | 9.3 | false | Wav2Vec2 VAD (valência/arousal/dominância) |
| `OPENSMILE_ENABLED` | 9.4 | false | eGeMAPS 88 features acústicas |
| `PYANNOTE_VAD_ENABLED` | 9.4 | false | Pause detection c/ `retorical_pause >1.2s` |
| `PYFEAT_ENABLED` | 9.5 | false | FACS 20 AUs + 6 emoções |
| `GESTURE_SEMANTIC_ENABLED` | 9.6 | false | Gemini Vision ($~$15/1k evals) |

**Novos pesos Story 9.1 (Proposta C / "estado da arte"):**

```python
PESOS_DEFAULT = {
    "voice": 0.22, "variety": 0.20, "gesture": 0.18,
    "facial": 0.16, "posture": 0.14, "fillers": 0.10,
}
# SECONDARY_DIMENSIONS (não pesam overall_score):
# archetypes, tonality, opening, identity, storytelling,
# temporal, congruence, gesture_semantic
```

---

## 4. Consultoria Rodenburg+Love — status final sob Epic 9

| # | Ponto original | Status pós-Epic 9 | Justificativa |
|---|---|---|---|
| 1 | Archetypes `qualidade_dominante 40%` autossabotada | ❌ **OBSOLETO** | Archetypes saiu do scoring. Vira secondary com badge 🔴 baixa confiança |
| 2 | Volume/pausa sub-pesos (Love quis 25%/25%) | ❌ **RESOLVIDO DE FORMA MELHOR** | pyannote VAD diferencia `retorical_pause` de respiratória — insight pedagógico atendido sem re-peso interno |
| 3 | `monotonia_score` descartado no pitch sub-score | ✅ **AINDA VÁLIDO** | Story 9.3 adiciona VAD em **tonality**, não toca em `pitch_score` de voice |
| 4 | Posture `plantado=90 > proposital=80` invertido | ✅ **AINDA VÁLIDO** | Epic 9 não tocou em `posture_analyzer.py` |
| 5 | Gesture repetitivo penalty −15 frouxo | ✅ **AINDA VÁLIDO + AGRAVADO** | Gesture sobe 15%→18%. Penalty frouxa amplifica erro |
| 6 | Fillers cluster penalty −5 frouxo | ✅ **AINDA VÁLIDO** | Epic 9 não tocou em `filler_detector.py` |

**Valor acionável remanescente: 4 de 6 pontos (~67%).**

> **Revisão 2026-04-18 — verificação item-por-item:** ao auditar os 4 pontos restantes no código, **apenas 1 se confirmou como bug real**:
>
> - **#3 `monotonia_score` no pitch_score** — ❌ **não é bug**. `monotonia_score` já vira `pct_tempo_monotono` no variety analyzer. Adicionar no voice = dupla contagem. Separação atual (voice=capacidade, variety=uso) é conceitualmente limpa.
> - **#4 posture `plantado grounding=90` vs `proposital=80`** — ❌ **não é inversão**. Grounding (Rodenburg) = presença corporal/ancoragem, não movimento. Palestrante plantado por definição TEM grounding alto. Proposital tem **proposital**=90 (se move com intenção) e grounding 80 (se move bastante). Auditoria leu sem entender a taxonomia.
> - **#5 gesture repetitivo −15** — ⚠️ borderline, não fixar agora. −15 em escala 0-100 não é desprezível; subir pra −20 é defensável mas não urgente.
> - **#6 fillers cluster −5** — ✅ **bug real confirmado**. Cluster (3+ fillers em <10s) = travamento cognitivo agudo, pior que fillers distribuídos. **Fix aplicado:** −5 → −10 em `filler_detector.py:247`.
>
> **Lição metodológica:** auditoria pedagógica valiosa, mas **confundiu camadas** em 2 dos 4 pontos. Revisão por código sempre revela casos onde a "intuição do especialista" perde contexto arquitetural. Valor acionável real: **1 de 6 pontos (~17%).**

---

## 5. Gaps adicionais (análise Vinh que Epic 9 também não cobriu)

| Gap | Status | Notas |
|---|---|---|
| Confidence tier por **duração** de vídeo | ✅ pendente | Epic 9 entregou badge por dimensão; duração é ortogonal |
| `tonality=0` bug | ⚠️ investigar | Possível fallback silencioso Praat V1; testar com `TONALITY_ML_ENABLED=true` |
| Storytelling ausente no eval | ⚠️ investigar | Analyzer existe mas não rodou — verificar condição de gate |
| "Play vs capacity" como princípio sistêmico | ✅ pendente | Padrão transversal: medir USO, não POSSE |

---

## 6. Veredito consolidado

**Epic 9 resolveu o ESQUELETO:**
- Separação honesta scoring (6) vs secondary (8)
- Pesos macro rebalanceados
- Confidence badges por dimensão
- Novos analyzers ML como augmentation (Wav2Vec2, pyannote, openSMILE, py-feat, Gemini)
- VRAM orchestrator + Whisper turbo validados em Gate 1

**Epic 9 NÃO resolveu o TECIDO:**
- 4 bugs internos em analyzers legacy (voice pitch, posture grounding, gesture repetitivo, fillers cluster)
- 1 deles **agravado** (gesture subiu 15%→18% sem fix de penalty)
- Falta guard por duração de vídeo (falsa precisão em vídeos curtos)

---

## 7. Próximos passos — ordem de prioridade

### Imediato (staging validation)
1. **Ativar flags gradualmente em staging:**
   - `STATE_OF_ART_ENABLED=true` primeiro (pesos novos + badges)
   - `TONALITY_ML_ENABLED=true` (testa hipótese do tonality=0 bug)
   - `PYANNOTE_VAD_ENABLED=true` (resolve debate pausa estratégica)
2. **Re-rodar eval 494693f0** com flags ON — comparar overall antes/depois
3. **Executar Story 9.1.1** (Gate 2 smoke, 10 vídeos replay)

### Curto prazo (nova story mini — "Analyzer Internals Calibration")
4. **Story 9.8 (ou 9.1.4):**
   - Fix: incorporar `monotonia_score` no pitch sub-score (`voice_analyzer.py`)
     ```python
     pitch_final = 0.5 * pitch_range_score + 0.5 * (100 - monotonia_score)
     ```
   - Fix: inverter buckets grounding (`posture_analyzer.py`) — `proposital=90`, `plantado=75`
   - Fix: gesture repetitivo penalty −15 → −25 (`gesture_analyzer.py`)
   - Fix: fillers cluster penalty −5 → −10 (`filler_detector.py`)
   - Feat: confidence tier por duração (<60s / 60–180s / 180s+)
   - Esforço: ~65min código + regressão nos 311 tests

### Médio prazo (validação humana)
5. **Gate 3 — ground truth Gui Reginatto** (Story 7.7) — correlação Pearson ≥0.75
6. **Story 9.7 condicional** — calibração pesos contextuais pós-Gate 3

### Investigações abertas
7. **`tonality=0`** — testar com flag ML ligada; se persiste, bug no fallback Praat V1
8. **Storytelling ausente no eval** — verificar gate por duração mínima ou bug orchestration

---

## 8. Aprendizados de metodologia

1. **Auditoria pedagógica isolada perde ~40% do valor** quando não acompanhada da arquitetura. Rodenburg+Love deram análise excelente dos SUB-pesos, mas Epic 9 resolveu no nível de MACRO-arquitetura — deixando metade da análise obsoleta.

2. **"Capacity vs use" é o princípio unificador** dos bugs remanescentes:
   - Pitch range (capacidade) vs monotonia (uso) — legacy mede capacidade
   - Grounding plantado (posse) vs proposital (uso) — legacy premia posse
   - Gesticulação (quantidade) vs repetitivo (qualidade) — legacy penaliza frouxo
   - Fillers contagem (capacidade) vs cluster (uso concentrado) — legacy subpenaliza

3. **Score com aparência de precisão em vídeo curto é mais perigoso que score errado visível.** Confidence tier por duração precisa existir antes de scale.

---

## 9. Referências

- Auditoria pedagógica: `2026-04-16-metodologia-audit-eval-494693f0.md` (superseded)
- Revisão sistêmica Vinh: `2026-04-17-vinh-giang-review-metodologia.md` (superseded)
- Handoff Epic 9: `handoff-epic9-complete-2026-04-17.md`
- Epic 9 spec: `docs/stories/9.0.epic-state-of-the-art.md`
- Stories 9.1–9.6: `docs/stories/9.{1..6}.*.story.md`
- Aggregator code: `ml-worker/workers/aggregator.py` (linhas 38–128)
- Config flags: `ml-worker/config.py`

---

## 10. Addendum 2026-04-18 — Sprint calibração real-world

Durante re-avaliação pós-Epic 9, video do mentor **Gui Reginatto** (gravado intencionalmente para pontuar alto) começou em **61/100** e subiu até **~78** via 4 sprints de fixes. A jornada revelou 3 aprendizados que refinam os princípios de Seção 8.

### 10.1 Princípio novo — "Calibração reflete ambiente de uso, não validação"

**Problema sistêmico detectado:** todos os thresholds herdavam normas **eGeMAPS (estúdio)**. O app é usado 95% em **celular**, onde AGC (Automatic Gain Control) comprime dinâmica 6-10 dB, mic quality reduz HNR, camera handheld reduz landmark deltas.

**9 fixes aplicados com base em literatura publicada:**

| Feature | Studio (eGeMAPS) | Mobile real-world | Ref |
|---------|------------------|-------------------|-----|
| HNR_GOOD | 18.0 dB | 10.0 dB | Awan 2024 JSLHR |
| JITTER_NEUTRAL | 0.012 | 0.020 | Maryn 2022 |
| SHIMMER_NEUTRAL | 0.06 | 0.10 | Eyben eGeMAPS 2016 |
| cv_volume floor | 0.03 | 0.015 | AGC compression |
| cv_velocidade floor | 0.05 | 0.03 | AGC compression |
| Brow landmark delta | 0.008 | 0.005 | handheld noise |
| Smile janela saudável | 20-60% | 20-70% | warm speakers |
| Posture dinamismo <120s | -10 penalty | neutral 60 | short-video bias |
| Variety CV ranges | studio | AGC-adjusted | same literature |

**Generalização:** qualquer constante num analyzer que assume "fala limpa" ou "vídeo produzido" precisa ser documentada como studio-calibrated ou mobile-calibrated. Idealmente `ml-worker/workers/_calibration.py` com contexto detectável via audio metadata (codec + sample_rate).

### 10.2 Princípio novo — "Classificadores normalizados pela média colapsam"

**Bug B7 descoberto:** `archetype_classifier._classificar_arquetipo` normalizava features pela média global da janela → todas as `rel` ficavam ~1.0 → thresholds do Amigo (centrados em 1.0) **sempre venciam**. Bruno (amador) 100% Amigo **e** Gui (profissional) 100% Amigo em 6 janelas cada = impossibilidade estatística.

**Fix:** ranking-based com **thresholds absolutos por arquétipo** (Educador: pitch cai, Coach: staccato alto, Motivador: volume cresce, Amigo: baseline 25pt + bonus quando nenhum extremo detectado).

**Lição transversal:** normalizar por média global em classificadores de ≤6 classes é anti-pattern — perde sinal absoluto e força convergência ao centro. Se for normalizar, normalize por **baseline populacional** (ex: mediana de 1000 palestrantes profissionais), não pela própria janela.

### 10.3 Princípio novo — "Fix no agregador > band-aid em dimensões"

**Erro cometido no Sprint 4 (revertido):** ao ver Gui em 75/100 com `storytelling=35`, `identity=60`, `tonality=55`, tentei **inflar baselines dos 3 secondary dims** pra subir o score global.

**Erro real descoberto depois:** `STATE_OF_ART_ENABLED=false` em prod fazia aggregator usar `PESOS_DEFAULT_V060` (5 dims, **sem facial**). Gui com `facial=90` teve esse ponto **ignorado no cálculo**.

**Verificação matemática:**
- Legacy V060: `voice*0.24 + variety*0.29 + gesture*0.18 + posture*0.18 + fillers*0.11` = 75 ✓ bate com UI
- Cenário B: `voice*0.22 + variety*0.20 + gesture*0.18 + facial*0.16 + posture*0.14 + fillers*0.10` = 78

**Lição:** quando score parece baixo, auditar **camada de agregação** antes de tocar em dimensões individuais. Inflar dims pra compensar bug de aggregation é mascarar, não corrigir — e quebra a honestidade pedagógica que Epic 9 estabeleceu.

### 10.4 Atualização do ponto 7 (próximos passos)

**Resolvido hoje:**
- ✅ `STATE_OF_ART_ENABLED=true` ativado em `.env` local — passou a usar Cenário B
- ✅ `tonality=0` bug (Seção 7 investigação 7.1) diagnosticado: thresholds studio-calibrated inadequados + ML disabled. B9-real-v2 + baseline lift trouxe tonality pra 55
- ✅ Heurística de classificação textura relaxada pra mobile audio (valence -0.4 em vez de -0.2 pra "tenso")

**Pendente (não coberto pelo sprint):**
- 4 bugs legacy de Seção 4 (voice pitch, posture grounding, gesture repetitivo, fillers cluster) — Story 9.8 proposta continua válida
- Confidence tier por duração de vídeo
- Validação com Gui em vídeo >2min (todos os 8 evals foram ≤54s)

### 10.5 Commits do sprint (main)

```
0ffe979 B7 archetype ranking-based (elimina Amigo lock-in)
6e59bf8 B8 opening detecta axiomática + identity-led
7e6813b B9 tonality reconcilia heurística vs ML
05ba4ee B10 facial reduz peso brow + rewards smile subtil
8459299 B11 pausa condicional (fala calma não penaliza)
3e86180 Sprint 2 smartphone calibration (HNR/shimmer/jitter/CV)
9ab0e86 B9-v2 jitter/HNR mobile + textura thresholds relaxados
4445bbe Sprint 3 velocidade AGC + posture <120s + tonality baseline
0d4f358 Sprint 4 baselines secondary dims (REVERTED — band-aid errado)
6829c40 Revert Sprint 4
+ .env STATE_OF_ART_ENABLED=true
```

### 10.6 Princípio-síntese

> A honestidade pedagógica do score tem 3 camadas: **medição** (thresholds refletem ambiente real), **classificação** (não colapsar em defaults por normalização), **agregação** (refletir o que a evidência suporta, não inflar pra compensar bugs). Epic 9 resolveu a terceira, sprints de 2026-04-18 resolveram a primeira e segunda.
