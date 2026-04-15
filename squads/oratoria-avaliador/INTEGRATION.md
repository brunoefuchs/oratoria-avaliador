# Integração ml-worker ↔ oratoria-avaliador squad

> **Status:** v0.5.1 — entrypoint `process()` pronto; integração em ml-worker/app.py pendente (não executada para não tocar código em produção sem confirmação).

## Fluxo

```
[ml-worker/app.py]
   ↓ coleta outputs de N workers
   ↓
[process_evaluation.process()]   ← entrypoint único do squad
   ├─ ml_worker_adapter.to_features_canonical()
   ├─ pipeline_end_to_end.run_pipeline()
   └─ audit_outlier.audit()  (se FAIL)
   ↓
[return result]
   └─ { gate_decision, artifacts, audit_report, features_canonical }
   ↓
[ml-worker persiste + entrega OU escala]
```

## Como chamar (exemplo)

```python
# Em ml-worker/app.py, após rodar todos os workers:

from squads.oratoria_avaliador.tasks.process_evaluation import process

# (assumindo que você já colheu voice_result, posture_result, etc.)

result = process(
    evaluation_id=req.evaluation_id,
    storage_path=video_url,
    duration_seconds=video_duration_seconds,
    fps=30,
    audio_sample_rate=44100,
    worker_outputs={
        "voice_analyzer": voice_result,
        "filler_detector": filler_result,
        "posture_analyzer": posture_result,
        "gesture_analyzer": gesture_result,
        "facial_analyzer": facial_result,
        "opening_analyzer": opening_result,
        "tonality_analyzer": tonality_result,  # v1.1.0
    },
    evaluation_context=evaluation_context_from_db,  # {"motivacao": [...], ...}
    processing_time_ms=elapsed_ms,
    warnings=warnings_list,
    fallbacks_applied=fallbacks_list,
)

gate = result["gate_decision"]

if gate["release_to_user"]:
    # PASS ou WAIVED → entregar
    narrative = result["artifacts"]["narrative"]
    exercises = result["artifacts"]["exercise_plan"]
    fidelity = result["artifacts"]["fidelity_result"]["fidelity_pct"]

    # persistir em Supabase
    save_report(evaluation_id, narrative, exercises, gate, fidelity)
    notify_complete(callback_url, evaluation_id, status="success")

else:
    # FAIL ou INCOMPLETE → escalar
    audit_report = result["audit_report"]  # já vem pronto
    log_fail(evaluation_id, gate, audit_report)
    notify_complete(
        callback_url,
        evaluation_id,
        status="failed",
        error_message=f"Gate FAIL: {gate['critical_fails']} → escalate_to {audit_report['escalate_to']}",
    )
```

## Retorno do `process()`

```python
{
    "pipeline_result": "COMPLETE" | "ABORTED_AT_PHASE_1",
    "evaluation_id": str,
    "features_canonical": dict,      # output do adapter (v1.1.0)
    "gate_decision": {
        "verdict": "PASS" | "FAIL" | "WAIVED" | "INCOMPLETE",
        "release_to_user": bool,
        "gate_states": {
            "G1_CONTRACT_VALIDITY": {...},
            "G2_COMPLETUDE": {...},
            "G3_CONGRUENCE": {...},
            "G4_VOICE_DNA_FIDELITY": {...},
            "G5_HIERARCHY_VALIDITY": {...},
            "G6_EXERCISE_LINKAGE": {...},
        },
        "critical_fails": list[str],
        "next_action": str,  # humano-legível
    },
    "artifacts": {
        "contract_result": {...},       # G1 result
        "scoring_result": {...},        # scores + applied_weights
        "congruence_result": {...},     # G3 violations se houver
        "hierarchy_result": {...},      # top-N problemas rankeados
        "router_result": {...},         # mentor + rationale
        "exercise_plan": {...},         # exercícios linkados
        "narrative": str,               # markdown na voz do mentor
        "fidelity_result": {...},       # G4 fidelity score
    },
    "audit_report": dict | None,        # preenchido se FAIL
}
```

## Nomes de workers esperados em `worker_outputs`

| Chave | ml-worker file | Obrigatório? |
|-------|----------------|--------------|
| `voice_analyzer` | `voice_analyzer.py` | Recomendado |
| `filler_detector` | `filler_detector.py` | Recomendado |
| `posture_analyzer` | `posture_analyzer.py` | Recomendado |
| `gesture_analyzer` | `gesture_analyzer.py` | Recomendado |
| `facial_analyzer` | `facial_analyzer.py` | Recomendado |
| `opening_analyzer` | `opening_analyzer.py` | Opcional |
| `tonality_analyzer` | `tonality_analyzer.py` | Opcional (v1.1.0) |

Qualquer worker ausente → dimensão correspondente omitida no canonical (dimensão parcial é aceita por design; G2 só avisa).

Worker com `confidence: "failed"` → dimensão omitida com warning no metadata.

## Shape esperado por worker

Adapter aceita DOIS formatos (alinhado com ml-worker atual):

```python
# Formato 1: metrics-nested (preferido)
{
    "version": "0.3.1",
    "confidence": "high",
    "metrics": {
        "pitch_mean_hz": 145.0,
        "wpm": 152,
        ...
    },
}

# Formato 2: flat (ainda funciona)
{
    "version": "0.3.1",
    "confidence": "high",
    "pitch_mean_hz": 145.0,
    "wpm": 152,
    ...
}
```

O adapter aplica `_safe_get()` em cadeia, então ausência de campo = skip sem erro.

## Plugar no ml-worker/app.py

**Não executei a edição** para não tocar código em produção sem confirmação. O diff mínimo seria em `_run_pipeline()`, onde hoje os workers são chamados individualmente. Nova seção após todos os workers terminarem:

```python
# ... código existente ...

# Coleta todos outputs
all_outputs = {
    "voice_analyzer": voice_result,
    "filler_detector": filler_result,
    "posture_analyzer": posture_result,
    "gesture_analyzer": gesture_result,
    "facial_analyzer": facial_result,
    "tonality_analyzer": tonality_result,
}

# Busca evaluation_context do Supabase
ctx = supabase.table("evaluation_context")
    .select("*").eq("evaluation_id", req.evaluation_id).single().execute().data

# Chama squad
from squads.oratoria_avaliador.tasks.process_evaluation import process

gov_result = process(
    evaluation_id=req.evaluation_id,
    storage_path=req.video_url,
    duration_seconds=video_duration,
    worker_outputs=all_outputs,
    evaluation_context=ctx,
)

# Persiste resultado + decide release
_save_gate_decision(supabase, gov_result["gate_decision"])
if gov_result["gate_decision"]["release_to_user"]:
    _save_report(supabase, req.evaluation_id, gov_result["artifacts"])
    await _notify_complete(req.callback_url, req.evaluation_id, "success")
else:
    _save_audit(supabase, gov_result["audit_report"])
    await _notify_complete(
        req.callback_url,
        req.evaluation_id,
        "failed",
        error_message=f"gate_fail: {gov_result['gate_decision']['critical_fails']}",
    )
```

## Cuidados

1. **Python path:** `from squads.oratoria_avaliador.tasks...` — ml-worker precisa do diretório `squads/` no `sys.path` ou instalado como package local.

2. **Import circular:** o adapter e o pipeline usam imports relativos dentro de `tasks/` — não importe módulos de tasks do mesmo package cruzando pastas sem ajustar `sys.path`.

3. **Supabase tables:** `gate_decisions`, `audit_reports`, `calibration_log` não existem ainda. Criar migrações em Epic 4b (persistência real do gate history).

4. **Rollout gradual:** plugar em paralelo primeiro — ml-worker continua com `report_generator.py` atual, squad roda em shadow mode. Compare verdicts por algumas semanas. Depois corta sobre.

## Testes

```bash
python3 squads/oratoria-avaliador/tasks/test_integration.py
# ALL INTEGRATION TESTS PASSED (5/5)
```

Integration test usa mocked ml-worker outputs no shape real. Não precisa de ml-worker rodando nem vídeo real.
