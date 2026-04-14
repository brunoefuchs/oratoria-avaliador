# Task: Optimize Workflow Execution

**Task ID:** optimize-workflow
**Version:** 1.0.0
**Purpose:** Otimizar workflows convertendo fases redundantes, identificando paralelização, convertendo checkpoints human → heuristic, e aplicando GAP ZERO
**Orchestrator:** @squad-chief
**Mode:** Analysis + Implementation
**Pattern:** EXEC-DT-002
**Execution Type:** `Agent` (requires semantic analysis of workflow structure)
**Model:** `Opus` (REQUIRED — semantic analysis of phase dependencies, multiplicative impact of errors)
**Haiku Eligible:** NO — this task modifies workflow structure; classification errors cascade

---

## Task Anatomy

| Field | Value |
|-------|-------|
| **task_name** | Optimize Workflow Execution |
| **status** | `active` |
| **responsible_executor** | @squad-chief |
| **execution_type** | Agent |
| **input** | `target` (workflow file path) |
| **output** | Relatório de otimização + economia de tokens |
| **action_items** | Analisar, otimizar, medir economia |
| **acceptance_criteria** | Workflow otimizado + relatório de ROI |

---

## Overview

Comando único para otimizar execução de workflows:

1. **Analisa** estrutura do workflow (fases, checkpoints, handoffs)
2. **Identifica** oportunidades de otimização (6 dimensões)
3. **Calcula** economia potencial de tokens
4. **Gera relatório** de ROI
5. **Implementa** otimizações (com --implement flag)

```
*optimize-workflow {target}

Onde {target} pode ser:
- workflow: "squads/{squad-name}/workflows/{workflow-name}.yaml"
- squad: "{squad-name}" (analisa todos workflows do squad)

Flags:
--scan        Só analisa, não implementa (default)
--implement   Aplica as otimizações no workflow
--cost N      Projeção com N execuções/mês (default: 10)
--verbose     Mostra análise detalhada por fase
```

---

## 6 DIMENSÕES DE OTIMIZAÇÃO

| # | Dimensão | O que otimiza | Métrica |
|---|----------|---------------|---------|
| D1 | **Phase Necessity** | Fases necessárias vs redundantes | % fases removíveis |
| D2 | **Parallelization** | Sequential → Parallel onde possível | # oportunidades |
| D3 | **Checkpoint Hierarchy** | Human → Heuristic onde aplicável | % automatizável |
| D4 | **Executor Distribution** | Agent → Worker/Hybrid por fase | % Worker |
| D5 | **GAP ZERO Compliance** | Tempo idle entre handoffs | gaps encontrados |
| D6 | **Cost Projection** | Tokens por execução | $/mês |

---

## PHASE 0: WORKFLOW LOADING & VALIDATION

**Duration:** 1-2 minutes

### Step 0.1: Parse Target

```yaml
parse_target:
  if_file:
    action: "Analisar único workflow"
    path: "{target}"

  if_squad:
    action: "Listar todos workflows do squad"
    glob: "squads/{target}/workflows/*.yaml"
```

### Step 0.2: Load Workflow

```yaml
load_workflow:
  for_each_file:
    - read: "{file_path}"
    - extract:
        - workflow_id
        - version
        - phases (lista completa)
        - checkpoints
        - agents_involved
        - estimated_duration
```

### Step 0.3: Validate Structure

```yaml
validate_structure:
  required_fields:
    - "workflow.id"
    - "workflow.phases"

  validation:
    - "phases.length >= 2"
    - "each phase has 'name' and 'agent'"

  on_fail:
    action: STOP
    message: "Workflow structure invalid. Fix before optimizing."
```

---

## PHASE 1: PHASE NECESSITY ANALYSIS (D1)

**Duration:** 3-5 minutes

### Step 1.1: Decompose Phases

```yaml
decompose_phases:
  for_each_phase:
    extract:
      - phase_name
      - phase_purpose (from description)
      - inputs (what it receives)
      - outputs (what it produces)
      - agent_assigned
      - dependencies (depends_on)
```

### Step 1.2: Analyze Phase Contribution

```yaml
analyze_contribution:
  for_each_phase:
    questions:
      Q1: "Esta fase produz output único não produzido por outra?"
      Q2: "Remover esta fase quebra o workflow?"
      Q3: "Output desta fase é consumido por fase posterior?"

    classification:
      ESSENTIAL:
        criteria: "Q1=SIM AND (Q2=SIM OR Q3=SIM)"
        action: "Manter"

      REDUNDANT:
        criteria: "Q1=NÃO AND Q3=NÃO"
        action: "Candidata a remoção"

      MERGE_CANDIDATE:
        criteria: "Q1=NÃO AND Q3=SIM"
        action: "Candidata a merge com fase anterior/posterior"
```

### Step 1.3: Output D1 Analysis

```yaml
output_format:
  table: |
    ## D1: Phase Necessity Analysis

    | Phase | Purpose | Q1 Único? | Q2 Quebra? | Q3 Consumido? | Status | Recomendação |
    |-------|---------|-----------|------------|---------------|--------|--------------|
    | {phase_name} | {purpose} | ✅/❌ | ✅/❌ | ✅/❌ | ESSENTIAL/REDUNDANT/MERGE | {action} |

    **Summary:**
    - Essential: {n} fases
    - Redundant: {n} fases (candidatas a remoção)
    - Merge candidates: {n} fases
```

---

## PHASE 2: PARALLELIZATION DETECTION (D2)

**Duration:** 2-3 minutes

### Step 2.1: Build Dependency Graph

```yaml
build_dependency_graph:
  action: |
    Para cada fase, mapear:
    - depends_on: quais fases precisam completar antes
    - produces: quais outputs gera
    - consumes: quais inputs usa

    Resultado: DAG (Directed Acyclic Graph) de dependências
```

### Step 2.2: Identify Parallel Opportunities

```yaml
identify_parallel:
  algorithm: |
    Fases podem rodar em paralelo SE:
    1. Não têm dependência direta entre si
    2. Não competem pelo mesmo recurso (agent)
    3. Outputs não se sobrepõem

  detection:
    for_each_phase_pair:
      if: "phase_a.depends_on NOT INCLUDES phase_b AND phase_b.depends_on NOT INCLUDES phase_a"
      then: "Candidatas a parallelização"
```

### Step 2.3: Output D2 Analysis

```yaml
output_format:
  table: |
    ## D2: Parallelization Opportunities

    | Phase Group | Phases | Current | Opportunity | Impact |
    |-------------|--------|---------|-------------|--------|
    | Group 1 | {phase_a}, {phase_b} | Sequential | Parallel | -{time_saved} |

    **Summary:**
    - Parallel groups identified: {n}
    - Potential time savings: {hours}h per execution

    **Dependency Graph:**
    ```
    {mermaid_diagram}
    ```
```

---

## PHASE 3: CHECKPOINT OPTIMIZATION (D3)

**Duration:** 3-5 minutes

### Step 3.1: Inventory Checkpoints

```yaml
inventory_checkpoints:
  for_each_phase:
    find:
      - "checkpoint: true"
      - "human_review: true"
      - "approval_required: true"
      - "gate:"

    extract:
      - checkpoint_name
      - type (human/automatic/hybrid)
      - condition (what triggers it)
      - action (what happens on pass/fail)
```

### Step 3.2: Classify Checkpoint Type

```yaml
classify_checkpoint:
  for_each_checkpoint:
    questions:
      Q1: "Decisão é binária (YES/NO) ou scoring subjetivo?"
      Q2: "Critério pode ser verificado por script/regex?"
      Q3: "Impacto de erro é reversível?"

    classification:
      KEEP_HUMAN:
        criteria: "Q1=Subjetivo OR Q2=NÃO OR Q3=NÃO"
        reason: "Requires human judgment"

      CONVERT_HEURISTIC:
        criteria: "Q1=Binário AND Q2=SIM AND Q3=SIM"
        reason: "Can be automated with script"

      CONVERT_HYBRID:
        criteria: "Q1=Binário AND Q2=PARCIAL"
        reason: "Script + Agent validation"
```

### Step 3.3: Output D3 Analysis

```yaml
output_format:
  table: |
    ## D3: Checkpoint Optimization

    | Checkpoint | Current Type | Q1 Binário? | Q2 Scriptável? | Q3 Reversível? | Recommendation |
    |------------|--------------|-------------|----------------|----------------|----------------|
    | {name} | Human | ✅/❌ | ✅/❌/⚠️ | ✅/❌ | Keep/Convert Heuristic/Convert Hybrid |

    **Summary:**
    - Human checkpoints: {n}
    - Convertible to heuristic: {n} ({pct}%)
    - Convertible to hybrid: {n} ({pct}%)

    **Automation Potential:** {total_pct}%
```

---

## PHASE 4: EXECUTOR DISTRIBUTION (D4)

**Duration:** 3-5 minutes

### ⚠️ MANDATORY: Load Decision Tree Framework

```yaml
mandatory_dependency:
  file: "squads/squad-creator/data/executor-decision-tree.md"
  action: READ COMPLETELY
  reason: "Framework contains the 6 questions for executor classification"
```

### Step 4.1: Analyze Phase Actions

```yaml
analyze_phase_actions:
  for_each_phase:
    decompose:
      - "List ALL actions/steps in this phase"
      - "For each action, note if deterministic or interpretive"
```

### Step 4.2: Apply Q1-Q6 Per Phase

```yaml
apply_decision_tree:
  for_each_phase:
    questions:
      Q1: "Output da fase é 100% previsível dado o input?"
      Q2: "Pode ser escrito como função pura f(x) → y?"
      Q2a: "Existe script/lib que faz isso?"
      Q3: "Requer interpretação de linguagem natural?"
      Q4: "Impacto de erro é significativo?"

    classification:
      WORKER:
        criteria: "Q1=SIM AND Q2=SIM AND Q2a=SIM"
        cost: "$0.0001/exec"

      AGENT:
        criteria: "Q3=SIM AND Q4=Baixo"
        cost: "$0.03-0.10/exec"

      HYBRID:
        criteria: "Mixed deterministic + interpretive"
        cost: "$0.01-0.05/exec"
```

### Step 4.3: Output D4 Analysis

```yaml
output_format:
  table: |
    ## D4: Executor Distribution

    | Phase | Current | Q1 Det? | Q2 Pura? | Q3 NL? | Q4 Impact? | Recommended | Savings |
    |-------|---------|---------|----------|--------|------------|-------------|---------|
    | {phase} | Agent | ✅/❌ | ✅/❌ | ✅/❌ | Alto/Baixo | Worker/Hybrid | {pct}% |

    **Summary:**
    - Worker phases: {n} ({pct}%)
    - Agent phases: {n} ({pct}%)
    - Hybrid phases: {n} ({pct}%)

    **Distribution Target:** 70% Worker, 20% Hybrid, 10% Agent
```

---

## PHASE 5: GAP ZERO ANALYSIS (D5)

**Duration:** 2-3 minutes

### Step 5.1: Map Handoffs

```yaml
map_handoffs:
  for_each_phase_transition:
    extract:
      - from_phase
      - to_phase
      - handoff_method (automatic/manual)
      - wait_condition (if any)
      - estimated_delay
```

### Step 5.2: Detect Gaps

```yaml
detect_gaps:
  gap_types:
    IDLE_WAIT:
      pattern: "Phase completes but next doesn't start automatically"
      fix: "Add auto-trigger on completion"

    HUMAN_BOTTLENECK:
      pattern: "Next phase waits for human approval that could be heuristic"
      fix: "Convert to automatic gate (see D3)"

    MISSING_HANDOFF:
      pattern: "No explicit handoff defined between phases"
      fix: "Add explicit handoff_to section"

    CONTEXT_LOSS:
      pattern: "Next phase doesn't receive outputs from previous"
      fix: "Add output→input mapping"
```

### Step 5.3: Output D5 Analysis

```yaml
output_format:
  table: |
    ## D5: GAP ZERO Compliance

    | Transition | From → To | Gap Type | Current Delay | Fix | Priority |
    |------------|-----------|----------|---------------|-----|----------|
    | T1 | Phase A → Phase B | IDLE_WAIT | ~30min | Auto-trigger | HIGH |

    **Summary:**
    - Gaps found: {n}
    - Total idle time: {hours}h per execution
    - GAP ZERO compliant: {yes/no}

    **Veto Conditions to Add:**
    {list of veto conditions}
```

---

## PHASE 6: COST PROJECTION (D6)

**Duration:** 2-3 minutes

### Step 6.1: Calculate Current Costs

```yaml
calculate_current:
  model_pricing:
    opus:
      input_per_1m: 15.00
      output_per_1m: 75.00
    sonnet:
      input_per_1m: 3.00
      output_per_1m: 15.00
    haiku:
      input_per_1m: 1.00
      output_per_1m: 5.00

  per_phase:
    estimate_tokens:
      input: "phase_context + workflow_state"
      output: "phase_result + handoff_context"

    calculate:
      cost_per_exec: "(input_tokens × price) + (output_tokens × price)"
```

### Step 6.2: Calculate Optimized Costs

```yaml
calculate_optimized:
  apply_recommendations:
    - "Worker phases: $0.0001/exec"
    - "Hybrid phases: 20% of original"
    - "Haiku-eligible phases: use Haiku pricing"
    - "Parallel phases: same cost, less time"
```

### Step 6.3: Output D6 Analysis

```yaml
output_format:
  table: |
    ## D6: Cost Projection

    | Phase | Current Model | Current Cost | Optimized Model | Optimized Cost | Savings |
    |-------|---------------|--------------|-----------------|----------------|---------|
    | {phase} | Opus | $0.10 | Haiku | $0.01 | 90% |

    **Summary (per execution):**
    - Current total: ${current}
    - Optimized total: ${optimized}
    - Savings: ${savings} ({pct}%)

    **Monthly Projection ({n} executions):**
    - Current: ${monthly_current}
    - Optimized: ${monthly_optimized}
    - Monthly savings: ${monthly_savings}

    **Annual Savings:** ${annual}
```

---

## PHASE 7: REPORT GENERATION

**Duration:** 2-3 minutes

### Step 7.1: Consolidate Findings

```yaml
report_template: |
  # Workflow Optimization Report

  **Workflow:** {workflow_id}
  **Version:** {version}
  **Date:** {date}
  **Analyzer:** *optimize-workflow v1.0.0

  ---

  ## Executive Summary

  | Dimension | Score | Opportunity | Priority |
  |-----------|-------|-------------|----------|
  | D1: Phase Necessity | {score}/10 | {n} redundant phases | {priority} |
  | D2: Parallelization | {score}/10 | {n} parallel groups | {priority} |
  | D3: Checkpoints | {score}/10 | {pct}% automatizable | {priority} |
  | D4: Executors | {score}/10 | {pct}% Worker potential | {priority} |
  | D5: GAP ZERO | {score}/10 | {n} gaps found | {priority} |
  | D6: Cost | {score}/10 | ${savings}/month | {priority} |

  **Overall Optimization Score:** {total}/60

  **ROI Summary:**
  - Current cost: ${current}/month
  - Optimized cost: ${optimized}/month
  - Monthly savings: ${savings} ({pct}%)
  - Implementation effort: ~{hours}h
  - Payback period: {days} days

  ---

  ## Detailed Analysis

  {D1_table}
  {D2_table}
  {D3_table}
  {D4_table}
  {D5_table}
  {D6_table}

  ---

  ## Action Items

  ### 🔴 HIGH PRIORITY (This Week)
  {high_priority_items}

  ### 🟡 MEDIUM PRIORITY (This Month)
  {medium_priority_items}

  ### 🟢 LOW PRIORITY (Backlog)
  {low_priority_items}

  ---

  ## Implementation Guide

  {step_by_step_implementation}
```

---

## PHASE 8: IMPLEMENTATION MODE (--implement)

**Trigger:** `--implement` flag
**Duration:** 5-10 minutes

### Step 8.1: Apply Optimizations

```yaml
apply_optimizations:
  for_each_recommendation:
    D1_redundant_phases:
      action: "Comment out phase with # DEPRECATED: reason"
      backup: "Create .bak file before modification"

    D2_parallelization:
      action: "Add parallel_group annotation"
      note: "Execution parallelization requires runner changes"

    D3_checkpoint_conversion:
      action: |
        Replace:
          checkpoint:
            type: human
        With:
          checkpoint:
            type: heuristic
            condition: "{binary_condition}"

    D4_executor_change:
      action: |
        Add to phase:
          executor:
            type: worker|hybrid
            script: "{script_path}"

    D5_gap_zero:
      action: |
        Add to phase:
          on_complete:
            trigger: next_phase
          veto_conditions:
            - id: "GAP_ZERO_{phase}"
              condition: "..."
```

### Step 8.2: Validate Changes

```yaml
validate_changes:
  checks:
    - "YAML syntax valid"
    - "All phases still reachable"
    - "No circular dependencies introduced"
    - "Checkpoints still cover critical gates"

  on_fail:
    action: "Rollback to .bak and report errors"
```

### Step 8.3: Version Bump

```yaml
version_bump:
  action: |
    Update workflow version:
    - Minor bump if structural changes only
    - Major bump if checkpoint logic changed

  add_changelog:
    entry: |
      ## v{new_version} ({date})
      - Optimized by *optimize-workflow v1.0.0
      - D1: Removed {n} redundant phases
      - D3: Converted {n} checkpoints to heuristic
      - D4: Changed {n} phases to Worker executor
      - Projected savings: ${savings}/month
```

---

## Examples

### Example 1: Scan Mode (Default)

```
User: *optimize-workflow squads/squad-creator/workflows/wf-squad-fusion.yaml

Agent:

## Workflow Optimization Analysis

**Workflow:** wf-squad-fusion
**Phases:** 5
**Current cost:** ~$0.45/execution

---

### D1: Phase Necessity

| Phase | Purpose | Unique? | Consumido? | Status |
|-------|---------|---------|------------|--------|
| discovery | Validate domain | ✅ | ✅ | ESSENTIAL |
| research | Find elite minds | ✅ | ✅ | ESSENTIAL |
| extraction | Clone minds | ✅ | ✅ | ESSENTIAL |
| integration | Wire squad | ✅ | ✅ | ESSENTIAL |
| validation | Quality gates | ✅ | ❌ | ESSENTIAL |

**Result:** 0 redundant phases found ✅

---

### D2: Parallelization

| Group | Phases | Opportunity |
|-------|--------|-------------|
| G1 | extraction (per mind) | Can run N minds in parallel |

**Result:** 1 parallelization opportunity ✅

---

### D3: Checkpoints

| Checkpoint | Current | Scriptable? | Recommendation |
|------------|---------|-------------|----------------|
| research_quality | Human | ✅ | → Heuristic |
| extraction_review | Human | ⚠️ | → Hybrid |
| final_qa | Human | ❌ | Keep Human |

**Result:** 33% convertible to heuristic, 33% to hybrid ✅

---

### D6: Cost Projection

| Current | Optimized | Savings |
|---------|-----------|---------|
| $0.45/exec | $0.25/exec | 44% |
| $4.50/month | $2.50/month | $2.00/month |

---

**Overall Score:** 48/60 (Good - room for optimization)

Want me to apply these optimizations? Use: *optimize-workflow wf-squad-fusion.yaml --implement
```

### Example 2: Implement Mode

```
User: *optimize-workflow squads/squad-creator/workflows/wf-squad-fusion.yaml --implement

Agent:

## Applying Optimizations...

✅ Created backup: wf-squad-fusion.yaml.bak

### Changes Applied:

1. **D3: Checkpoint Conversion**
   - research_quality_gate: human → heuristic
   - Condition: `score >= 7.0 AND sources >= 3`

2. **D4: Executor Optimization**
   - discovery phase: Agent → Hybrid (added preflight script)

3. **D5: GAP ZERO**
   - Added auto-trigger on research completion
   - Added veto condition GAP_ZERO_001

4. **Version Bump**
   - 1.0.0 → 1.1.0
   - Changelog entry added

✅ YAML syntax validated
✅ All phases reachable
✅ No circular dependencies

**Result:** Workflow optimized. Projected savings: $2.00/month (44%)
```

---

## Quality Gate

```yaml
quality_gate:
  id: "SC_WFL_OPT_001"
  name: "Workflow Optimization Quality"

  blocking:
    - "All 6 dimensions analyzed"
    - "Each dimension has score"
    - "ROI calculated"
    - "Action items prioritized"

  warning:
    - "Implementation guide provided"
    - "Backup created before changes"
```

---

## Command Variants

```bash
# SCAN (default) - análise das 6 dimensões
*optimize-workflow wf-squad-fusion.yaml
*optimize-workflow squad-creator              # todos workflows do squad

# IMPLEMENT - scan + aplica otimizações
*optimize-workflow wf-squad-fusion.yaml --implement

# COST - projeção customizada
*optimize-workflow wf-squad-fusion.yaml --cost 50   # 50 exec/mês

# VERBOSE - análise detalhada
*optimize-workflow wf-squad-fusion.yaml --verbose

# COMBINADOS
*optimize-workflow wf-squad-fusion.yaml --implement --cost 100 --verbose
```

---

## Anti-Patterns

### ❌ Anti-Pattern 1: Optimizing without understanding

```yaml
WRONG:
  action: "Convert all human checkpoints to heuristic"
  why_wrong: "Some checkpoints NEED human judgment"

CORRECT:
  action: "Analyze each checkpoint with Q1-Q3, convert only those that pass"
```

### ❌ Anti-Pattern 2: Ignoring dependencies

```yaml
WRONG:
  action: "Mark phases A and B as parallel because they don't reference each other"
  why_wrong: "They might share implicit state or resources"

CORRECT:
  action: "Build explicit dependency graph, check for shared resources, THEN identify parallel candidates"
```

### ❌ Anti-Pattern 3: Optimizing for cost only

```yaml
WRONG:
  action: "Convert all Agent phases to Worker for maximum savings"
  why_wrong: "Quality may suffer, errors may cascade"

CORRECT:
  action: "Balance cost optimization with quality maintenance (target: 90% of baseline)"
```

---

## Related Documents

- `optimize.md` - Task optimization (Agent → Worker) — pattern reference
- `executor-decision-tree.md` - Q1-Q6 framework for executor assignment
- `quality-dimensions-framework.md` - Scoring model
- `workflow-tmpl.yaml` - Workflow structure reference
- `validate-squad.md` - Hybrid executor pattern reference

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-02-12 | Initial version — 6 dimensions analysis + implementation mode |

---

**END OF TASK**
