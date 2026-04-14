# Runner-lib Tests

Suíte de integração shell para a runner-lib. Todos os testes rodam sem chamadas reais a LLM.

## Como rodar

```bash
bash infrastructure/scripts/runner-lib/tests/run-tests.sh
```

Para rodar uma suíte específica:

```bash
bash infrastructure/scripts/runner-lib/tests/run-tests.sh runtime
bash infrastructure/scripts/runner-lib/tests/run-tests.sh test-replan.sh
```

## O que a suíte cobre

- `test-runtime.sh`: `detect_runtime()` e `run_llm_prompt()` com runtime mockado.
- `test-state-manager.sh`: criação, atualização e validação do state file.
- `test-metrics.sh`: JSONL de métricas, cost cap e custo acumulado.
- `test-session-mgr.sh`: lifecycle e arquivamento de sessões.
- `test-arg-parser.sh`: flags comuns dos runners.
- `test-replan.sh`: bridge `run_llm_prompt_with_replan()` e estratégias de recovery.
- `test-guards.sh`: guards de budget, circuit breaker, truncate e output filter.
- `test-evaluator.sh`: bypass, Tier 1 only, verdict JSON e retry limiter.
- `test-validate-runner.sh`: contrato de `validate-runner.sh` para smoke test ausente, falhando e passando.

## Estado atual da suíte

- Integração: 9 testes `test-*.sh`
- Smoke: 8 runners registrados
- Execução consolidada: `npm test` → `17 passed, 0 failed, 0 skipped` no estado atual do Epic 101

## Padrão de teste

- Cada `test-*.sh` deve ser autocontido e retornar `0` para PASS ou `1` para FAIL.
- Use `mktemp -d` para isolar arquivos temporários.
- Faça mock de `_exec_runtime()` ou `run_llm_prompt()` dentro do próprio arquivo de teste.
- Nenhum teste deve depender de CLIs reais (`claude`, `codex`, `gemini`).

## Adding New Tests

1. Crie um novo arquivo `test-<modulo>.sh` neste diretório.
2. Inicialize um diretório temporário com `mktemp -d` e limpe com `trap`.
3. Sourceie apenas os módulos necessários da runner-lib.
4. Mocke chamadas externas no próprio teste.
5. Garanta output legível com assertions simples e exit code `0/1`.

Para smoke tests de runners completos, use `SMOKE_TEST=true` no bootstrap. Isso mantém a separação entre:

- testes de integração da runner-lib;
- smoke tests de runners consumidores.

## Adding tests for new runners

Cada runner novo **DEVE** nascer com um smoke test. O SOP `squads/runner-ops/tasks/create-runner.md` (Phase 5) automatiza essa geração.

### Passo a passo manual

1. Copie o template:

```bash
cp infrastructure/scripts/runner-lib/tests/templates/test-runner-template.sh \
   infrastructure/scripts/runner-lib/tests/smoke/test-{runner-id}.sh
chmod +x infrastructure/scripts/runner-lib/tests/smoke/test-{runner-id}.sh
```

2. Configure as 4 variáveis no topo do arquivo gerado:

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `RUNNER_ID` | ID do runner no registry | `mmos` |
| `RUNNER_PATH` | Caminho relativo ao repo | `squads/mmos/scripts/mmos.sh` |
| `RUNNER_SQUAD` | Squad dono do runner | `mmos` |
| `FIXTURE_DIR` | Dir de fixtures (pode estar vazio) | `infrastructure/scripts/runner-lib/tests/smoke/fixtures/mmos` |

3. Crie o diretório de fixtures:

```bash
mkdir -p infrastructure/scripts/runner-lib/tests/smoke/fixtures/{runner-id}
```

4. Se o runner tem args não-padrão (validators, `--source`, project dir), customize a função `build_runner_args()` no teste gerado. O template inclui exemplos comentados.

5. Registre o runner em `infrastructure/scripts/runner-lib/runner-registry.yaml`. O smoke suite (`run-smoke-tests.sh`) lê do registry para rodar todos os testes.

6. Rode o teste individual:

```bash
bash infrastructure/scripts/runner-lib/tests/smoke/test-{runner-id}.sh
```

### Os 7 checks do smoke

| # | Check | O que valida |
|---|-------|-------------|
| 1 | `init` | Script existe e tem shebang |
| 2 | `state` | Cria state file ou indica inicialização |
| 3 | `session` | Produz indicadores de sessão/lifecycle |
| 4 | `banner` | Imprime header/banner reconhecível |
| 5 | `phase-start` | Inicia ao menos uma fase |
| 6 | `metrics` | Produz saída de métricas |
| 7 | `exit-code` | Sai com código limpo (0 para pipelines, <=1 para validators) |

### validate-runner.sh integration

O `validate-runner.sh` (Story 101.8) verifica automaticamente se o smoke test existe:

- **WARNING** se `tests/smoke/test-{runner-id}.sh` não existe (não bloqueia runners legados)
- **ERROR** se o smoke test existe mas falha ao rodar

Story: 101.16
