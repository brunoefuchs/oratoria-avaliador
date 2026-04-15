# 🎤 Oratória Avaliador — Meta-Squad de Governança

> **Status:** v0.5.1 — ml-worker bridge pronta (Epic 1-4 + 6 delivered; Epic 5 deferred)
> **Schema contract:** v1.1.0 (aditivo; v1.0.0 ainda suportado)
> **Integração ml-worker:** `tasks/process_evaluation.py` — ver `INTEGRATION.md`
> **PRD canônico:** [`docs/projects/oratoria-avaliador/prd.md`](../../docs/projects/oratoria-avaliador/prd.md)

## O que este squad é

Um **meta-squad de governança** para o produto Oratória Avaliador. Não executa ML nem escreve narrativa do zero — **orquestra** especialistas técnicos + mentores clonados (vinh-giang, gui-reginatto) + workers ML existentes e **bloqueia** outputs que violam regras de coerência, completude ou fidelidade à metodologia dos mentores.

A inteligência do produto está na orquestração, não na captura.

## O que este squad NÃO é

- Não é um squad de ML workers (quem extrai features é `ml-worker/`)
- Não é um mentor novo (vinh-giang/gui-reginatto já existem no `squad-creator-pro`)
- Não é um squad de UI (`apps/web/` já tem esqueleto)
- Não é um squad de data engineering (schema Supabase é owned pelo `@data-engineer`)

## Estado atual (Epic 1)

| Artefato | Status |
|----------|--------|
| `oratoria-avaliador-chief` (orchestrator) | ✅ Epic 1 |
| `features_canonical.schema.json` (contract v1.0.0) | ✅ Epic 1 |
| `ml_worker_adapter.py` (legado → canonical) | ✅ Epic 1 |
| `validate_contract.py` (G1 gate) | ✅ Epic 1 |
| `scoring-engine` + `tasks/scoring_engine.py` | ✅ Epic 2 |
| `congruence-auditor` + `tasks/congruence_auditor.py` (G3 gate) | ✅ Epic 2 |
| `speech-prosody-expert` (lean reference) | ✅ Epic 2 |
| `face-gesture-expert` (lean reference) | ✅ Epic 2 |
| `narrative-structure-expert` (lean reference) | ✅ Epic 2 |
| `mentor-router` + `tasks/mentor_router.py` | ✅ Epic 3 |
| `hierarchy-ranker` + `tasks/hierarchy_ranker.py` (G5 gate) | ✅ Epic 3 |
| `exercise-prescriber` + `tasks/exercise_prescriber.py` (G6 gate) | ✅ Epic 3 |
| `mentor-narrator` + `tasks/mentor_narrator.py` (template+LLM prompt, G4 gate) | ✅ Epic 3 |
| `tasks/fidelity_checker.py` (G4 measurement) | ✅ Epic 3 |
| `quality-gate-keeper` + `tasks/quality_gate_keeper.py` (G_FINAL) | ✅ Epic 4 |
| `calibration-keeper` + `tasks/calibration_keeper.py` (G7 gate) | ✅ Epic 4 |
| `tasks/audit_outlier.py` + `wf-audit-outlier.yaml` | ✅ Epic 4 |
| `tasks/dashboard_generator.py` | ✅ Epic 4 |
| `tasks/pipeline_end_to_end.py` (runner das 6 fases) | ✅ Epic 4 |
| `wf-evaluate-pipeline` (phases 1-6 COMPLETE) | ✅ Epic 4 |
| `wf-calibrate-weights.yaml` (human-in-loop) | ✅ Epic 4 |
| `tasks/evolve_dimension.py` (playbook runner) | ✅ Epic 6 |
| `wf-evolve-dimension.yaml` (7 fases) | ✅ Epic 6 |
| Schema v1.1.0 com tonality (additive; v1.0.0 backward compat) | ✅ Epic 6 |
| Tonality scorer + exercises gui/vinh | ✅ Epic 6 |
| `tasks/process_evaluation.py` (entrypoint ml-worker) | ✅ v0.5.1 |
| `INTEGRATION.md` (guia de integração) | ✅ v0.5.1 |
| 54 smoke tests total (3+3+8+11+14+10+5 integration) | ✅ PASS |
| `psychometry-calibrator` | ⏳ Epic 2b (deferred; dataset ≥500) |
| LLM call integration real | ⏳ Epic 3b |
| B2B team aggregation | ⏳ Epic 5 (not_before: 100+ avaliações em prod) |

### 🎯 Milestone: Pipeline end-to-end COMPLETO

Com Epic 4 concluído, o squad tem **pipeline integral** de features brutas a
release decision:

```
features_canonical (v1.0.0)
  → G1 contract validity
  → scoring + pesos contextuais
  → G3 congruence check
  → hierarchy ranking (G5)
  → mentor routing + narrative (G4) + exercises (G6)
  → G_FINAL → RELEASE or FAIL → wf-audit-outlier
```

Cada mudança de peso/threshold passa por `wf-calibrate-weights` (human-in-loop)
e grava precedent imutável via calibration-keeper (G7).

### Rodar smoke tests

```bash
# Epic 1: Validar fixtures contra contract (G1)
python3 squads/oratoria-avaliador/tasks/validate_contract.py \
  squads/oratoria-avaliador/data/fixtures/features_valid_v1.json

# Epic 1: Adapter (ml-worker legado → canonical)
python3 squads/oratoria-avaliador/tasks/test_adapter.py

# Epic 2: Scoring + Congruence (8 testes)
python3 squads/oratoria-avaliador/tasks/test_scoring_congruence.py

# Epic 3: Mentor Narrative (11 testes)
python3 squads/oratoria-avaliador/tasks/test_epic_3.py

# Epic 4: Quality Gate + Calibration + End-to-end (14 testes)
python3 squads/oratoria-avaliador/tasks/test_epic_4.py

# Epic 6: Evolve Dimension playbook + tonality integration (10 testes)
python3 squads/oratoria-avaliador/tasks/test_epic_6.py
```

### Rodar pipeline end-to-end

```python
from pipeline_end_to_end import run_pipeline
import json

with open("squads/oratoria-avaliador/data/fixtures/features_valid_v1.json") as f:
    features = json.load(f)

result = run_pipeline(
    features,
    evaluation_context={"motivacao": ["vender_mais"]},
)

decision = result["gate_decision"]
print(decision["verdict"], decision["release_to_user"])
# PASS True

print(result["artifacts"]["narrative"])  # relatório na voz do gui-reginatto
```

## Ativação

```
@oratoria-avaliador-chief
```

Comandos disponíveis:
- `*evaluate {video_id}` — rodar pipeline de avaliação (stub em Epic 1)
- `*status` — ver estado do pipeline
- `*help` — lista comandos

## Arquitetura

```
ml-worker/workers/*  →  features_canonical.json  →  chief
                                                     ↓
                                            [Epic 2: scoring + congruence]
                                                     ↓
                                            [Epic 3: mentor narrative]
                                                     ↓
                                            [Epic 4: quality gate]
                                                     ↓
                                            evaluation_report.json → usuário
```

## Contract: `features_canonical.json`

Ver `data/features_canonical.schema.json`. Qualquer ML worker novo precisa emitir output compatível com esse schema para entrar no pipeline.

**Breaking change no contract = breaking change em todo pipeline.** Versionar estritamente.

## Roadmap

| Epic | Goal | Not Before |
|------|------|------------|
| 1 | Foundation + Contract | Inventário ml-worker ✅ |
| 2 | Scoring + Congruence | Epic 1 + questionário 6.Q live |
| 3 | Mentor Narrative | Epic 2 + DNA vinh/gui validado (já PASS) |
| 4 | Quality Gate + Calibration | Epic 3 |
| 5 | B2B Team Aggregation | Epic 4 + 100+ avaliações G-PASS |
| 6 | Evolve Dimensions | Epic 4 |

## Referências

- **PRD:** `docs/projects/oratoria-avaliador/prd.md`
- **Planning Summary:** `docs/projects/oratoria-avaliador/planning-summary.yaml`
- **Epic 6 spec (produto):** `docs/architecture/epic-6-architectural-spec.md`
- **Mentor DNA (externa):**
  - `squads/squad-creator-pro/minds/vinh_giang/`
  - `squads/squad-creator-pro/minds/gui_reginatto/`
- **ML workers (externa):** `ml-worker/workers/`
