# 🎤 Oratória Avaliador — Meta-Squad de Governança

> **Status:** Epic 1 delivered — Foundation + Contract
> **Versão:** 0.1.0
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
| `oratoria-avaliador-chief` (orchestrator) | ✅ Delivered |
| `features_canonical.schema.json` (contract v1.0.0) | ✅ Delivered |
| `wf-evaluate-pipeline` (stub) | ✅ Delivered |
| `ml_worker_adapter.py` (legado → canonical) | ✅ Delivered |
| `validate_contract.py` (G1 gate enforcer) | ✅ Delivered |
| 3 fixtures + 3 smoke tests + 3 adapter tests | ✅ PASS |
| Scoring engine | ⏳ Epic 2 |
| Congruence auditor | ⏳ Epic 2 |
| Mentor narrative | ⏳ Epic 3 |
| Quality gate keeper | ⏳ Epic 4 |
| B2B team aggregation | ⏳ Epic 5 |

### Rodar smoke tests

```bash
# Validar fixtures contra contract
python3 squads/oratoria-avaliador/tasks/validate_contract.py \
  squads/oratoria-avaliador/data/fixtures/features_valid_v1.json

# Testar adapter (ml-worker legado → canonical)
python3 squads/oratoria-avaliador/tasks/test_adapter.py
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
