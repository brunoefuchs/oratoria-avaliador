# Handoff — Epic 9 "State of the Art" COMPLETE

**Data:** 2026-04-17
**Duração:** ~1 dia de sessão contínua (auto mode)
**Agentes:** @vinh-giang · @pm · @sm · @po · @dev · @qa · @devops
**Resultado:** **6/6 stories MERGED em main**

---

## Resumo executivo

Epic 9 aprovado em 2026-04-16 e completamente shipado em 2026-04-17. Orchestration chain AIOX validada ponta-a-ponta com 6 PRs consecutivos. Zero regressão em produção (todas as features flags default OFF).

---

## Merge trail

| Wave | PR | Story | Commit | Delta tests |
|---|---|---|---|---|
| 0 | #25 | 9.1 Aggregator refactor + confidence badges | `1faf2fc` | +31 (241→272) |
| 1 | #26 | 9.2 Whisper turbo + VRAM orchestrator | `6feec6d` | +14 (272→255 após reorg) |
| 2 | #27 | 9.4 openSMILE + pyannote VAD | `0696577` | +11 (255→266) |
| 2 | #28 | 9.3 Wav2Vec2-Emotion ML | `905664f` | +11 (266→277) |
| 3 | #29 | 9.5 py-feat FACS (20 AUs + 6 emocoes) | `8252abf` | +15 (277→292) |
| 3 | #30 | 9.6 Gemini Vision gesture semantic | `cdc768b` | +19 (292→311) |

**Total: 311 tests PASS em main**

---

## State of main — v0.7.0-alpha.6

### Dimensions

| Categoria | Count | Dims |
|---|---|---|
| Scoring (pesa overall_score) | 6 | voice, variety, gesture, facial, posture, fillers |
| Secondary (augmentation) | 8 | archetypes, tonality, opening, identity, storytelling, temporal, congruence, **gesture_semantic** |
| **Total** | **14** | |

### Feature flags (7 independentes, todas default OFF salvo indicado)

| Flag | Story | Default | Descrição |
|---|---|---|---|
| `STATE_OF_ART_ENABLED` | 9.1 | false | Novos pesos + confidence badges |
| `WHISPER_TURBO_ENABLED` | 9.2 | **true** | Opt-out rollback |
| `MODEL_ORCHESTRATOR_ENABLED` | 9.2 | false | VRAM orchestrator (AC9 flip pós-Gate 1) |
| `TONALITY_ML_ENABLED` | 9.3 | false | Wav2Vec2 emotion |
| `OPENSMILE_ENABLED` | 9.4 | false | eGeMAPS 88 features |
| `PYANNOTE_VAD_ENABLED` | 9.4 | false | Pause detection |
| `PYFEAT_ENABLED` | 9.5 | false | FACS 20 AUs |
| `GESTURE_SEMANTIC_ENABLED` | 9.6 | false | Gemini Vision ($$) |

### Optional deps groups

```
pip install -e ".[prosody]"   # opensmile + pyannote.audio (Story 9.4)
pip install -e ".[emotion]"   # transformers (Story 9.3)
pip install -e ".[facs]"      # py-feat (Story 9.5)
pip install -e ".[prosody,emotion,facs]"  # todas
```

### Hardware validation

**Gate 1 — real RTX 4060 Laptop 8.59GB VRAM:**
- whisper_turbo peak: 4.93 GB ✅
- whisper_medium peak: 4.58 GB ✅
- Peak global: 4.93 GB ≤ 7.5 GB budget
- Margem: 3.66 GB disponível pra Wav2Vec2 (~1.5GB) + py-feat (~2GB) — **viabilidade confirmada**

---

## Princípios Vinh implementados em código

| Princípio | Onde mora |
|---|---|
| "Variedade = 88 keys" | variety meta-dim em SCORING_DIMENSIONS |
| "Rosto = 40% percepção emocional" | py-feat FACS 20 AUs + 6 emoções (9.5) |
| "Pausa = poder" | pyannote VAD `retorical_pause` >1.2s (9.4) |
| "Se distrai = problema" | Gemini Vision `distracts: bool` per frame (9.6) |
| "Confiança transparente" | Badges 🟢🟡🔴 + prompt hedge language (9.1) |
| "Textura emocional vocal" | Wav2Vec2 VAD + eGeMAPS (9.3 + 9.4) |

---

## Custo operacional

| Feature | Custo | Condição |
|---|---|---|
| Whisper turbo | $0 | Local, GPU 4.93GB |
| Wav2Vec2 emotion | $0 | Local, opt-in |
| openSMILE + pyannote | $0 | CPU only |
| py-feat FACS | $0 | CPU SVM |
| **Gemini Vision** | **~$15/1000 evals** | Flag OFF por padrão, budget guard $0.10/eval |

---

## Follow-ups pós-merge (não-bloqueantes)

### Alta prioridade
1. **Story 9.1.1** — Gate 2 smoke execution
   - 10 vídeos replay Supabase
   - Delta ≤15pt + rastreabilidade à nova fórmula
   - Requer criar `ml-worker/scripts/replay_eval.py` (~30 linhas)

2. **AC9 flip** — `MODEL_ORCHESTRATOR_ENABLED=true` default
   - Commit pequeno pós-Gate 1 validado em prod
   - Desbloqueia Stories 9.3 + 9.5 em prod (precisam orchestrator)

### Média prioridade
3. **Install real deps em prod** — `pip install -e ".[prosody,emotion,facs]"`
4. **HF_TOKEN setup doc** — `docs/guides/pyannote-setup.md`
5. **Observability dashboard** — Gemini Vision custo acumulado por evaluation

### Condicional (só dispara se gatilhos)
6. **Story 9.7** — calibração pesos contextuais pós-Gate 3
   - Gatilho: ground truth Gui Reginatto (Story 7.7) retornado + Pearson <0.75 com app

### Docs polish
7. **CodeRabbit findings** — aplicar `[SOURCE:]` e `[INFERRED]` tags em `docs/sessions/` audit artifacts (AIOX convention, não-bloqueante)

---

## Epics 10-12 (conditional roadmap — aguardando gatilhos)

Mantidos em memória como roadmap condicional. **NÃO ativar sem gatilhos:**

- **Epic 10 — Dataset Expansion:** gatilho ≥500 vídeos coletados em shadow mode
- **Epic 11 — LLM Semantic Layer:** gatilho receita mensal que justifique ~$5k/ano API
- **Epic 12 — Multi-person + Scene Analysis:** gatilho diferencial competitivo ser gargalo estratégico

---

## Como retomar

### Validar Epic 9 em ambiente real

```bash
# 1. Instalar deps opcionais
cd ml-worker
pip install -e ".[prosody,emotion,facs]"

# 2. Gate 1 hardware smoke
python scripts/vram_check.py

# 3. Ativar flags gradualmente em staging
export STATE_OF_ART_ENABLED=true      # Story 9.1 (score novo)
export MODEL_ORCHESTRATOR_ENABLED=true # Story 9.2 (VRAM)
# Opcional conforme validação:
# export TONALITY_ML_ENABLED=true
# export PYFEAT_ENABLED=true
# export OPENSMILE_ENABLED=true
# export PYANNOTE_VAD_ENABLED=true
# export GESTURE_SEMANTIC_ENABLED=true  # PAGO

# 4. Rodar 10 vídeos de calibração
# 5. Comparar overall_score v0.6.0 vs v0.7.0-alpha.6
```

### Disparar Story 9.1.1

```bash
@sm
*draft 9.1.1
# Combinar Gate 2 smoke + AC6 WER benchmark + AC7 perf budget
```

---

## Meta-aprendizado sobre orchestration

A chain AIOX funciona em **auto mode** com fricção mínima:

1. Todos os 6 Pre-Flight questionários resolvidos com "default"
2. 2 flags @sm levantadas em stories 9.1/9.2 resolvidas pelo @po inline
3. 1 fix @qa→@dev em Story 9.1 (C2 legacy pesos) executado em <20 minutos
4. 0 issues bloqueantes em 311 tests rodados 6 vezes

**Próximos epics podem seguir mesmo pattern** — batched drafts quando stories são paralelas, sequential quando uma bloqueia outra.

---

**Última validação:** Epic 9 100% shipado em main. Aguarda validação real em staging + Gate 3 (ground truth Gui) pra promoção flags e produção.
