# Squad Validators

Validadores auditáveis portados do Stage e adaptados ao layout do Hub.

## Invocações determinísticas

```bash
node infrastructure/scripts/squads/validate_workflow_contract_single.cjs --file squads/squad-creator-pro/workflows/wf-create-squad.yaml --json
node infrastructure/scripts/squads/validate_workflow_contract_single.cjs --file infrastructure/scripts/squads/fixtures/valid-workflow.yaml --json
node infrastructure/scripts/squads/validate_workflow_contract_single.cjs --file infrastructure/scripts/squads/fixtures/invalid-workflow.yaml --json
node infrastructure/scripts/squads/check_doc_drift.cjs --squad movement --json
node infrastructure/scripts/squads/check_doc_drift.cjs --squad infra-doc-drift-pass --json
node infrastructure/scripts/squads/check_doc_drift.cjs --squad infra-doc-drift-fail --json
node infrastructure/scripts/squads/capture_repo_global_quality_baseline.cjs
node infrastructure/scripts/squads/validate_squad_runtime_ssot.cjs --json
node infrastructure/scripts/squads/validate_squad_runtime_ssot.cjs --fixture infrastructure/scripts/squads/fixtures/runtime-ssot-pass.json --json
node infrastructure/scripts/squads/validate_squad_runtime_ssot.cjs --fixture infrastructure/scripts/squads/fixtures/runtime-ssot-fail.json --json
```

## Scripts

- `workflow_cross_squad_contract.cjs`: resolve agentes cross-squad e valida bridges locais.
- `validate_workflow_contract_single.cjs`: roda `WorkflowValidator` do `.aiox-core` em um workflow específico e agrega o contrato cross-squad.
- `check_doc_drift.cjs`: compara contagens documentadas de um squad com a árvore real do squad.
- `capture_repo_global_quality_baseline.cjs`: serializa o baseline dos gates globais do root (`lint`, `typecheck`, `test`).
- `validate_squad_runtime_ssot.cjs`: protege `squad-creator*` contra artefatos legados de runtime/state e aceita fixtures controladas.

## Fixtures

- `fixtures/valid-workflow.yaml` / `fixtures/invalid-workflow.yaml`
- `fixtures/runtime-ssot-pass.json` / `fixtures/runtime-ssot-fail.json`
- `squads/infra-doc-drift-pass/` / `squads/infra-doc-drift-fail/`
