# Sessão 2026-04-17 — Epic 9 End-to-End + Post-Deploy Hotfixes + Coaching Real

**Duração:** ~24h de sessão (começou 2026-04-16 com diagnóstico Vinh, terminou 2026-04-17 com coaching em dados reais)
**Modo:** Auto mode (100% agentes orquestrados)
**Resultado:** Epic 9 "State of the Art" **shipado + validado em produção real** com pipeline honesto end-to-end.

---

## 1. Contexto inicial

Sessão anterior (2026-04-16) terminou com diagnóstico @vinh-giang propondo Epic 9 — "State of the Art":
- 6 stories (9.1–9.6)
- 6 upgrades computacionais
- 7 feature flags
- Backbone ML estado-da-arte

User aprovou escopo completo. Target: `oratoria-avaliador@0.7.0`.

---

## 2. Epic 9 formalização + shipping (PRs #25-#30)

Orchestration chain AIOX completa executou 6 vezes, uma por story:

```
@vinh-giang → @pm *create-epic → @sm *draft → @po *validate
→ @dev *develop (Pre-Flight) → @qa *qa-gate → @devops *push + *merge
```

### 6 stories principais mergeadas em 1 dia

| Wave | PR | Story | Merge | Size |
|---|---|---|---|---|
| 0 | #25 | 9.1 Aggregator refactor + confidence badges | `1faf2fc` | M (~16h solo → 1 turn) |
| 1 | #26 | 9.2 Whisper turbo + VRAM orchestrator | `6feec6d` | L (~20h solo) |
| 2 | #27 | 9.4 openSMILE + pyannote VAD | `0696577` | M (~18h) |
| 2 | #28 | 9.3 Wav2Vec2-Emotion | `905664f` | L (~24h) |
| 3 | #29 | 9.5 py-feat FACS 20 AUs | `8252abf` | L (~32h) |
| 3 | #30 | 9.6 Gemini Vision gesto semântico | `cdc768b` | L (~24h) |

### Decisões arquiteturais aprovadas

1. **Cenário B de pesos** (Story 9.1):
   ```python
   PESOS_DEFAULT = {
       "voice": 0.22, "variety": 0.20, "gesture": 0.18,
       "facial": 0.16, "posture": 0.14, "fillers": 0.10
   }
   ```
2. **SCORING_DIMENSIONS reduz 10→6** (archetypes, tonality, opening, identity, storytelling, temporal, congruence movem pra SECONDARY)
3. **Feature flag master `STATE_OF_ART_ENABLED`** (default false pra rollback)
4. **Todo ML novo entra como augmentation primeiro** — só vira scoring após Gate 3 (ground truth Gui)

### Gate 1 — Hardware Smoke real (RTX 4060)

Executado em `ml-worker/scripts/vram_check.py`:
- whisper_turbo peak: **4.93 GB**
- whisper_medium peak: 4.58 GB
- Peak global: **4.93 GB ≤ 7.5 GB budget** ✅

---

## 3. Follow-ups pós-merge (PRs #31-#33)

| PR | Story | Commit | Fix |
|---|---|---|---|
| #31 | 9.1.1 Gate 2 smoke | `9c6ae5b` | `replay_eval.py` executado em 5 evals reais: **PASS** (max delta 5pt) |
| #32 | 9.1.2 AC9 flip | `283331a` | `MODEL_ORCHESTRATOR_ENABLED=true` default |
| #33 | 9.1.3 Deps validation | `3d8f29d` | Install real revelou: `facebook/wav2vec2-base-superb-er` removido do HF → corrigido pra `superb/...`; py-feat >=0.7 não existe → pin `>=0.6,<0.7` |

### Gate 2 Smoke — 5 evals reais do Supabase

| eval_id | v0.6.0 | v0.7.0 | Δ | facial |
|---|---|---|---|---|
| 775b5f6b | 59 | 54 | **-5** | 40 |
| 8f53044c | 59 | 54 | **-5** | 40 |
| 113cb6a4 | 60 | 57 | **-3** | 40 |
| 494693f0 | 60 | 57 | **-3** | 40 |
| 18699d04 | 58 | 62 | **+4** | 75 |

**Verdict: PASS** — direção correlaciona com facial_score (facial alto sobe, baixo desce).

---

## 4. Descobertas técnicas salvas em memória

`memory/feedback_epic9_deps_descobertas.md`:

1. **`facebook/wav2vec2-base-superb-er` foi removido do HuggingFace** — usar `superb/wav2vec2-base-superb-er` (39k+ downloads)
2. **py-feat max PyPI version é 0.6.2** — nunca existiu >=0.7
3. **py-feat 0.6.x bloqueado Python 3.12** — `pkgutil.ImpImporter` removido upstream
4. **Wav2Vec2 carrega em CPU por default** — precisa `.to("cuda")` pra GPU path

Princípio documentado: **"Gate 0.5 — install validation"** antes de Gate 1 pra validar deps reais.

---

## 5. Teste real pós-deploy — Cascata de 4 ciclos de hotfix

Depois de shipado, user tentou subir vídeo real e descobriu bugs que Gate 2 smoke (replay sintético) não pegou.

### Ciclo 1 — Eval `0b7a7fb8` (tudo errado)

Pipeline completou mas report nonsense (score 45). Diagnóstico @vinh-giang identificou 3 bugs:

- **B1 CRITICAL** `voice_analyzer` INSERT NULL em `transcriptions.model` (regression do próprio Epic 9)
- **B2 HIGH** `librosa` não instalado (dep transitiva do Wav2Vec2)
- **B3 HIGH** Schema Supabase sem 5 colunas Epic 9 (Supabase drop silent via `extra=allow`)

**Fix:** commit `c09386d` + migration 013 aplicada em prod via `supabase db push`.

### Ciclo 2 — Eval `be8bfdfa` (5 cards em vez de 6)

User: "não era pra aparecer 6 scores globais?". Auditoria revelou gap do Epic 9:

- **B4 CRITICAL** `report_generator.py` prompt hardcoded 5 dims (sem facial) → Gemini não gera feedback facial
- **B5 HIGH** Frontend `DIMENSION_LABELS` sem `facial: "Expressão Facial"` → card sumia
- **N2 HIGH** `variety` falsely skipped — `_upstream_failed` só aceitava dict, voice retorna `WorkerSuccess` pydantic
- **N1+N4 HIGH** Save layer em `app.py::aggregated_metrics insert` ignorava 5 campos Epic 9

**Fix:** commit `b091c53`.

### Ciclo 3 — Eval `35d8196f` (6 cards OK!)

User confirmou "TUDO VERDE — 6 scores". Mas 2 issues sutis persistiam:

- **N5 HIGH** Identity card mostrava "/100" vazio — `data.score` undefined porque `WorkerSuccess` separa score de metrics, aggregator preservava separação, UI lia só metrics
- **N6 MEDIUM** `storytelling` saía `{}` vazio — overrides redundantes em app.py sobrescreviam dados do aggregator com dict incompleto
- **N7 MEDIUM** `analysis_results` só salvava 7/13 dims (secondary não eram persistidas)

**Fix:** commit `ee6e0bb`.

### Ciclo 4 — Eval `8534ca9e` (Postgres CHECK constraint)

User: "veja se rodou tudo". Auditoria revelou que N7 tinha root cause adicional:

- **Postgres CHECK constraint** `analysis_results_dimension_check` só permitia 7 dims antigas
- Secondary dims (facial, tonality, opening, storytelling, temporal, congruence) violavam INSERT
- `_save_analysis` silent warn + skip

**Fix:** migration 014 aplicada em prod + backfill manual do eval atual.

---

## 6. Merge trail final — 12 commits Epic 9 em main

```
ef4496a fix(db): migration 014 — expand dimension CHECK (14 dims)
ee6e0bb fix(epic-9): N5+N6+N7 — identity score + storytelling + secondary save
b091c53 fix(epic-9): B4+B5+N2+N1/N4 — facial card + variety + save layer
c09386d fix(ml-worker): hotfix B1+B2+B3 — voice NULL + librosa + migration 013
7ccec4a fix(web): crypto.randomUUID fallback pra non-secure context
3d8f29d fix(ml-worker): Story 9.1.3 — MODEL_ID fix + py-feat pin + deps validated
283331a feat(ml-worker): AC9 flip — MODEL_ORCHESTRATOR_ENABLED default TRUE
9c6ae5b feat(ml-worker): Story 9.1.1 — Gate 2 smoke EXECUTED, PASS em dados reais
3f7710c docs(sessions): handoff final Epic 9 COMPLETE
cdc768b feat(epic-9): Story 9.6 — Gemini Vision gesture semantic (#30)
8252abf feat(epic-9): Story 9.5 — py-feat FACS 20 AUs + 6 emotions (#29)
905664f feat(ml-worker): Story 9.3 — Wav2Vec2-Emotion ML (#28)
0696577 feat(epic-9): Story 9.4 — openSMILE eGeMAPS + pyannote VAD (#27)
6feec6d feat(epic-9): Story 9.2 — Whisper large-v3-turbo + VRAM orchestrator (#26)
1faf2fc feat(epic-9): Story 9.1 — aggregator refactor + confidence badges (#25)
```

---

## 7. Estado final validado em produção

### Schema DB completo

```
aggregated_metrics:
  + overall_score, dimension_scores, detailed_metrics, incomplete_dimensions
  + partial_aggregation BOOLEAN (migration 013)
  + schema_version TEXT (migration 013)
  + dimension_confidence JSONB (migration 013)
  + contexto TEXT (migration 013)
  + pesos_utilizados JSONB (migration 013)

analysis_results:
  + CHECK constraint agora permite 13 dims + gesture_semantic (migration 014)
```

### Pipeline real validado (eval `8534ca9e`)

| Camada | Status | Evidência |
|---|---|---|
| 13 analyzers rodaram | ✅ | Todas em `detailed_metrics` |
| 6 scoring dims no overall | ✅ | Matemática confere: voice×0.22 + variety×0.20 + gesture×0.18 + facial×0.16 + posture×0.14 + fillers×0.10 |
| partial_aggregation | ✅ | False (todas 6 completaram) |
| schema_version | ✅ | "1.2.0" |
| dimension_confidence | ✅ | 13 keys 🟢🟡🔴 |
| 6 cards na UI | ✅ | Variedade 22, Voz 55, Presença 85, Facial 40, Postura 66, Clareza 22 |
| Identity card | ✅ | "60/100" (antes "/100" vazio) |
| Report Gemini com 6 dims | ✅ | Incluindo seção `expressao_facial` |
| analysis_results | ✅ | 13/13 dims salvas |

### Feature flags ativas em ml-worker prod

```
STATE_OF_ART_ENABLED=true      ✅ (Epic 9 core)
WHISPER_TURBO_ENABLED=true     ✅ (default, com fallback medium)
MODEL_ORCHESTRATOR_ENABLED=true ✅ (AC9 flip)
TONALITY_ML_ENABLED=true       ✅ (Wav2Vec2 ativo)
OPENSMILE_ENABLED=true         ✅ (eGeMAPS 88 features)
PYANNOTE_VAD_ENABLED=true      ✅ (pausa retórica)
PYFEAT_ENABLED=false           ⏭️ (Python 3.12 blocked)
GESTURE_SEMANTIC_ENABLED=false ⏭️ (pago, opt-in)
```

### Deps instaladas em `.venv`

- transformers 5.5.4 ✅
- opensmile 2.6.0 ✅
- pyannote.audio 4.0.4 ✅
- librosa 0.11.0 ✅
- py-feat ❌ (Python 3.12 blocked)

---

## 8. Coaching Vinh em dados reais (eval `8534ca9e`)

User: "sim analise profunda". @vinh-giang executou sessão completa:

### Score final: **50/100**

| Dim | Score | Nota Vinh |
|---|---|---|
| gesture | 85 | 🟢 Forte — zona ideal, 2 mãos, eye contact |
| posture | 66 | 🟢 Aberta 100%, ombros nivelados |
| voice | 55 | 🟡 Alcance rico (21.6 semitons) mas subutilizado |
| archetypes | 45 | 🔴 **Lock-in AMIGO 100%** (1 dim só) |
| facial | 40 | 🔴 Smile 6.7%, brow 0/min |
| variety | 22 | 🔴 Monotonia 75% tempo, cv_volume 0.0099 |
| fillers | 22 | 🔴 6.7/min (meta <3) |

### Diagnóstico central (80/20)

Default primário: **Lock-in Amigo + monotonia + rosto apático**. Discurso sobre internet (tema Educador) entregue em tom Amigo casual, sem variedade, com rosto neutro. Audiência recebe sinal misto.

### Plano 12 semanas assinalado

- **Sem 1-2:** Verbal Highlighter (pausa retórica — 0 hoje, meta 3/min)
- **Sem 3-4:** Volume contrast (peaks and troughs down)
- **Sem 5-6:** Eliminar muletas (ai/então/né/sabe)
- **Sem 7-8:** Arquétipo Educador
- **Sem 9-10:** Smile + brow
- **Sem 11-12:** Integração

### Projeção

Score 50 → **75+** após 12 semanas (variety 22→50+, fillers 22→70+, facial 40→70+).

---

## 9. Lições aprendidas — salvar em memory/feedback

### Pattern que funcionou (orquestração AIOX auto mode)

- 100% dos Pre-Flight respondidos com "default" (defaults razoáveis)
- Feature flags default OFF permitiu rollback instantâneo em 4 ciclos de hotfix
- `replay_eval.py` pra testar fórmula sem re-processar vídeos = game-changer
- Migrations aplicadas via `supabase db push` funcionou depois de link correto

### Gaps descobertos

- **Gate 2 smoke sintético NÃO PEGOU bugs reais** — replay de evals antigas não testa path completo (transcriptions insert, dispatcher, report prompt, frontend labels)
- **CHECK constraints do Postgres NÃO estavam documentados** — story 9.1 não previu
- **Overrides redundantes em app.py** acumularam tech debt silencioso (Story 7.3/7.4/7.5 each added a block)

### Princípio novo

> **"Gate 0.5 — Install Validation"** antes de Gate 1: rodar `pip install -e .[all]` em CI com Python da versão prod + smoke de model_id existence check no HF API + schema diff vs Supabase constraints.

### Princípio Vinh — a sessão fechou o loop inteiro

> "A aquisição de conhecimento traz satisfação. A aplicação traz realização."

Epic 9 aprovado em 1 dia. Mas só **15 horas depois** (teste real + 4 ciclos de hotfix), o pipeline entregou coaching honesto num vídeo real. **A diferença entre shipou e funciona é sempre maior do que parece.**

---

## 10. Próximos passos (conditional roadmap)

### Imediato (próxima sessão)

1. User gravar vídeo **seguindo plano Vinh Sem 1-2** (3 pausas retóricas)
2. Rodar através do pipeline novamente
3. Comparar scores: variety, fillers, archetypes esperam subir

### Follow-ups pendentes

1. **Storytelling vazio em vídeos curtos** — threshold <30 palavras retorna disponivel=false OK, mas vídeos 100-200 palavras às vezes retornam dict vazio sem warn explícito. Investigar.
2. **Identity MINIMUM_MARKERS=3** — threshold pode ser muito alto pra vídeos 1min. User vê "dados_insuficientes" mesmo com 1 marcador. Discutir com @po ajustar pra 2 ou mostrar score + disclaimer.
3. **Wav2Vec2 em CPU** — `load_wav2vec2_emotion` não chama `.to("cuda")`. 75s load time. GPU migration pra perf.
4. **Gate 3 (ground truth Gui Reginatto)** — story 7.7. Quando Gui devolver rubric dos 10 vídeos blindados, rodar correlação Pearson com app scores.
5. **Story 9.7 condicional** — calibração pesos contextuais se Gate 3 mostrar desvio sistemático por contexto.

### Epics 10-12 (conditional — documentados em memória)

- **Epic 10** Dataset Expansion (gatilho: ≥500 evals shadow)
- **Epic 11** LLM Semantic Layer (gatilho: receita justifica ~$5k/ano API)
- **Epic 12** Multi-person Audience Analysis (pós 10+11)

---

## 11. Artefatos criados

### Código (main)
- `ml-worker/contracts/dimensions.py` — SCORING/SECONDARY/AUGMENTATION topology
- `ml-worker/workers/aggregator.py` — flag-aware com 6 pesos
- `ml-worker/workers/_model_loader.py` — `ModelGPU` context manager
- `ml-worker/workers/_emotion_ml.py` — Wav2Vec2 factory
- `ml-worker/workers/_prosody_extras.py` — openSMILE + pyannote
- `ml-worker/workers/_facs_ml.py` — py-feat FACS (stub-ready)
- `ml-worker/workers/_frame_sampler.py` — Gemini Vision frames
- `ml-worker/workers/gesture_semantic_analyzer.py` — LLM gesture
- `ml-worker/workers/report_generator.py` — prompt com facial section
- `ml-worker/scripts/vram_check.py` — Gate 1 hardware
- `ml-worker/scripts/wer_benchmark.py` — AC6 WER
- `ml-worker/scripts/replay_eval.py` — Gate 2 smoke
- `apps/web/src/components/confidence-badge.tsx` — UI badge
- `apps/web/src/app/report/[id]/page.tsx` — 6 dims rendering

### Docs
- `docs/stories/9.0.epic-state-of-the-art.md` — Epic doc formalizado
- `docs/stories/9.1.*` através `docs/stories/9.6.*` — 6 stories + 9.1.1, 9.1.2, 9.1.3
- `docs/stories/EPIC-9.0-EXECUTION.yaml` — wave plan
- `docs/qa/gates/9.1-*.yml` + `9.2-*.yml` — QA gates
- `docs/qa/gate2-story91-smoke.md` + `gate2-story91-results.md` — Gate 2 protocol + results
- `docs/qa/gate1-story92-post-deps-install.md` — Gate 1 pós-install
- `docs/qa/coderabbit-reports/9.1-*.md` + `9.2-*.md` — CodeRabbit summaries
- `docs/sessions/2026-04/handoff-epic9-complete-2026-04-17.md` — mid-session handoff
- `docs/sessions/2026-04/epic9-plan-vs-reality-2026-04-17.md` — verificação plano
- `docs/sessions/2026-04/handoff-2026-04-17-epic9-post-deploy-complete.md` — **este handoff**

### Migrations
- `supabase/migrations/013_epic9_state_of_art_columns.sql` — 5 colunas novas
- `supabase/migrations/014_expand_dimension_check.sql` — CHECK constraint 14 dims

### CHANGELOG
- `squads/oratoria-avaliador/CHANGELOG.md` — v0.7.0-alpha.1 até alpha.8

### Memory
- `memory/epic9_approved_conditional_roadmap.md` — 9 PRs + gatilhos 10-12
- `memory/sessao_2026_04_17_epic9_completo.md` — session artifact
- `memory/feedback_epic9_deps_descobertas.md` — 4 gotchas técnicos

---

## 12. Métricas da sessão

| Métrica | Valor |
|---|---|
| **Duração total** | ~24h (2026-04-16 21:00 → 2026-04-17 21:00+) |
| **PRs mergeados** | **12** (#25 até #33 + 3 hotfixes diretos em main) |
| **Commits em main** | ~15 atômicos |
| **Tests** | **311/311 PASS** ml-worker regression |
| **Dimensions ativas** | 14 (6 scoring + 8 secondary) |
| **Feature flags** | 7 independentes |
| **Optional deps groups** | 3 (`prosody`, `emotion`, `facs`) |
| **Migrations aplicadas em prod** | 2 (013, 014) |
| **Bugs descobertos em teste real** | 4 ciclos × 2-4 bugs = ~11 bugs corrigidos pós-ship |
| **Gate 1 real** | ✅ PASS (RTX 4060 peak 4.93GB) |
| **Gate 2 smoke** | ✅ PASS (5 evals, max delta 5pt) |
| **Gate 3 ground truth** | ⏳ aguarda Gui Reginatto |
| **Custo prod** | **$0** (todas flags pagas OFF) |
| **Primeiro vídeo com coaching honesto** | eval `8534ca9e-6c0a-47e9-9457-d0f30971c528` |

---

## 13. Como retomar

### Validar estado atual
```bash
# ml-worker rodando?
curl -s http://localhost:7860/health

# web rodando?
curl -s http://localhost:3000

# Último eval processado?
cd ml-worker && .venv/bin/python -c "
from supabase import create_client
import config
c = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
r = c.table('evaluations').select('id,status').order('created_at', desc=True).limit(1).execute()
print(r.data[0])
"
```

### Novo teste de coaching
1. Seguir plano Vinh Sem 1-2 (3 pausas retóricas)
2. Gravar novo vídeo
3. Upload via http://172.23.196.94:3000
4. Analisar report com `@vinh-giang *coach`

### Se quiser trabalhar em Gate 3
1. Contatar Gui Reginatto
2. Entregar 10 vídeos blindados
3. Receber rubric 11-dim preenchido
4. Rodar `replay_eval.py` com correlação Pearson
5. Se ≥0.75: promover tonality/facial de SECONDARY → SCORING

### Se quiser disparar Epics 10-12
Verificar gatilhos documentados em `memory/epic9_approved_conditional_roadmap.md`.

---

**Handoff gerado por:** `@dev` (Dex) em 2026-04-17
**Status da sessão:** FECHADA
**Branch atual:** `main` em sync com `origin/main`
**Commit HEAD:** `ef4496a` (ou posterior se houver)
**Próxima ativação sugerida:** `@vinh-giang *coach` após user gravar novo vídeo com plano Sem 1-2 aplicado
