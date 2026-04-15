# Upgrade Plan — Squad Oratória Avaliador v0.5.1 → v0.6.0

**Data:** 2026-04-15
**Command:** `*upgrade-squad oratoria-avaliador --mode=plan --focus=all`
**Input:** `validation-report-2026-04-15.md` (PASS com CONCERNS, score 8.5/10)
**Objetivo:** Fechar 2 BLOCKING + 3 MAJOR + 2 MINOR gaps identificados; elevar Operational Excellence de 6/10 → 9/10.

---

## 1. Inventário (factual)

| Categoria | Count | Estado |
|---|---|---|
| Agents `.md` | 12 | Todos presentes, 3 são technical-reference |
| Tasks `.py` (production) | 16 | 0 com `logging`, 3 com `try/except`, 15 com return type |
| Tests `.py` | 6 | 54 smoke tests PASS standalone (`python3 tasks/test_*.py`) |
| Workflows `.yaml` | 4 | Todos `implemented` |
| Data contracts | 1 schema + 4 fixtures | v1.0.0 + v1.1.0 backward compat |
| Test coverage | 100% | 16/16 tasks testadas |
| Cross-refs | 100% | config.yaml ↔ filesystem sem orfandade |
| Baseline suite run | `test_integration.py` → 5/5 PASS | ✅ |

---

## 2. Gap Report (dual-track)

### 2a. Structural gaps (inherited baseline)
Nenhum — estrutura do squad está 100% íntegra (cross-refs, tipos, arquivos).

### 2b. Qualitative gaps (pro overlay)

| ID | Categoria | Severidade | Arquivos | Fix complexity |
|---|---|---|---|---|
| **B1** | Observability | BLOCKING | 16 tasks (zero `import logging`) | Low-Medium |
| **B2** | Error handling | BLOCKING | 5 tasks críticos (sem try/except) | Medium |
| M1 | Doc contract (I/O) | MAJOR | 6 agents `.md` | Low |
| M2 | Type hint | MAJOR | `pipeline_end_to_end.py:33` | Trivial |
| M3 | Epic traceability | MAJOR | `wf-evaluate-pipeline.yaml` | Trivial |
| MIN1 | Metadata | MINOR | 3 reference agents sem `epic_source` em config | Trivial |
| MIN2 | Docstring | MINOR | `fidelity_checker.py` sem `:return:` | Trivial |

**Esforço total estimado:** ~2h30.

---

## 3. Plano de Execução

Dividido em **2 PRs independentes** para separar risco:

### PR A — `chore(observability): add logging + error handling to oratoria-avaliador tasks`

Fecha **B1 + B2** (BLOCKING). Altera comportamento runtime → requer testes.

**Escopo:**
- Adicionar `import logging` + `logger = logging.getLogger(__name__)` em todos os 16 tasks production
- Substituir `print()` existentes (se houver) por `logger.info/warning/error`
- Adicionar try/except nos 5 tasks críticos identificados:
  - `audit_outlier.py`
  - `calibration_keeper.py`
  - `congruence_auditor.py`
  - `quality_gate_keeper.py`
  - `scoring_engine.py`
- Pattern de error handling (para tasks que retornam dict):
  ```python
  def task_fn(...) -> dict[str, Any]:
      try:
          # main logic
          logger.info("task_started", extra={"evaluation_id": eid})
          result = compute(...)
          logger.info("task_completed", extra={"verdict": result["verdict"]})
          return result
      except (KeyError, TypeError, ValueError) as e:
          logger.error("task_failed", exc_info=True, extra={"evaluation_id": eid})
          return {
              "verdict": "INCOMPLETE",
              "error": {"type": type(e).__name__, "msg": str(e)},
          }
  ```
- Para tasks que **lançam** exceções (vs retornar dict de erro): manter `raise` mas logar antes:
  ```python
  except ValueError as e:
      logger.error("contract_violation", exc_info=True)
      raise
  ```

**Exclusões (decisão consciente):**
- NÃO mudar assinaturas públicas (contratos)
- NÃO adicionar logging dentro de loops tight (só em entry/exit + branches)
- NÃO swallowar exceções que eram `raise` — só logar antes de re-raise

**Verification:**
```bash
# 1. Todos os 6 test files passam sem regressão
for t in squads/oratoria-avaliador/tasks/test_*.py; do
  echo "=== $t ==="
  python3 "$t" || exit 1
done

# 2. Smoke: rodar o pipeline end-to-end com fixture válida
python3 squads/oratoria-avaliador/tasks/test_integration.py

# 3. Grep de sanity — todos os 16 tasks têm logging
ls squads/oratoria-avaliador/tasks/*.py | grep -v test_ | grep -v __pycache__ | \
  xargs grep -L "^import logging" | wc -l  # deve retornar 0
```

**Acceptance criteria:**
- [ ] 16/16 production tasks com `import logging`
- [ ] 5/5 tasks críticos com try/except estruturado
- [ ] `python3 tasks/test_integration.py` → 5/5 PASS
- [ ] `python3 tasks/test_epic_3.py` → todos PASS
- [ ] `python3 tasks/test_epic_4.py` → todos PASS
- [ ] `python3 tasks/test_epic_6.py` → todos PASS
- [ ] `python3 tasks/test_scoring_congruence.py` → todos PASS
- [ ] `python3 tasks/test_adapter.py` → todos PASS
- [ ] Zero alteração em schemas/fixtures
- [ ] Zero alteração em assinaturas públicas

**Rollback:** `git revert <sha>`. Nenhuma migração de schema ou dado; safe revert.

**Estimate:** ~1h30.

---

### PR B — `chore(docs): close doc gaps + metadata in oratoria-avaliador squad`

Fecha **M1 + M2 + M3 + MIN1 + MIN2**. Só altera docs/metadata → zero risco runtime.

**Escopo:**

**B.1 Adicionar `operational_logic.inputs/outputs` em 6 agents `.md`:**
Template de referência: `squads/oratoria-avaliador/agents/congruence-auditor.md`.

Agents a atualizar:
- `mentor-router.md` — input: scoring_output + user_profile; output: routing_decision (consumers: mentor-narrator, hierarchy-ranker)
- `hierarchy-ranker.md` — input: scoring_output + congruence_report; output: ranked_problems (consumer: exercise-prescriber, mentor-narrator)
- `exercise-prescriber.md` — input: ranked_problems + routing_decision; output: exercise_prescription (consumer: mentor-narrator)
- `mentor-narrator.md` — input: routing + ranked + exercises; output: narrative_text (consumer: quality-gate-keeper)
- `quality-gate-keeper.md` — input: all G1-G6 gate results; output: quality_gate_decision (consumer: release decision)
- `calibration-keeper.md` — input: weight_change_proposal; output: audit_trail_entry (consumer: scoring-engine on next run)

**B.2 Type hint em `pipeline_end_to_end.run_pipeline`:**
```python
# tasks/pipeline_end_to_end.py:33
def run_pipeline(
    features_canonical: dict[str, Any],
    evaluation_context: dict[str, Any] | None = None,
    user_profile: dict[str, Any] | None = None,
    mode: str = "template",
) -> dict[str, Any]:  # ← ADICIONAR
```

**B.3 `epic_source: 2` em `wf-evaluate-pipeline.yaml`** (top-level metadata).

**B.4 Adicionar `epic_source` em config.yaml para 3 reference agents** (ou remover flag se for marker de functional-only).

**B.5 Docstring `:return:` em `fidelity_checker.measure_fidelity`** — 1 seção adicional no docstring.

**Verification:**
```bash
# Tests continuam passando (zero risco, mas sanity)
python3 squads/oratoria-avaliador/tasks/test_integration.py

# Cross-refs ainda íntegros
python3 -c "import yaml; c = yaml.safe_load(open('squads/oratoria-avaliador/config.yaml'))"
```

**Acceptance criteria:**
- [ ] 6 agents com `operational_logic.inputs/outputs`
- [ ] `run_pipeline` com return type hint
- [ ] `wf-evaluate-pipeline.yaml` com `epic_source`
- [ ] 3 reference agents normalizados em config.yaml
- [ ] `fidelity_checker` docstring completo
- [ ] Tests: 5/5 integration PASS

**Rollback:** git revert. Zero risco.

**Estimate:** ~1h.

---

## 4. Ordem de execução e dependências

```
main
  ↓
PR A (observability)   ← BLOCKING fixes, altera runtime
  ↓ (merge)
  ↓
PR B (docs)            ← zero risco, independente
  ↓ (merge)
  ↓
main → squad v0.6.0    ← bump version em config.yaml
```

**Paralelismo:** PR B pode rodar em paralelo com PR A (arquivos disjuntos exceto `config.yaml` se bumpar version — resolver em merge). Para solo dev, sequencial é mais simples.

**Pre-requisito mandatory:**
- Criar tag `backup/pre-upgrade-v0.5.1` antes de abrir PR A
- Rodar baseline `test_integration.py` em main antes de começar PR A

---

## 5. Safe rerun protocol

Cada PR segue o protocolo:

1. **Branch off main limpa**
   ```bash
   git checkout main && git pull
   git checkout -b chore/<scope>
   ```

2. **Snapshot antes**
   ```bash
   python3 squads/oratoria-avaliador/tasks/test_integration.py > /tmp/before.log 2>&1
   ```

3. **Aplicar patches em commits atômicos** (1 commit por file group)

4. **Snapshot depois**
   ```bash
   python3 squads/oratoria-avaliador/tasks/test_integration.py > /tmp/after.log 2>&1
   diff /tmp/before.log /tmp/after.log  # deve diferir apenas em timing ou log lines
   ```

5. **Verificar acceptance criteria** (checklist acima)

6. **Abrir PR com body que linka este plano**

7. **Em caso de falha**
   - Se test falha → analisar, fixar, re-rodar. Não mergear.
   - Se produção shadow mode alerta drift → revert e investigar.

---

## 6. Pós-upgrade verification

Depois que PR A + PR B mergeam em main:

1. **Bump version em `config.yaml`**
   ```yaml
   pack:
     version: "0.6.0"
   metadata:
     version: "0.6.0"
     note: "v0.6.0 — observability + doc cleanup (upgrade de v0.5.1)"
   ```

2. **Setar `tested: true` em config.yaml**
   ```yaml
   entry_agent: oratoria-avaliador-chief
   tested: true  # ← era false
   ```

3. **Adicionar entrada no CHANGELOG**
   ```yaml
   # v0.6.0 (2026-04-15) — Observability + Doc cleanup
   #   - Logging estruturado em todos os 16 tasks
   #   - Error handling (try/except) em 5 tasks críticos
   #   - I/O contracts documentados em 6 agents
   #   - Type hints completos, epic_source normalizados
   #   - Zero mudança em schemas/contracts/assinaturas públicas
   ```

4. **Re-rodar `*validate-squad`** para confirmar score ≥9/10.

5. **Ativar shadow mode em mais evaluations** com confiança de observabilidade.

---

## 7. TODOs e delegações

Nenhuma invenção silenciosa — tudo no plano é rastreável ao validation report.

**Delegações fora de escopo deste upgrade:**
- Epic 3b (LLM real integration em `mentor-narrator`): não endereçado aqui, fica no roadmap
- Epic 5 (B2B aggregation): não endereçado, aguardando ≥100 evals PASS em shadow
- `psychometry-calibrator` (Epic 2b): deferido por falta de dataset ≥500

---

## 8. Próximo passo

**Aguardando aprovação.** Se aprovar:

1. Executo PR A (observability) como primeiro lote — mais impacto, mais risco
2. Valido testes + abro PR no GitHub
3. Você revisa + merge via devops
4. Sigo pro PR B (docs) em sequência
5. Ao final, bump version + `*validate-squad` novamente pra confirmar 9+/10

Quer seguir? Ou ajustar escopo (ex: só PR A primeiro; adiar PR B)?
